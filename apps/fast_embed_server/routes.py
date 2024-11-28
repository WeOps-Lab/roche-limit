from langserve import add_routes

from apps.fast_embed_server.runnable.fast_embed_runnable import FastEmbedRunnable


def register_routes(app):
    add_routes(app, FastEmbedRunnable().instance())
