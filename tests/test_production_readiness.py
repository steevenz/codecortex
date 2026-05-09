import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from mcp.server.fastmcp import FastMCP
from src.main import create_orchestrator
from src.domain.filesystem.api.tools import register_tools as register_fs_tools
from src.domain.coderefactor.api.tools import register_tools as register_refactor_tools
from src.domain.codegraph.api.tools import register_tools as register_graph_tools
from src.domain.coderepository.api.tools import register_tools as register_repository_tools
from src.domain.codetester.api.tools import register_tools as register_qa_tools
from src.domain.codeindex.api.tools import register_tools as register_index_tools

async def test_all_tools_registered():
    mcp = FastMCP("Test")
    
    # Register all
    register_fs_tools(mcp, create_orchestrator)
    register_refactor_tools(mcp, create_orchestrator)
    register_graph_tools(mcp, create_orchestrator)
    register_repository_tools(mcp, create_orchestrator)
    register_qa_tools(mcp, create_orchestrator)
    register_index_tools(mcp, create_orchestrator)
    
    tools = await mcp.list_tools()
    print(f"Total tools registered: {len(tools)}")
    
    # Check for critical tools
    expected_tools = [
        "fs_tree",
        "fs_read",
        "refactor_impact",
        "graph_build",
        "repo_init",
        "index_repo",
        "qa_run"
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
    
    # We need a path to initialize. Use current dir.
    current_dir = str(Path(__file__).resolve().parents[1])
    
    print(f"Testing repo_init on {current_dir}...")
    result = await mcp.call_tool("repo_init", {"path": current_dir})
    
    # result is a list of Content objects. The first one should have our JSON.
    if not result:
        print("FAILED: No result from tool")
        return False
    
    content = result[0].text
    try:
        data = __import__("json").loads(content)
        print(f"Response format: {list(data.keys())}")
        
        required_keys = ["success", "status_code", "message", "data", "meta"]
        missing_keys = [k for k in required_keys if k not in data]
        
        if missing_keys:
            print(f"FAILED: Missing keys in api_response: {missing_keys}")
            return False
            
        print(f"SUCCESS: api_response format validated. Success={data['success']}")
        return True
    except Exception as e:
        print(f"FAILED: Could not parse response as JSON: {e}")
        print(f"Raw content: {content}")
        return False

async def main():
    print("--- CodeCortex Production Readiness Test ---")
    s1 = await test_all_tools_registered()
    s2 = await test_tool_response_format()
    
    if s1 and s2:
        print("\nOVERALL STATUS: PRODUCTION READY")
        sys.exit(0)
    else:
        print("\nOVERALL STATUS: FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
