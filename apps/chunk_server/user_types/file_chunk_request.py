from langchain.pydantic_v1 import Field

from apps.chunk_server.user_types.base_chunk_request import BaseChunkRequest


class FileChunkRequest(BaseChunkRequest):
    file: str = Field(..., extra={"widget": {"type": "base64file"}})
    file_name: str
