from langserve import add_routes

from apps.chunk_server.runnable.file_chunk_runnable import FileChunkRunnable
from apps.chunk_server.runnable.manual_chunk_runnable import ManualChunkRunnable
from apps.chunk_server.runnable.web_page_chunk_runnable import WebPageChunkRunnable


def register_routes(app):
    add_routes(app, FileChunkRunnable().instance(), path="/file_chunk")
    add_routes(app, WebPageChunkRunnable().instance(), path="/webpage_chunk")
    add_routes(app, ManualChunkRunnable().instance(), path="/manual_chunk")
