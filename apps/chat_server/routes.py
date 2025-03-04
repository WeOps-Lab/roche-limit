from langserve import add_routes

from apps.chat_server.runnable.openai_runnable import OpenAIRunnable
from apps.chat_server.runnable.tools_info_runnable import ToolsInfoRunnable


def register_routes(app):
    add_routes(app, OpenAIRunnable().instance(), path='/openai')
    add_routes(app, ToolsInfoRunnable().instance(), path='/tools_info')
