from typing import Optional

from pydantic.v1 import Field, BaseModel


class DummyInput(BaseModel):
    tool_input: Optional[str] = Field("", description="An empty string")