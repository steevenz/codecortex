"""
Dynamic Tool Proxy.
Automatically resolves and proxies MCP tool calls.

:project: Cognitive Server
:package: Core.Bridges
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
"""

from typing import Any, Dict, List, Optional
import logging

from mcp import ClientSession

logger = logging.getLogger(__name__)

class DynamicToolProxy:
    """
    Proxies dynamic tool calls to an active MCP session.
    Allows syntax like: `proxy.codecortex_codebase(action="search", query="foo")`
    which translates to `execute_tool("codecortex:codebase", {"action": "search", "query": "foo"})`
    """
    def __init__(self, session: ClientSession):
        self.session = session
        self._cached_tools: Dict[str, Any] = {}
        self._initialized = False

    async def initialize(self):
        """Fetch available tools from the server."""
        try:
            result = await self.session.list_tools()
            for tool in result.tools:
                self._cached_tools[tool.name] = tool
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to fetch tools schema: {e}")

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the remote server."""
        if not self._initialized:
            await self.initialize()

        if tool_name not in self._cached_tools:
            logger.warning(f"Tool {tool_name} not found in remote server schema.")
            # We still attempt to call it, maybe it was added dynamically
            
        try:
            result = await self.session.call_tool(tool_name, arguments)
            if hasattr(result, "content") and result.content:
                # Extract content depending on MCP structure
                contents = []
                for item in result.content:
                    if item.type == "text":
                        contents.append(item.text)
                if len(contents) == 1:
                    # Attempt to parse json if it is structured
                    import json
                    try:
                        return json.loads(contents[0])
                    except:
                        return contents[0]
                return contents
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            raise

    def __getattr__(self, name: str):
        """
        Magic method to proxy method calls.
        Example: `proxy.codecortex_codebase(...)` -> tool_name="codecortex:codebase"
        """
        # Convert snake_case method to namespace:toolname if applicable
        # e.g., codecortex_codebase -> codecortex:codebase
        if "_" in name:
            parts = name.split("_", 1)
            tool_name = f"{parts[0]}:{parts[1]}"
        else:
            tool_name = name

        async def _dynamic_caller(**kwargs):
            return await self.execute_tool(tool_name, kwargs)

        return _dynamic_caller
