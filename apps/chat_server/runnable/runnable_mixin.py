from langchain_community.chat_message_histories import ChatMessageHistory

from apps.chat_server.user_types.base_chat_request import BaseChatRequest


class RunnableMixin:

    def chat_llm(self, driver, req: BaseChatRequest):
        llm_chat_history = ChatMessageHistory()

        if req.chat_history:
            for event in req.chat_history[-req.conversation_window_size:]:
                if event.event == "user":
                    llm_chat_history.add_user_message(event.text)
                elif event.event == "bot":
                    llm_chat_history.add_ai_message(event.text)

        result = driver.chat_with_history(
            system_prompt=req.system_message_prompt,
            user_message=req.user_message,
            message_history=llm_chat_history,
            rag_content=req.rag_context,
            tools=req.tools
        )
        return result
