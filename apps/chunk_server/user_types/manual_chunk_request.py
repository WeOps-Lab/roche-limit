from apps.chunk_server.user_types.base_chunk_request import BaseChunkRequest


class ManualChunkRequest(BaseChunkRequest):
    content: str