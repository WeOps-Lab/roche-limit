from langserve import add_routes

from apps.chat_server.runnable.openai_runnable import OpenAIRunnable


def register_routes(app):
    add_routes(app, OpenAIRunnable().instance(), path='/openai')
