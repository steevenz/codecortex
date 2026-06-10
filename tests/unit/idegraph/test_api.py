import os
import sys
sys.path.insert(0, os.path.abspath('.'))

import pytest
import asyncio
from unittest.mock import MagicMock

from src.modules.idegraph.api.tools import _build_tools

class MockMCP:
    def __init__(self):
        self.tools = {}
        
    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator

class MockDB:
    def close(self):
        pass

class MockOrchestrator:
    def __init__(self):
        self.db = MockDB()

def orchestrator_factory():
    return MockOrchestrator()

@pytest.fixture
def mcp():
    mcp = MockMCP()
    _build_tools(mcp, orchestrator_factory)
    return mcp

@pytest.mark.asyncio
async def test_api_unknown_action(mcp):
    func = mcp.tools["idegraph"]
    res = await func(action="unknown_action")
    
    assert res["success"] is False
    assert res["status_code"] == 400
    assert "Unknown action" in res["message"]

@pytest.mark.asyncio
async def test_api_search_missing_query(mcp):
    func = mcp.tools["idegraph"]
    res = await func(action="search", query=None)
    
    assert res["success"] is False
    assert res["status_code"] == 400
    assert "query is required" in res["message"]

@pytest.mark.asyncio
async def test_api_get_missing_id(mcp):
    func = mcp.tools["idegraph"]
    res = await func(action="get", memory_id=None)
    
    assert res["success"] is False
    assert res["status_code"] == 400
    assert "memory_id is required" in res["message"]

if __name__ == "__main__":
    import asyncio
    m = MockMCP()
    _build_tools(m, orchestrator_factory)
    func = m.tools["idegraph"]
    
    res1 = asyncio.run(func(action="unknown_action"))
    assert res1["success"] is False
    
    res2 = asyncio.run(func(action="search", query=None))
    assert res2["success"] is False
    
    print("All test_api tests PASSED")
