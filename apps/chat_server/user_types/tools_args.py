from langserve import CustomUserType


class ToolsArgs(CustomUserType):
    key: str
    value: str