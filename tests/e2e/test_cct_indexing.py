import asyncio
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from src.main import create_orchestrator
from src.modules.coderepository.api.tools import register_tools as register_repository_tools

async def test_cct_indexing():
    mcp = FastMCP("CCT-Test")
    register_repository_tools(mcp, create_orchestrator)

    cct_path = "c:/Users/steevenz/MCP/mcp-cct-server"
    print(f"Targeting CCT Server at: {cct_path}")

    print("\n--- Phase 1: Index Repository ---")
    result = await mcp.call_tool("repo_init", {"repo_path": cct_path})
    print(f"Result: {result}")

    print("\nCCT INDEXING TEST COMPLETED")

if __name__ == "__main__":
    asyncio.run(test_cct_indexing())
