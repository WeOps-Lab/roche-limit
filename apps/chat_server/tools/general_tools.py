from typing import Optional
import requests
import subprocess
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.tools import BaseTool


class ChineseHolidayTool(BaseTool):
    def _run(
            self, year: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        url = f"https://api.jiejiariapi.com/v1/holidays/{year}"
        response = requests.get(url)
        if response.status_code == 200:
            return str(response.json()).replace("{","").replace("}","")
        else:
            return f"Error: Failed to fetch holiday data. Status code: {response.status_code}"

    async def _arun(
            self, year: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        raise NotImplementedError("chinese_holiday_lookup does not support async")


class ShellCommandTool(BaseTool):
    command: str = ""
    
    def __init__(self, name: str, description: str, command: str):
        super().__init__(name=name, description=description)
        self.command = command

    def _run(
            self, query: str = "", run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Command execution failed: {str(e)}"

    async def _arun(
            self, query: str = "", run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        raise NotImplementedError("ShellCommandTool does not support async")
