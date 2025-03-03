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

    def _invoke_simple_chain(self, user_message: str, message_history: Any, system_prompt: str, rag_content: str):
        logger.info(f"Starting simple chain invocation with message: {user_message}")
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
        logger.info(f"Simple chain result: {result}")
        return result

    def chat_with_history(self, system_prompt: str, user_message: str,
                          message_history: Any, rag_content: str = "",
                          tools: List[str] = []) -> str:
        try:
            logger.info(f"System Prompt: {system_prompt}, User Message: {user_message},tools:{tools}")

            if tools:
                total_prompt_tokens = 0
                total_completion_tokens = 0

                requested_tools = []
                for tool_name in tools:
                    if isinstance(tool_name, str):
                        loaded_tools = self.tool_loader.get_tools([tool_name])
                        if loaded_tools:
                            requested_tools.extend(loaded_tools)
                        else:
                            logger.warning(f"Tool {tool_name} not found or failed to load")

                agent_executor = initialize_agent(
                    tools=requested_tools,
                    llm=self.client,
                    handle_parsing_errors=True,
                    agent=AgentType.OPENAI_FUNCTIONS,
                    verbose=True,
                    max_iterations=5,
                    early_stopping_method="generate",
                    return_intermediate_steps=True,
                )

                agent_prompt = ChatPromptTemplate.from_messages([
                    ("system", self.AGENT_SYSTEM_TEMPLATE),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}"),
                ])

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
                    result = agent_executor(input_data)
                    total_prompt_tokens += cb.prompt_tokens
                    total_completion_tokens += cb.completion_tokens

                    logger.info(
                        f"Agent execution completed. Token usage - Input: {cb.prompt_tokens}, Output: {cb.completion_tokens}")

                    tool_desc_map = {tool.name: tool.description for tool in requested_tools}
                    tools_result = ""
                    for index, r in enumerate(result['intermediate_steps']):
                        if r[0].tool in tool_desc_map:
                            description = tool_desc_map.get(r[0].tool)
                            tools_result += f"""
                               step:{index}
                                 tools name: {r[0].tool}
                                 tools description: {description}
                                 tools execute result: {r[1]}
                            """ + '\n'
                            logger.info(f"Tool execution: {r[0].tool} - Result: {r[1]}")

                if tools_result:
                    rag_content += f"""
                        <function_call_step_result>
                            {tools_result}
                        </function_call_step_result>
                    """

                    rag_content += f"""
                            <function_call_thought>
                                {result['output']}
                            </function_call_thought>
                    """

                simple_result = self._invoke_simple_chain(user_message, message_history, system_prompt, rag_content)
                total_prompt_tokens += simple_result.usage_metadata['input_tokens']
                total_completion_tokens += simple_result.usage_metadata['output_tokens']

                logger.info(
                    f"Final combined token usage:\n"
                    f"Total Input Tokens: {total_prompt_tokens}\n"
                    f"Total Output Tokens: {total_completion_tokens}\n"
                    f"Total: {total_prompt_tokens + total_completion_tokens}"
                )

                return json.dumps({
                    "result": True,
                    "data": {
                        "content": simple_result.content,
                        "input_tokens": total_prompt_tokens,
                        "output_tokens": total_completion_tokens,
                    }
                }, ensure_ascii=False, indent=4)
            else:
                simple_result = self._invoke_simple_chain(user_message, message_history, system_prompt, rag_content)

                logger.info(
                    f"Chat Result Summary:\n"
                    f"Request: {user_message}\n"
                    f"Response: {simple_result.content}\n"
                    f"Token Usage - Input: {simple_result.usage_metadata['input_tokens']}, "
                    f"Output: {simple_result.usage_metadata['output_tokens']}, "
                    f"Total: {simple_result.usage_metadata['total_tokens']}"
                )

                return json.dumps({
                    "result": True,
                    "data": {
                        "content": simple_result.content,
                        "input_tokens": simple_result.usage_metadata['input_tokens'],
                        "output_tokens": simple_result.usage_metadata['output_tokens'],
                    }
                }, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.exception(f"Error during chat execution: {str(e)}")
            return json.dumps({
                "result": True,
                "data": {
                    "content": "非常抱歉,触发了智能体的拦截策略,不能回复您哦.....",
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            }, ensure_ascii=False, indent=4)
