import json
from typing import Optional, Dict
import subprocess
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.tools import BaseTool
from loguru import logger


class ShellCommandTool(BaseTool):
    command: str = ""
    tools_args: Optional[Dict[str, str]]

    def _run(
            self, tools_input: str = "", run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        try:
            logger.info(f"Running command: {self.command}")
            tools_param = {}
            if self.tools_args:
                tools_param.update(self.tools_args)
            if tools_input:
                tools_dict = json.loads(tools_input)
                tools_param.update(tools_dict)

            tools_param = {k: str(v) for k, v in tools_param.items()}
            self.command = self.command.format(**tools_param)
            result = subprocess.run(
                self.command,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip().replace("{", "").replace("}", "")
        except subprocess.CalledProcessError as e:
            return f"Command execution failed: {str(e)}"

    async def _arun(
            self, query: str = "", run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        raise NotImplementedError("ShellCommandTool does not support async")
