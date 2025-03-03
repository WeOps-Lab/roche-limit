import os
import yaml
import importlib
from typing import List, Dict, Any, Optional
from loguru import logger
from pydantic import create_model
from pydantic.v1 import BaseModel, Field


def create_input_model(tool_config: Dict) -> Optional[type[BaseModel]]:
    """从工具配置创建输入模型"""
    if not tool_config.get('input_schema'):
        return None

    field_definitions = {
        field['key']: (
            eval(field['type']),
            Field(description=field['description'])
        )
        for field in tool_config['input_schema']
    }

    # 创建一个专门的输入模型类
    model_name = f"{tool_config['name']}Input"
    return type(
        model_name,
        (BaseModel,),
        {
            '__annotations__': {
                k: v[0] for k, v in field_definitions.items()
            },
            **{
                k: Field(description=v[1].description)
                for k, v in field_definitions.items()
            }
        }
    )


class ToolLoader:
    def __init__(self, toolsets_dir: str):
        self.toolsets_dir = toolsets_dir
        self._tools_metadata = {}
        self.load_all_toolsets()

    def load_all_toolsets(self):
        """加载所有工具集配置"""
        for file in os.listdir(self.toolsets_dir):
            if not file.endswith('.yml'):
                continue

            with open(os.path.join(self.toolsets_dir, file), 'r') as f:
                for toolset_name, data in yaml.safe_load(f).items():
                    for tool in data.get('tools', []):
                        self._tools_metadata[tool['name']] = {
                            'toolset': toolset_name,
                            'toolset_description': data.get('description', ''),
                            'package': tool['package'],
                            'tool_config': tool,
                        }

    def get_tool_instance(self, tool_name: str, init_params: Optional[Dict[str, Any]] = None):
        """根据工具名称创建工具实例"""
        if tool_name not in self._tools_metadata:
            logger.error(f"Tool {tool_name} not found")
            return None

        metadata = self._tools_metadata[tool_name]
        try:
            module = importlib.import_module(metadata['package'])
            tool_class = getattr(module, metadata['tool_config']['class'])
            tool_config = metadata['tool_config']

            # 先创建输入模型
            args_schema = create_input_model(tool_config)

            # 创建基础实例，包含args_schema
            instance = tool_class(
                name=tool_config['name'],
                args_schema=args_schema,
                **tool_config.get('init_config', {}),
                **(init_params or {})
            )

            return instance
        except Exception as e:
            logger.error(f"Failed to load tool {tool_name}: {e}")
            return None

    def get_tools(self,
                  tool_names: List[str],
                  tools_init_param: Optional[Dict[str, Dict[str, Any]]] = None,
                  tools_param: Optional[Dict[str, Dict[str, Any]]] = None) -> List:
        """获取工具实例列表"""
        if not tool_names:
            return []

        tools = []
        tools_init_param = tools_init_param or {}
        tools_param = tools_param or {}

        for name in tool_names:
            merged_params = {
                **(tools_init_param.get(name, {})),
                **(tools_param.get(name, {}))
            }
            if instance := self.get_tool_instance(name, merged_params):
                tools.append(instance)

        return tools
