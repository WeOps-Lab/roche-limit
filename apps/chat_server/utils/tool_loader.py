import os
import yaml
import importlib
from typing import List, Dict, Any, Optional
from loguru import logger
from pydantic import create_model
from pydantic.v1 import BaseModel, Field

def create_input_model(tool_config: Dict) -> Optional[type[BaseModel]]:
    """从工具配置创建输入模型"""
    if 'input_schema' not in tool_config:
        return None
    
    fields = {}
    for field in tool_config['input_schema']:
        field_type = eval(field['type'])  # 将字符串类型转换为实际类型
        fields[field['key']] = (field_type, Field(description=field['description']))
    
    return create_model('DynamicInput', **fields)

class ToolLoader:
    def __init__(self, toolsets_dir: str):
        self.toolsets_dir = toolsets_dir
        self._tools_cache = {}
        self._tools_metadata = {}
        self.load_all_toolsets()

    def load_all_toolsets(self):
        """加载所有工具集配置"""
        for file in os.listdir(self.toolsets_dir):
            if file.endswith('.yml'):
                with open(os.path.join(self.toolsets_dir, file), 'r') as f:
                    toolset_config = yaml.safe_load(f)
                    for toolset_name, toolset_data in toolset_config.items():
                        package = toolset_data.get('package', '')  # 从工具集级别获取package
                        for tool in toolset_data.get('tools', []):
                            self._tools_metadata[tool['name']] = {
                                'toolset': toolset_name,
                                'toolset_description': toolset_data.get('description', ''),
                                'package': package,  # 存储工具集级别的package
                                'tool_config': tool,
                            }

    def get_tool_instance(self, tool_name: str, init_params: Optional[Dict[str, Any]] = None):
        """根据工具名称创建工具实例，支持初始化参数"""
        if tool_name not in self._tools_metadata:
            logger.error(f"Tool {tool_name} not found in metadata")
            return None

        metadata = self._tools_metadata[tool_name]
        tool_config = metadata['tool_config']
        package = metadata['package']

        try:
            module = importlib.import_module(package)
            tool_class = getattr(module, tool_config['class'])

            # 创建动态输入模型
            input_model = create_input_model(tool_config)
            
            # 从配置中获取基本参数
            constructor_params = {}
            constructor_params['name'] = tool_config['name']
            
            # 从init_config中获取参数
            if 'init_config' in tool_config:
                constructor_params.update(tool_config['init_config'])
            
            # 添加其他初始化参数
            if init_params:
                constructor_params.update(init_params)

            # 创建工具实例
            tool_instance = tool_class(**constructor_params)
            
            # 如果有输入模型，设置到工具实例
            if input_model:
                tool_instance.args_schema = input_model

            if hasattr(tool_instance, 'process_runtime_params'):
                tool_instance._has_runtime_params = True

            return tool_instance
        except Exception as e:
            logger.error(f"Failed to load tool {tool_name}: {e}")
            return None

    def get_tools(self,
                  tool_names: List[str],
                  tools_init_param: Optional[Dict[str, Dict[str, Any]]] = None,
                  tools_param: Optional[Dict[str, Dict[str, Any]]] = None) -> List:
        """获取指定名称的工具实例列表，支持初始化参数和运行时参数"""
        if not tool_names:
            return []

        tools = []
        tools_init_param = tools_init_param or {}
        tools_param = tools_param or {}

        for tool_name in tool_names:
            cache_key = f"{tool_name}_{hash(str(tools_init_param.get(tool_name, {})))}"

            if cache_key not in self._tools_cache:
                tool_instance = self.get_tool_instance(
                    tool_name,
                    init_params=tools_init_param.get(tool_name)
                )
                if tool_instance:
                    self._tools_cache[cache_key] = tool_instance

            if cache_key in self._tools_cache:
                tool_instance = self._tools_cache[cache_key]
                # 如果工具有运行时参数且提供了参数值，则处理运行时参数
                if hasattr(tool_instance, '_has_runtime_params') and tool_name in tools_param:
                    # 创建工具实例的副本，避免修改缓存的实例
                    tool_instance = self._process_runtime_params(tool_instance, tools_param[tool_name])
                tools.append(tool_instance)

        return tools

    def _process_runtime_params(self, tool_instance, runtime_params: Dict[str, Any]):
        """处理工具的运行时参数"""
        try:
            # 创建工具实例的副本
            new_instance = tool_instance.__class__(**{
                attr: getattr(tool_instance, attr)
                for attr in tool_instance.__dict__
                if not attr.startswith('_')
            })
            # 设置基本属性
            new_instance.name = tool_instance.name
            new_instance.description = tool_instance.description
            # 处理运行时参数
            new_instance.process_runtime_params(runtime_params)
            return new_instance
        except Exception as e:
            logger.error(f"Failed to process runtime params for tool {tool_instance.name}: {e}")
            return tool_instance
