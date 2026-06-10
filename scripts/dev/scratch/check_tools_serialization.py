
import asyncio
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test")

@mcp.tool()
def my_tool(x: int):
    return x

async def check():
    tools = await mcp.list_tools()
    print(f"Tool list item type: {type(tools[0])}")
    # Try model_dump
    try:
        print(f"Tool model_dump: {tools[0].model_dump()}")
    except Exception as e:
        print(f"model_dump failed: {e}")
        # Fallback to as_dict or similar?
        print(f"Tool dir: {dir(tools[0])}")

asyncio.run(check())
