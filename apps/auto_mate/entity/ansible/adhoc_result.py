from pydantic import BaseModel, Field


class AdHocResult(BaseModel):
    success: bool = Field(True, description="是否执行成功")
    result: dict = Field({}, description="ad-hoc执行结果")
    message: str = Field("", description="异常信息(success为False时使用)")
    multi_host: bool = Field(False, description="是否是多主机执行")
