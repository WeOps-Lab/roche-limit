import os
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.runnables import RunnableLambda

from apps.chat_server.driver.tool_loader import ToolLoader


class ToolsInfoRunnable():
    def tools_info(self, req) -> List:
        current_dir = Path(__file__).parent
        toolsets_dir = os.path.join(current_dir, "..", "toolsets")
        tool_loader = ToolLoader(toolsets_dir=toolsets_dir)
        tool_loader.load_all_toolsets()
        return tool_loader._tools_metadata

    def instance(self):
        runnable = RunnableLambda(self.tools_info).with_types(input_type=List, output_type=List)
        return runnable
