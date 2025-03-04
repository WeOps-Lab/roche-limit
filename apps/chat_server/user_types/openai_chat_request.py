import uuid

from langserve import CustomUserType
from typing import Optional, List, Dict

from apps.chat_server.user_types.chat_history import ChatHistory
from apps.chat_server.user_types.tools_args import ToolsArgs


class OpenAIChatRequest(CustomUserType):
    openai_api_base: str = 'https://api.openai.com'
    openai_api_key: str
    model: str = 'gpt-4o'

    system_message_prompt: Optional[str] = ''
    temperature: float = 0.7
    user_message: str
    chat_history: List[ChatHistory]

    conversation_window_size: Optional[int] = 10
    rag_context: Optional[str] = ''
    tools: Optional[List[str]]

    tools_args: Optional[List[ToolsArgs]]

    trace_id: Optional[str] = str(uuid.uuid4())
