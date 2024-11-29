from typing import Type, Optional

import requests
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel, Field

from apps.chat_server.tools.common_input import DummyInput
from core.server_settings import server_settings


class ToolsInput(BaseModel):
    query: str = Field(description="should be a promql search query")


class PrometheusLabelLookupTool(BaseTool):
    name = "prometheus_label_lookup"
    description = """
    useful for when you need to answer questions about metircs data analysis,
    such as "what is the average cpu usage of all pods in the last 24 hours"
    generate a tool_input param , the param is always an empty string
    """
    args_schema: Type[BaseModel] = DummyInput

    def _run(
            self, tool_input: Optional[str] = None, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        response = requests.get(f"{server_settings.prometheus_url}/api/v1/label/__name__/values", params={})
        if response.status_code == 200:
            return str(response.json())
        else:
            return f"Error: {response.text}"

    async def _arun(
            self, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        raise NotImplementedError("custom_search does not support async")


class PrometheusSearchTool(BaseTool):
    name = "prometheus_search"
    description = """
    useful for when you need to answer questions about metircs data analysis,
    such as "what is the average cpu usage of all pods in the last 24 hours"
    the datasource is prometheus,must generate a promql query,
    before using this tool, you mush use the prometheus_label_lookup tool to get the correct metric name
    you will think step by step about the query you want to generate, and then input the query
    """
    args_schema: Type[BaseModel] = ToolsInput

    def _run(
            self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ):
        params = {'query': query}
        response = requests.get(f"{server_settings.prometheus_url}/api/v1/query", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return f"Error: {response.text}"

    async def _arun(
            self, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        raise NotImplementedError("custom_search does not support async")