import json
import os
from pathlib import Path
from typing import List, Dict, Any

from langchain.agents import initialize_agent, AgentType, AgentExecutor
from langchain_community.callbacks import get_openai_callback
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from loguru import logger

from apps.chat_server.utils.tool_loader import ToolLoader


class BaseDriver:
    AGENT_SYSTEM_TEMPLATE = """     
        {system_prompt}

        Here is our chat history:
        {chat_history}

        Here is some context: 
        {rag_content}      

        Answer the following questions as best you can. You have access to the following tools:
        {tools}

        Use the following format:
        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{tools}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question
        Begin!
        Question: {input}
        Thought:{agent_scratchpad}
    """

    def __init__(self):
        current_dir = Path(__file__).parent
        toolsets_dir = os.path.join(current_dir, "..", "toolsets")
        self.tool_loader = ToolLoader(toolsets_dir=toolsets_dir)

    def chat_with_history(self, system_prompt: str, user_message: str,
                         message_history: Any, rag_content: str = "",
                         tools: List[str] = []) -> str:
        try:
            if tools:
                # 处理使用工具的情况
                requested_tools = []
                for tool_name in tools:
                    if isinstance(tool_name, str):
                        loaded_tools = self.tool_loader.get_tools([tool_name])
                        if loaded_tools:
                            requested_tools.extend(loaded_tools)
                        else:
                            logger.warning(f"Tool {tool_name} not found or failed to load")

                agent_prompt = ChatPromptTemplate.from_messages([
                    ("system", self.AGENT_SYSTEM_TEMPLATE),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}"),
                ])

                agent_executor = initialize_agent(
                    tools=requested_tools,
                    llm=self.client,
                    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                    verbose=True,
                    max_iterations=30,
                    early_stopping_method="generate"
                )

                input_data = {
                    "input": user_message,
                    "chat_history": message_history.messages,
                    "rag_content": rag_content,
                    "tools": [tool.name for tool in requested_tools],
                    "system_prompt": system_prompt,
                }

                formatted_prompt = agent_prompt.format(**input_data)
                logger.debug(f"Formatted Prompt:\n{formatted_prompt}")

                with get_openai_callback() as cb:
                    result = agent_executor.run(input_data)
                    token_info = {
                        "input_tokens": cb.prompt_tokens,
                        "output_tokens": cb.completion_tokens,
                    }
                    logger.info(f"Token usage: {token_info}")

                return json.dumps({
                    "result": True,
                    "data": {
                        "content": result,
                        "input_tokens": cb.prompt_tokens,
                        "output_tokens": cb.completion_tokens,
                    }
                }, ensure_ascii=False, indent=4)
            else:
                # 处理不使用工具的情况
                simple_prompt = ChatPromptTemplate.from_messages([
                    ("system", f"{system_prompt}, Here is some context: {rag_content}"),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                ])
                chain = simple_prompt | self.client
                chain_with_history = RunnableWithMessageHistory(
                    chain,
                    get_session_history=lambda: message_history,
                    input_messages_key="input",
                    history_messages_key="chat_history",
                )

                result = chain_with_history.invoke({"input": user_message})

                logger.info(
                    f"Chat Result:\n"
                    f"Request: {user_message}\n"
                    f"System: {system_prompt}\n"
                    f"Response: {result.content}\n"
                    f"Tokens - Input: {result.usage_metadata['input_tokens']}, "
                    f"Output: {result.usage_metadata['output_tokens']}, "
                    f"Total: {result.usage_metadata['total_tokens']}"
                )

                return json.dumps({
                    "result": True,
                    "data": {
                        "content": result.content,
                        "input_tokens": result.usage_metadata['input_tokens'],
                        "output_tokens": result.usage_metadata['output_tokens'],
                    }
                }, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.exception(e)
            return json.dumps({
                "result": True,
                "data": {
                    "content": "非常抱歉,触发了智能体的拦截策略,不能回复您哦.....",
                    "token_usage": {
                        "total_tokens": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_cost": 0
                    }
                }
            }, ensure_ascii=False, indent=4)