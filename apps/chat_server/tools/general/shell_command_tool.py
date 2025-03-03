import json
from typing import Optional
import subprocess
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.tools import BaseTool


class ShellCommandTool(BaseTool):
    command: str = ""

    def _run(
            self, tools_input: str = "", run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        try:
            if tools_input:
                tools_param = {k: str(v) for k, v in json.loads(tools_input).items()}
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
