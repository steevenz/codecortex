import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP
from src.main import create_orchestrator
from src.modules.filesystem.api.tools import register_tools as register_fs_tools
from src.modules.coderefactor.api.tools import register_tools as register_refactor_tools
from src.modules.codegraph.api.tools import register_tools as register_graph_tools
from src.modules.coderepository.api.tools import register_tools as register_repository_tools
from src.modules.codetester.api.tools import register_tools as register_qa_tools

async def test_all_tools_registered():
    mcp = FastMCP("Test")

    register_fs_tools(mcp, create_orchestrator)
    register_refactor_tools(mcp, create_orchestrator)
    register_graph_tools(mcp, create_orchestrator)
    register_repository_tools(mcp, create_orchestrator)
    register_qa_tools(mcp, create_orchestrator)

    tools = await mcp.list_tools()
    print(f"Total tools registered: {len(tools)}")

    expected_tools = [
        "fs_manage",
        "fs_search",
        "code_refactor",
        "code_search",
        "repo_init",
        "repo_analyze",
        "repo_inspect",
        "code_tester"
    ]

    registered_names = [t.name for t in tools]
    missing = [t for t in expected_tools if t not in registered_names]

    if missing:
        print(f"FAILED: Missing tools: {missing}")
        return False

    print("SUCCESS: All critical tools registered.")
    return True

async def test_tool_response_format():
    mcp = FastMCP("Test")
    register_repository_tools(mcp, create_orchestrator)

    current_dir = str(Path(__file__).resolve().parents[1])

    print(f"Testing repo_init on {current_dir}...")
    result = await mcp.call_tool("repo_init", {"repo_path": current_dir})

    if not result:
        print("FAILED: No result from tool")
        return False

    print(f"Result type: {type(result)}")
    print(f"SUCCESS: Tool executed successfully")
    return True

async def test_fs_manage():
    mcp = FastMCP("Test")
    register_fs_tools(mcp, create_orchestrator)

    test_path = str(Path(__file__).resolve().parents[1])
    print(f"Testing fs_manage on {test_path}...")

    result = await mcp.call_tool("fs_manage", {"operation": "tree", "path": test_path, "max_depth": 2})
    print(f"SUCCESS: fs_manage executed")
    return True

if __name__ == "__main__":
    asyncio.run(test_all_tools_registered())
