import os

from pydantic.v1 import BaseSettings


class ServerSettings(BaseSettings):
    app_name: str = "langserve-base"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    token: str = ""

    secret_key: str = ""
    protect_level: int = 0

    playbook_path: str = os.path.join('../', 'playbooks')

    class Config:
        env_file = ".env"


server_settings = ServerSettings()
