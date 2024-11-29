from typing import List

from langchain_core.runnables import RunnableLambda

from apps.chat_server.runnable.runnable_mixin import RunnableMixin
from apps.chat_server.user_types.openai_chat_request import OpenAIChatRequest
from apps.chat_server.utils.openai_driver import OpenAIDriver


class OpenAIRunnable(RunnableMixin):
    def openai_chat(self, req: OpenAIChatRequest) -> str:
        driver = OpenAIDriver(
            openai_api_key=req.openai_api_key,
            openai_base_url=req.openai_api_base,
            temperature=req.temperature,
            model=req.model,
        )
        result = self.chat_llm(driver, req)
        return result

    def instance(self):
        runnable = RunnableLambda(self.openai_chat).with_types(input_type=OpenAIChatRequest, output_type=str)
        return runnable
