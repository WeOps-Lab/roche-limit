from typing import Optional

from pydantic.v1 import BaseSettings


class ServerSettings(BaseSettings):
    app_name: str = "langserve-base"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    token: str = ""

    prometheus_url: Optional[str] = "http://localhost:9090"


    class Config:
        env_file = ".env"


server_settings = ServerSettings()
