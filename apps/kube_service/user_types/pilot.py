from langserve import CustomUserType


class StartPilotRequest(CustomUserType):
    pilot_id: str
    api_key: str
    replicas: int = 1
    namespace: str = "lite"
    munchkin_url: str = "http://munchkin"
    rabbitmq_host: str = "rabbitmq-service"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "admin"
    rabbitmq_password: str = ""
    enable_ssl: bool = False
    bot_domain: str = ""
    enable_bot_domain: bool = False
    enable_node_port: bool = False
    node_port: int = 18080


class StopPilotRequest(CustomUserType):
    namespace: str = "lite"
    bot_id: str


class PilotInfo(CustomUserType):
    name: str
    status: str


class ListPilotRequest(CustomUserType):
    namespace: str = "lite"
    label_selector: str = ""
