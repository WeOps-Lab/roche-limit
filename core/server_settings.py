from pydantic.v1 import BaseSettings


class ServerSettings(BaseSettings):
    app_name: str = "langserve-base"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    token: str = ""

    model_name: str = "BAAI/bge-small-zh-v1.5"

    class Config:
        env_file = ".env"


server_settings = ServerSettings()
