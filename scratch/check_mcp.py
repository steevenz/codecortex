
import asyncio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test")

@mcp.tool()
def my_tool(x: int):
    return x

print(f"Dir mcp: {dir(mcp)}")
print(f"Tools attribute: {getattr(mcp, '_tools', 'NOT FOUND')}")

try:
    print(f"List tools: {mcp.list_tools()}")
except Exception as e:
    print(f"Error list_tools: {e}")
