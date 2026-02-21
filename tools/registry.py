from importlib import metadata
import logging
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolInvocation, ToolResults
from tools.builtin import ReadFileTool, get_all_builtin_tools
logger = logging.getLogger(__name__)

class ToolRegistry:
    
    def __init__(self):
        self._tools : dict[str, Tool] = {}
        
    def register(self, tool : Tool):
        if tool.name in self._tools:
            logger.warning(f'Overwriting existing tool " {tool.name}')
        self._tools[tool.name] = tool
        logger.debug(f'Registered tool : {tool.name}')           
        
    def unregister(self, name : str):
        
        if name in self._tools:
            del self._tools[name]
            return True
        return None
    
    def get(self, name : str ) -> Tool:
        if name in self._tools:
            return self._tools[name]
        return False
    
    def get_tools(self):
        
        tools = []
        for tool in self._tools.values():
            tools.append(tool)
        return tools
    
    def get_schemas(self):
        
        return [tool.to_openai_schema() for tool in self.get_tools()]
    
    
    async def invoke(self, name : str, params : dict[str, Any], cwd : Path| None):
        
        tool = self.get(name)
        if tool is None:
            return ToolResults.error_results(f"Unknown Tool :{name}",
                                             metadata = {"tool_name": name})
        validation_errors = tool.validate_params(params)
        if validation_errors:
            return ToolResults.error_results(
                error=f"Invalid parameters : {'; '.join(validation_errors)}",
                metadata = {'tool_name':name, "validation_errors": validation_errors}
            )
        invocation = ToolInvocation(params=params, cwd = cwd)
        try:
            await tool.execute(invocation)
        except Exception as e:
            logger.exception(f"Tool {name} raised unexpected error !")
            return ToolResults.error_results(
                f"Internal error : {str(e)}",
                metadata = {"tool_name": name}
            )
            
            
def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool_cls in get_all_builtin_tools():
        registry.register(tool_cls())    
    return registry
    