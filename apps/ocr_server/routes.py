from langserve import add_routes

from apps.ocr_server.runnable.got_ocr_runnable import GotOcrRunnable
from core.server_settings import server_settings
from loguru import logger


def register_routes(app):
    add_routes(app, GotOcrRunnable().instance(), path='/got_ocr')