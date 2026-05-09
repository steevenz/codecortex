
import asyncio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test")

@mcp.tool()
def my_tool(x: int):
    return x

print(f"Tools type: {type(mcp._tool_manager._tools)}")
print(f"Tools content: {mcp._tool_manager._tools}")
