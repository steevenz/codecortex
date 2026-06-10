
import asyncio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test")

@mcp.tool()
def my_tool(x: int):
    return x

print(f"Tool manager: {mcp._tool_manager}")
print(f"Tool manager dir: {dir(mcp._tool_manager)}")

async def check():
    tools = await mcp.list_tools()
    print(f"Tools from list_tools: {tools}")

asyncio.run(check())
