from langserve import CustomUserType


class NetworkRetrievalRequest(CustomUserType):
    query: str