import asyncio
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("Test")

@mcp.tool()
async def test_tool():
    return {"hello": "world"}

async def run_test():
    result = await mcp.call_tool("test_tool", {})
    print(f"Result Type: {type(result)}")
    for item in result:
        print(f"Item Type: {type(item)}")
        if hasattr(item, "text"):
            print(f"Item Text: {item.text}")
        else:
            print(f"Item: {item}")

asyncio.run(run_test())
