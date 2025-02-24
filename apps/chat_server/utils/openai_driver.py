from langchain_openai import ChatOpenAI

from apps.chat_server.utils.base_driver import BaseDriver


class OpenAIDriver(BaseDriver):
    def __init__(self, openai_api_key, openai_base_url, temperature, model):
        # 先调用父类的初始化方法
        super().__init__()
        
        # 然后初始化 OpenAI 客户端
        self.client = ChatOpenAI(
            openai_api_key=openai_api_key,
            openai_api_base=openai_base_url,
            temperature=temperature,
            model=model,
            max_retries=3,
        )