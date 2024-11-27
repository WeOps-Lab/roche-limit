from langserve import CustomUserType


class ExampleUserType(CustomUserType):
    msg: str
