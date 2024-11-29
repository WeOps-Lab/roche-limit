from langserve import add_routes

from apps.ocr_server.runnable.azure_ocr_runnable import AzureOcrRunnable
from apps.ocr_server.runnable.paddle_ocr_runnable import PaddleOcrRunnable
from core.server_settings import server_settings
from loguru import logger


def register_routes(app):
    if server_settings.enable_azure_ocr:
        logger.info('启动Azure OCR服务')
        add_routes(app, AzureOcrRunnable().instance(), path='/azure_ocr')
    add_routes(app, PaddleOcrRunnable().instance(), path='/paddle_ocr')
