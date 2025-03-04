from langchain_openai import ChatOpenAI
import os
from pathlib import Path

import json
import time
from typing import List, Any
from langchain.agents import initialize_agent, AgentType
from langchain_community.callbacks import get_openai_callback
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from loguru import logger

from apps.chat_server.user_types.tools_args import ToolsArgs
from apps.chat_server.driver.tool_loader import ToolLoader


class OpenAIDriver():
    def __init__(self, openai_api_key, openai_base_url, temperature, model):
        # 先调用父类的初始化方法
        super().__init__()

        # 然后初始化 OpenAI 客户端
        self.client = ChatOpenAI(
            openai_api_key=openai_api_key,
            openai_api_base=openai_base_url,
            temperature=temperature,
            model=model,
            max_retries=3,
        )

        current_dir = Path(__file__).parent
        toolsets_dir = os.path.join(current_dir, "..", "toolsets")
        self.tool_loader = ToolLoader(toolsets_dir=toolsets_dir)

        self.agent_system_template = """     
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

    def _invoke_simple_chain(self, user_message: str,
                             message_history: Any,
                             system_prompt: str,
                             rag_content: str,
                             trace_id: str):
        start_time = time.time()
        logger.info(f"问题[{trace_id}]: {user_message}")
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

        end_time = time.time()
        duration = end_time - start_time

        logger.info(f"耗时:[{duration:.4f}秒],回复[{trace_id}]: {result.content}")
        return result

    def chat_with_history(self, system_prompt: str, user_message: str,
                          message_history: Any, rag_content: str = "",
                          tools: List[str] = [],
                          tools_args: List[ToolsArgs] = [],
                          trace_id: str = '') -> str:
        try:
            logger.info(f"System Prompt: {system_prompt}, User Message: {user_message},tools:{tools}")

            if tools:
                total_prompt_tokens = 0
                total_completion_tokens = 0

                requested_tools = self.tool_loader.get_tools(
                    tool_names=tools,
                    tools_args=tools_args
                )

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
                    ("system", self.agent_system_template),
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
                    tools_result = ""
                    thoughts_result = ""
                    tool_desc_map = {tool.name: tool.description for tool in requested_tools}
                    for index, step in enumerate(agent_executor.iter(input_data)):
                        if 'output' in step:
                            thoughts_result = step['output']
                            continue

                        start_time = time.time()
                        if output := step.get("intermediate_step"):
                            action, value = output[0]
                            description = tool_desc_map.get(action.tool)
                            tools_result += f"""
                               step:{index}
                                 tools name: {action.tool}
                                 tools description: {description}
                                 tools execute result: {value}
                            """ + '\n'
                        end_time = time.time()
                        duration = end_time - start_time
                        logger.info(f"工具执行耗时:[{duration:.4f}秒] [{trace_id}] 执行工具:{action.tool},结果:{value}")

                    total_prompt_tokens += cb.prompt_tokens
                    total_completion_tokens += cb.completion_tokens

                if tools_result:
                    rag_content += f"""
                        <function_call_step_result>
                            {tools_result}
                        </function_call_step_result>
                    """

                    rag_content += f"""
                            <function_call_thought>
                                {thoughts_result}
                            </function_call_thought>
                    """

                simple_result = self._invoke_simple_chain(user_message, message_history, system_prompt, rag_content,
                                                          trace_id)
                total_prompt_tokens += simple_result.usage_metadata['input_tokens']
                total_completion_tokens += simple_result.usage_metadata['output_tokens']

                return json.dumps({
                    "result": True,
                    "data": {
                        "content": simple_result.content,
                        "input_tokens": total_prompt_tokens,
                        "output_tokens": total_completion_tokens,
                    }
                }, ensure_ascii=False, indent=4)
            else:
                simple_result = self._invoke_simple_chain(user_message, message_history, system_prompt, rag_content,
                                                          trace_id)

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
