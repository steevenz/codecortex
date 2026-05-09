import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from mcp.server.fastmcp import FastMCP
from src.main import create_orchestrator
from src.domain.coderepository.api.tools import register_tools as register_repository_tools
from src.domain.codeindex.api.tools import register_tools as register_index_tools

async def test_cct_indexing():
    mcp = FastMCP("CCT-Test")
    register_repository_tools(mcp, create_orchestrator)
    register_index_tools(mcp, create_orchestrator)
    
    cct_path = "c:/Users/steevenz/MCP/mcp-cct-server"
    print(f"Targeting CCT Server at: {cct_path}")
    
    # 1. Initialize
    print("\n--- Phase 1: Initialize Repository ---")
    init_result = await mcp.call_tool("repo_init", {"path": cct_path})
    init_data = __import__("json").loads(init_result[0].text)
    
    if not init_data["success"]:
        print(f"Init Failed: {init_data['message']}")
        return
    
    repo_id = init_data["data"]["repository_id"]
    print(f"Init Success. Repo ID: {repo_id}")
    
    # 2. Index
    print("\n--- Phase 2: Index Repository ---")
    index_result = await mcp.call_tool("index_repo", {"repo_id": repo_id})
    index_data = __import__("json").loads(index_result[0].text)
    
    if not index_data["success"]:
        print(f"Index Failed: {index_data['message']}")
        return
        
    print(f"Index Success: {index_data['message']}")
    print(f"Stats: {index_data['data']}")
    
    print("\nCCT INDEXING TEST COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    asyncio.run(test_cct_indexing())
