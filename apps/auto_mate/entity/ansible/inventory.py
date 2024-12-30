from pydantic import BaseModel, Field


class Inventory(BaseModel):
    host: str = Field("", description="主机")
    user: str = Field("", description="用户")
    password: str = Field("", description="密码")
    port: int = Field(22, description="端口")
    protocol: str = Field("ssh", description="协议")  # 协议类型
