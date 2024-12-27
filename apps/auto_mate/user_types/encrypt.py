from langserve import CustomUserType


class EncryptUserType(CustomUserType):
    content: str
    key: str


class DecryptUserType(CustomUserType):
    content: str
    key: str
