import json
import os
import time
import uuid
from typing import List
from pydantic import BaseModel, Field, parse_obj_as
from langchain_core.runnables import RunnableLambda
from langserve import add_routes

from apps.auto_mate.utils.entrypt import decrypt_data, encrypt_data
from core.server_settings import server_settings
import ansible_runner


class AdHocResult(BaseModel):
    success: bool = Field(True, description="是否执行成功")
    result: dict = Field({}, description="ad-hoc执行结果")
    message: str = Field("", description="异常信息(success为False时使用)")
    multi_host: bool = Field(False, description="是否是多主机执行")


class InventoryBase(BaseModel):
    host: str = Field("", description="主机")
    user: str = Field("", description="用户")
    password: str = Field("", description="密码")
    port: int = Field(22, description="端口")
    protocol: str = Field("ssh", description="协议")  # 协议类型


class AnsibleRunnable:
    def __init__(self):
        self.key = server_settings.secret_key.encode('utf-8')

    def _build_inventory_entry(self, inventory: InventoryBase) -> str:
        inventory_formats = {
            "ssh": (
                "{host} ansible_ssh_user='{user}' ansible_ssh_pass='{password}' "
                "ansible_ssh_port={port}"
            ),
            "winrm": (
                "{host} ansible_user='{user}' ansible_ssh_pass='{password}' "
                "ansible_port={port} ansible_connection=winrm "
                "ansible_winrm_server_cert_validation=ignore"
            )
        }
        try:
            return inventory_formats[inventory.protocol].format(
                host=inventory.host,
                user=inventory.user,
                password=inventory.password,
                port=inventory.port
            )
        except KeyError:
            raise ValueError(f"Unsupported protocol: {inventory.protocol}")

    def build_inventory(self, inventories: List[InventoryBase]) -> str:
        return "\n".join(self._build_inventory_entry(inventory) for inventory in inventories if inventory.host)

    def adhoc(self, content: str) -> str:
        decoded_content = decrypt_data(content, self.key)
        adhoc_config = json.loads(decoded_content)

        _uuid = str(uuid.uuid1())
        now = int(time.time())
        file_name = f"temporary_inventory_{now}_{_uuid}"
        temporary_inventory_file = os.path.join(server_settings.inventory_dir, file_name)

        try:
            inventory = parse_obj_as(List[InventoryBase], adhoc_config["inventory"])
            inventory_str = self.build_inventory(inventory)

            if inventory_str:
                with open(temporary_inventory_file, "w") as f:
                    f.write(inventory_str)
                runner = ansible_runner.run(
                    host_pattern="*",
                    inventory=temporary_inventory_file,
                    module=adhoc_config["module_name"],
                    module_args=adhoc_config["module_args"],
                    json_mode=True,
                    timeout=adhoc_config["timeout"]
                )
            else:
                runner = ansible_runner.run(
                    host_pattern="localhost",
                    module=adhoc_config["module_name"],
                    module_args=adhoc_config["module_args"],
                    json_mode=True,
                    timeout=adhoc_config["timeout"]
                )

            result = self.get_result(runner)
        finally:
            if os.path.exists(temporary_inventory_file):
                os.remove(temporary_inventory_file)  # Clean up any created file even if an exception occurs

        return json.dumps(result)

    def run_playbook(self, content: str) -> str:
        decoded_content = decrypt_data(content, self.key)
        playbook_config = json.loads(decoded_content)

        rc = ansible_runner.RunnerConfig(
            private_data_dir=server_settings.private_data_dir,
            playbook=f"{server_settings.playbook_path}/{playbook_config['playbook_name']}/main.yml",
            timeout=playbook_config["timeout"],
            extravars=playbook_config['extra_vars']
        )
        rc.prepare()
        _uuid = str(uuid.uuid1())
        runner = ansible_runner.Runner(config=rc)
        runner.run()
        runner._uuid = _uuid
        result: AdHocResult = self.get_result(runner)  # noqa

        return json.dumps(result)

    def get_result(self, runner) -> AdHocResult:
        """
        {
            "playbook_name":"ping_scan",
            "timeout":10,
            "extra_vars":{
                "ips": [
                    "127.0.0.1","1.1.1.1"
                ],
                "timeout":3
           }
        }
        :param runner:
        :return:
        """
        events = runner.events or []
        results = {}
        messages = {}
        statuses = {}

        for event in events:
            event_data = event.get("event_data", {})
            ip = event_data.get("remote_addr")
            res = event_data.get("res", {})
            event_type = event.get("event")

            if event_type == "runner_on_ok":
                self._update_event_results(ip, res, results, messages, statuses, success=True)
            elif event_type == "runner_on_failed":
                message = res.get("msg", "Ansible execution failed")
                self._update_event_results(ip, res, results, messages, statuses, success=False, message=message)
            elif event_type == "runner_on_unreachable":
                message = res.get("msg", "Host unreachable")
                self._update_event_results(ip, res, results, messages, statuses, success=False, message=message)

        success = all(statuses.values())
        is_multi_host = len(results) > 1
        result = list(results.values())[0] if results else {}

        final_result = AdHocResult(
            success=success,
            result=results if is_multi_host else result,
            message=";".join(messages.values()),
            multi_host=is_multi_host
        )

        encoded_result = encrypt_data(final_result.json(), self.key)
        return encoded_result

    def _update_event_results(self, ip, res, results, messages, statuses, success, message=None):
        if ip:
            results[ip] = res
            results[ip]["ansible_success"] = success
            messages[ip] = message or "success" if success else "failure"
            statuses[ip] = success

    def register(self, app):
        add_routes(app, RunnableLambda(self.adhoc).with_types(input_type=str, output_type=str), path='/adhoc')
        add_routes(app, RunnableLambda(self.run_playbook).with_types(input_type=str, output_type=str),
                   path='/playbook')
