from typing import Type, Optional
import requests
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel, Field

class HolidayInput(BaseModel):
    year: str = Field(description="要查询的年份，例如：2025")

class ChineseHolidayTool(BaseTool):
    name = "chinese_holiday_lookup"
    description = """
    用于查询中国节假日信息的工具。
    输入年份（如2025），返回该年的所有节假日信息。
    """
    args_schema: Type[BaseModel] = HolidayInput

    def _run(
            self, year: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        url = f"https://api.jiejiariapi.com/v1/holidays/{year}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return f"Error: Failed to fetch holiday data. Status code: {response.status_code}"

    async def _arun(
            self, year: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        raise NotImplementedError("chinese_holiday_lookup does not support async")
