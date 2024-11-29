from langchain_openai import ChatOpenAI

from apps.chat_server.utils.base_driver import BaseDriver


class OpenAIDriver(BaseDriver):
    def __init__(self, openai_api_key, openai_base_url, temperature, model):
        self.client = ChatOpenAI(
            openai_api_key=openai_api_key,
            openai_api_base=openai_base_url,
            temperature=temperature,
            model=model,
            max_retries=3,
        )