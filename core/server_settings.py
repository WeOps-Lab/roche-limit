from pydantic.v1 import BaseSettings


class ServerSettings(BaseSettings):
    app_name: str = "langserve-base"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    token: str = ""

    pandoc_server_host: str = "http://pandoc-server.ops-pilot"

    class Config:
        env_file = ".env"


server_settings = ServerSettings()
