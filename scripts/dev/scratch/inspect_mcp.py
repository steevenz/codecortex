from mcp.server.fastmcp import FastMCP
mcp = FastMCP("Test")

print(f"Dir: {dir(mcp)}")
if hasattr(mcp, "_tool_manager"):
    print(f"Tool Manager Dir: {dir(mcp._tool_manager)}")
