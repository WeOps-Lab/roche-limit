import os
import yaml
import importlib
from typing import List
from loguru import logger

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
                        for tool in toolset_data.get('tools', []):
                            self._tools_metadata[tool['name']] = {
                                'toolset': toolset_name,
                                'toolset_description': toolset_data.get('description', ''),
                                'tool_config': tool
                            }

    def get_tool_instance(self, tool_name: str):
        """根据工具名称创建工具实例"""
        if tool_name not in self._tools_metadata:
            logger.error(f"Tool {tool_name} not found in metadata")
            return None

        metadata = self._tools_metadata[tool_name]
        tool_config = metadata['tool_config']

        try:
            module = importlib.import_module(tool_config['package'])
            tool_class = getattr(module, tool_config['class'])
            
            tool_instance = tool_class()
            # 使用YAML中的配置覆盖工具实例的属性
            tool_instance.name = tool_config['name']
            tool_instance.description = tool_config['description']
            
            return tool_instance
        except Exception as e:
            logger.error(f"Failed to load tool {tool_name}: {e}")
            return None

    def get_tools(self, tool_names: List[str]) -> List:
        """获取指定名称的工具实例列表"""
        if not tool_names:
            return []

        tools = []
        for tool_name in tool_names:
            if tool_name not in self._tools_cache:
                tool_instance = self.get_tool_instance(tool_name)
                if tool_instance:
                    self._tools_cache[tool_name] = tool_instance
            
            if tool_name in self._tools_cache:
                tools.append(self._tools_cache[tool_name])

        return tools
