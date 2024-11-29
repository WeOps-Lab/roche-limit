from langserve import add_routes

from apps.chat_server.runnable.openai_runnable import OpenAIRunnable
from apps.chat_server.runnable.zhipu_runnable import ZhipuRunnable


def register_routes(app):
    add_routes(app, OpenAIRunnable().instance(), path='/openai')
    add_routes(app, ZhipuRunnable().instance(), path='/zhipu')
