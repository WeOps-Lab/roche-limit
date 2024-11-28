from langserve import add_routes

from apps.bce_rerank_server.runnable.bce_embed_runnable import BCEEmbedRunnable
from apps.bce_rerank_server.runnable.bce_rerank_runnable import BCEReRankRunnable


def register_routes(app):
    add_routes(app, BCEReRankRunnable().instance(), path="/rerank")
    add_routes(app, BCEEmbedRunnable().instance(), path="/embed")
