import json
import os
import time
import uuid
from pydantic import parse_obj_as
from langchain_core.runnables import RunnableLambda
from langserve import add_routes
from pydantic import typing, BaseModel, Field

from apps.auto_mate.utils.entrypt import decrypt_data, encrypt_data
from core.server_settings import server_settings
import ansible_runner


class AdHocResult(BaseModel):
    success: bool = Field(True, description="执行是否成功")
    result: dict = Field({}, description="执行AD-Hoc返回的JSON对象")
    message: str = Field("", description="执行的异常信息，success为False时可以使用此信息")
    multi_host: bool = Field(False, description="是否多主机执行")


class InventoryBase(BaseModel):
    host: str = Field("", description="主机")
    user: str = Field("", description="用户")
    password: str = Field("", description="密码")
    port: int = Field(22, description="端口")
    # 协议
    protocol: str = Field("ssh", description="协议")


class AnsibleRunnable:
    def __init__(self):
        self.key = server_settings.secret_key.encode('utf-8')

    def build_inventory(self, inventories: typing.List[InventoryBase]):
        """
        172.16.60.220 ansible_ssh_user=root ansible_ssh_pass=123456 ansible_ssh_port=22
        172.16.60.221 ansible_ssh_user=root ansible_ssh_pass=bo@123 ansible_ssh_port=22
        172.16.60.222 ansible_ssh_user=app ansible_ssh_pass=bj@123 ansible_ssh_port=22 ansible_sudo_pass=bj@123
        """
        ssh_inventory_format = (
            "{host} ansible_ssh_user='{user}' ansible_ssh_pass='{password}' " "ansible_ssh_port={port}"
        )
        winrm_inventory_format = (
            "{host} ansible_user='{user}' ansible_ssh_pass='{password}'"
            " ansible_port={port} ansible_connection=winrm  "
            "ansible_winrm_server_cert_validation=ignore"
        )
        inventory_list = []
        for inventory in inventories:
            host = inventory.host
            if not host:
                continue
            if inventory.protocol == "ssh":
                user = inventory.user or "root"
                password = inventory.password or ""
                port = inventory.port or 22
                inventory_str = ssh_inventory_format.format(host=host, user=user, password=password, port=port)
            elif inventory.protocol == "winrm":
                user = inventory.user or "Administrator"
                password = inventory.password or ""
                port = inventory.port or 5985
                inventory_str = winrm_inventory_format.format(host=host, user=user, password=password, port=port)
            else:
                raise Exception(f"不支持的协议{inventory.protocol}")
            inventory_list.append(inventory_str)
        return "\n".join(inventory_list)

    def adhoc(self, content: str) -> str:
        """
        {"inventory":"xxxx","module":"","module_args":"","timeout":10,"extravars":""}
        """
        decoded_content = decrypt_data(content, server_settings.secret_key.encode('utf-8'))
        adhoc_config = json.loads(decoded_content)

        _uuid = str(uuid.uuid1())
        is_local = True
        temporary_inventory_file = ""
        now = int(time.time())
        file_name = f"temporary_inventory_{now}"
        temporary_inventory_file = os.path.join(server_settings.inventory_dir, file_name)

        inventory = parse_obj_as(typing.List[InventoryBase], adhoc_config["inventory"])
        inventory_str = self.build_inventory(inventory)
        if inventory_str:
            with open(temporary_inventory_file, "w") as f:
                f.write(inventory_str)
            is_local = False
            runner = ansible_runner.run(
                host_pattern="*",
                inventory=temporary_inventory_file,
                module=adhoc_config["module_name"],
                module_args=adhoc_config["module_args"],
                json_mode=True,
                timeout=adhoc_config["timeout"],
                extravars={},
            )
            os.remove(temporary_inventory_file)
        else:
            runner = ansible_runner.run(
                host_pattern="localhost",
                module=adhoc_config["module_name"],
                module_args=adhoc_config["module_args"],
                json_mode=True,
                timeout=adhoc_config["timeout"],
                extravars={},
            )

        runner._uuid = _uuid
        runner.temporary_inventory_file = temporary_inventory_file
        result: AdHocResult = self.get_result(runner)
        return json.dumps(result)

    def get_result(self, runner, is_async=False) -> AdHocResult:
        timeout = runner.config.timeout
        success = True
        all_result = {}
        all_message = {}
        all_status = {}
        if is_async:
            message = "async run ansible command"
        else:
            for e in runner.events:
                if e["event"] == "runner_on_ok":
                    ip = e["event_data"]["remote_addr"]
                    all_result.setdefault(ip, {}).update(e["event_data"]["res"])
                    all_result[ip].update(ansible_success=True)
                    all_message.setdefault(ip, "success")
                    all_status.setdefault(ip, True)
                elif e["event"] == "runner_on_failed":
                    message = str(e["event_data"]["res"].get("msg", "ansible执行失败"))
                    ip = e["event_data"]["remote_addr"]
                    all_result.setdefault(ip, {}).update(e["event_data"]["res"])
                    all_result[ip].update(ansible_success=False)
                    all_message.setdefault(ip, message)
                    all_status.setdefault(ip, False)
                elif e["event"] == "runner_on_unreachable":
                    ip = e["event_data"]["remote_addr"]
                    message = str(e["event_data"]["res"].get("msg", "ansible主机无法链接"))
                    all_result.setdefault(ip, {})
                    all_message.setdefault(ip, message)
                    all_status.setdefault(ip, False)
                    all_result[ip].update(ansible_success=False)

            else:
                if timeout:
                    message = f"failed: runner timeout [timeout:{timeout}],please check kwargs `timeout` value "
                else:
                    message = "failed: runner unknown error "
                success = False
        self.multi_host = getattr(self, "multi_host", False)
        if self.multi_host:
            result = all_result
            message = ";".join([f"{k}:{v}" for k, v in all_message.items()])
            success = all(all_status.values())
        else:
            result = (all_result and list(all_result.values())[0]) or {}
            message = (all_message and list(all_message.values())[0]) or message
            success = (all_status and list(all_status.values())[0]) or success
        result.update(uuid=runner._uuid)
        adhoc_result = AdHocResult(result=result, message=message, success=success, multi_host=self.multi_host)

        encode_content = encrypt_data(adhoc_result.json(), server_settings.secret_key.encode('utf-8'))
        return encode_content

    def register(self, app):
        add_routes(app,
                   RunnableLambda(self.adhoc).with_types(input_type=str, output_type=str),
                   path='/adhoc')
