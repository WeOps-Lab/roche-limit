from pydantic.v1 import BaseSettings


class ServerSettings(BaseSettings):
    app_name: str = "langserve-base"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    token: str = ""

    kube_config_file: str = ""

    class Config:
        env_file = ".env"


server_settings = ServerSettings()
