import json
import os
import tempfile
import uuid
from typing import List
from pydantic import parse_obj_as
from langchain_core.runnables import RunnableLambda
from langserve import add_routes
from loguru import logger
from apps.auto_mate.entity.ansible.adhoc_result import AdHocResult
from apps.auto_mate.entity.ansible.inventory import Inventory
from apps.auto_mate.utils.entrypt import decrypt_data, encrypt_data
from core.server_settings import server_settings
import ansible_runner


class AnsibleRunnable:
    def __init__(self):
        self.key = server_settings.secret_key.encode('utf-8')

    def build_inventory(self, inventories: List[Inventory]) -> str:
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
        inventory_strs = [
            inventory_formats[inventory.protocol].format(
                host=inventory.host,
                user=inventory.user,
                password=inventory.password,
                port=inventory.port
            ) for inventory in inventories if inventory.host
        ]
        return "\n".join(inventory_strs)

    def process_content(self, content: str) -> dict:
        if server_settings.protect_level == 0:
            return json.loads(content)
        elif server_settings.protect_level == 1:
            decoded_content = decrypt_data(content, self.key)
            return json.loads(decoded_content)

    def encode_result(self, result: AdHocResult) -> str:
        result_json = result.json()
        if server_settings.protect_level == 0:
            return json.dumps(result_json)
        elif server_settings.protect_level == 1:
            return encrypt_data(result_json, self.key)

    def adhoc(self, content: str) -> str:
        """
        {
            "inventory": [
                {
                    "host": "127.0.0.1",
                    "port": 22,
                    "user": "root",
                    "protocol": "ssh",
                    "password": "password"
                }
            ],
            "module_name": "shell",
            "module_args": "ifconfig",
            "host_pattern": "all",
            "timeout": 10
        }
        :param content:
        :return:
        """
        adhoc_config = self.process_content(content)
        inventory = parse_obj_as(List[Inventory], adhoc_config["inventory"])
        inventory_str = self.build_inventory(inventory)

        runner = ansible_runner.run(
            host_pattern=adhoc_config["host_pattern"],
            inventory=inventory_str,
            module=adhoc_config["module_name"],
            module_args=adhoc_config["module_args"],
            json_mode=True,
            timeout=adhoc_config["timeout"]
        )

        result = self.get_result(runner)
        logger.info(result)
        return self.encode_result(result)

    def run_playbook(self, content: str) -> str:
        """
        {
            "playbook_name":"ping_scan",
            "timeout":10,
            "extra_vars":{
                "ips": [
                    "127.0.0.1"
                ],
                "timeout":3
           }
        }
        :param content:
        :return:
        """
        playbook_config = self.process_content(content)

        with tempfile.TemporaryDirectory() as tempdir:
            rc = ansible_runner.RunnerConfig(
                private_data_dir=tempdir,
                playbook=f"{server_settings.playbook_path}/{playbook_config['playbook_name']}/main.yml",
                timeout=playbook_config["timeout"],
                extravars=playbook_config['extra_vars']
            )
            rc.prepare()
            _uuid = str(uuid.uuid1())
            runner = ansible_runner.Runner(config=rc)
            runner.run()
            runner._uuid = _uuid
            result: AdHocResult = self.get_result(runner)

        logger.info(result)
        return self.encode_result(result)

    def get_result(self, runner) -> AdHocResult:
        events = runner.events or []
        results, messages, statuses = {}, {}, {}

        for event in events:
            event_data = event.get("event_data", {})
            ip = event_data.get("remote_addr")
            res = event_data.get("res", {})
            event_type = event.get("event")

            if event_type == "runner_on_ok":
                self._update_event_results(ip, res, results, messages, statuses, success=True)
            elif event_type in ["runner_on_failed", "runner_on_unreachable"]:
                message = res.get("msg",
                                  "Ansible execution failed" if event_type == "runner_on_failed" else "Host unreachable")
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

        return final_result

    def _update_event_results(self, ip, res, results, messages, statuses, success, message=None):
        if ip:
            results[ip] = res
            results[ip]["ansible_success"] = success
            messages[ip] = message or "success" if success else "failure"
            statuses[ip] = success

    def register(self, app):
        add_routes(app, RunnableLambda(self.adhoc).with_types(input_type=str, output_type=str), path='/adhoc')
        add_routes(app, RunnableLambda(self.run_playbook).with_types(input_type=str, output_type=str), path='/playbook')
