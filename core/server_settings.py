from typing import Optional

from pydantic.v1 import BaseSettings


class ServerSettings(BaseSettings):
    app_name: str = "langserve-base"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    token: str = ""

    enable_azure_ocr: bool = False
    azure_ocr_endpoint: Optional[str] = ''
    azure_ocr_key: Optional[str] = ''
    
    class Config:
        env_file = ".env"


server_settings = ServerSettings()
