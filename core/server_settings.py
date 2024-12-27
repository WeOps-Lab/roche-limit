from pydantic.v1 import BaseSettings


class ServerSettings(BaseSettings):
    app_name: str = "langserve-base"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    token: str = ""
    inventory_dir: str = "/tmp/inventory"
    secret_key: str = ""
    playbook_path: str = "./playbooks"
    private_data_dir: str = "/tmp/"

    class Config:
        env_file = ".env"


server_settings = ServerSettings()
