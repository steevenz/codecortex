
import asyncio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test")

@mcp.tool()
def my_tool(x: int):
    return f"Result: {x}"

async def check():
    result = await mcp.call_tool("my_tool", {"x": 42})
    print(f"Call tool result: {result}")

asyncio.run(check())
