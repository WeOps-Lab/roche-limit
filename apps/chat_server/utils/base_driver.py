import os
import json
from pathlib import Path

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.tools import ShellTool, DuckDuckGoSearchRun
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from loguru import logger

from apps.chat_server.tools.prometheus_tools import PrometheusLabelLookupTool, PrometheusSearchTool
from apps.chat_server.utils.tool_loader import ToolLoader


class BaseDriver:
    def __init__(self):
        # 使用相对路径，从当前文件位置定位 toolsets 目录
        current_dir = Path(__file__).parent
        toolsets_dir = os.path.join(current_dir, "..", "toolsets")
        self.tool_loader = ToolLoader(toolsets_dir=toolsets_dir)

    def chat_with_history(self, system_prompt, user_message, message_history, rag_content="", tools=[]):
        try:
            if tools:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """     
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

                    """),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}"),
                ])

                # 根据用户指定的工具名称加载工具
                requested_tools = []
                for tool_name in tools:
                    if isinstance(tool_name, str):  # 确保工具名称是字符串
                        loaded_tools = self.tool_loader.get_tools([tool_name])
                        if loaded_tools:
                            requested_tools.extend(loaded_tools)
                        else:
                            logger.warning(f"Tool {tool_name} not found or failed to load")

                if not requested_tools:
                    logger.error("No valid tools were loaded")
                    return json.dumps({
                        "result": False,
                        "data": {"content": "未能加载指定的工具，请检查工具名称是否正确"}
                    })

                agent = create_tool_calling_agent(self.client, requested_tools, prompt)
                agent_executor = AgentExecutor(agent=agent, tools=requested_tools, max_iterations=30, verbose=True)

                input_data = {
                    "input": user_message,
                    "chat_history": message_history.messages,
                    "rag_content": rag_content,
                    "tools": [tool.name for tool in requested_tools],
                    "system_prompt": system_prompt,
                }
                formatted_prompt = prompt.format(**input_data)
                print("Formatted Prompt:\n", formatted_prompt)

                result = agent_executor.invoke(input_data)
                return json.dumps({"result": True, "data": {"content": result["output"]}}, ensure_ascii=False, indent=4)

            else:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", f"{system_prompt}, Here is some context: {rag_content}"),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                ])

                chain = prompt | self.client
                chain_with_history = RunnableWithMessageHistory(
                    chain,
                    get_session_history=lambda: message_history,
                    input_messages_key="input",
                    history_messages_key="chat_history",
                )

                result = chain_with_history.invoke({"input": user_message})

                logger.info(f"""
                            请求消息: {user_message}
                            系统消息: {system_prompt}
                            响应消息: {result.content}
                            输入令牌: {result.usage_metadata['input_tokens']}
                            输出令牌: {result.usage_metadata['output_tokens']}
                            总令牌: {result.usage_metadata['total_tokens']}
                        """)
                return_data = {
                    "content": result.content,
                    "input_tokens": result.usage_metadata['input_tokens'],
                    "output_tokens": result.usage_metadata['output_tokens'],
                }
                return json.dumps({"result": True, "data": return_data}, ensure_ascii=False, indent=4)
        except Exception as e:
            # log traceback
            logger.exception(e)
            return json.dumps({
                "result": True,
                "data": {
                    "content": "非常抱歉,触发了智能体的拦截策略,不能回复您哦.....",
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            })
