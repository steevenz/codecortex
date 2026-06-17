"""
Wiring verification script — checks all integration points for unified_indexing.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

print("=== WIRING VERIFICATION ===")
print()

# 1. CLI Registration
print("--- CLI Registration ---")
from src.cli import _DOMAIN_REGISTRY, _init_registry
_init_registry()
assert "indexing" in _DOMAIN_REGISTRY, "indexing not registered"
assert "idx" in _DOMAIN_REGISTRY, "idx alias not registered"
assert "unified-index" in _DOMAIN_REGISTRY, "unified-index alias not registered"
print("indexing: registered with aliases idx, index, unified-index")
cmds = list(_DOMAIN_REGISTRY["indexing"]["commands"].keys())
print("  commands: " + str(cmds))
print("PASS: CLI registration verified")

# 2. MCP Tool Registration
print()
print("--- MCP Tool Registration ---")
from src.api.tools import register_tools
import inspect
src = inspect.getsource(register_tools)
assert "async def indexing(" in src, "indexing tool not found in register_tools"
print("codecortex:indexing MCP tool registered in api/tools.py")
print("PASS: MCP tool registration verified")

# 3. Services Export
print()
print("--- Services Export ---")
from src.services import (
    UnifiedIndexingEngine, IndexingRequest, IndexingResult, get_indexing_engine,
)
from src.services.unified_indexing import INDEX_PROVIDERS
assert UnifiedIndexingEngine is not None
assert IndexingRequest is not None
assert get_indexing_engine is not None
assert len(INDEX_PROVIDERS) == 8
print("UnifiedIndexingEngine: exported from src.services")
print("INDEXING_PROVIDERS: %d providers" % len(INDEX_PROVIDERS))
print("PASS: Services export verified")

# 4. Orchestration
print()
print("--- Orchestration Routing ---")
from src.api.orchestration import ActionRouter, INDEXING_ACTIONS
assert "run" in INDEXING_ACTIONS
assert "schedule" in INDEXING_ACTIONS
assert "stop" in INDEXING_ACTIONS
assert "status" in INDEXING_ACTIONS
assert "providers" in INDEXING_ACTIONS
actions = sorted(INDEXING_ACTIONS)
print("INDEXING_ACTIONS: " + str(actions))
print("PASS: Orchestration routing verified")

# 5. HTTP Endpoints
print()
print("--- HTTP Endpoints ---")
http_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "server", "http.py")
with open(http_path, "r") as f:
    content = f.read()
assert "/v1/index" in content, "/v1/index endpoint not found"
assert "/v1/index/schedule" in content, "/v1/index/schedule endpoint not found"
assert "/v1/index/stop" in content, "/v1/index/stop endpoint not found"
assert "/v1/index/status" in content, "/v1/index/status endpoint not found"
assert "/v1/index/providers" in content, "/v1/index/providers endpoint not found"
print("/v1/index -- POST: run indexing")
print("/v1/index/schedule -- POST: start scheduler")
print("/v1/index/stop -- POST: stop scheduler")
print("/v1/index/status -- GET: scheduler status")
print("/v1/index/providers -- GET: list providers")
print("PASS: HTTP endpoints verified")

# 6. Cross-reference with Unified Search
print()
print("--- Cross-reference with Unified Search ---")
from src.services.unified_search import SEARCH_PROVIDERS
shared = set(SEARCH_PROVIDERS.keys()) & set(INDEX_PROVIDERS.keys())
print("Shared providers: " + str(shared))
assert "codecortex-codeindex" in shared
assert "codecortex-graph" in shared
assert "codecortex-knowledge" in shared
print("PASS: Cross-reference with Unified Search verified")

# 7. Documentation
print()
print("--- Documentation ---")
docs_base = os.path.join(os.path.dirname(__file__), "..", "docs", "features", "unified-indexing")
for f in ["concept.md", "usage.md"]:
    path = os.path.join(docs_base, f)
    assert os.path.exists(path), f + " missing"
    print("docs/features/unified-indexing/" + f + " -- exists")
print("PASS: Documentation verified")

# 8. Main.py tool count
print()
print("--- Main.py tool count ---")
main_path = os.path.join(os.path.dirname(__file__), "..", "src", "main.py")
with open(main_path, "r") as f:
    content = f.read()
assert "8 unified MCP tools" in content
print("src/main.py: updated tool count to 8")
print("PASS: Main.py verified")

# 9. Test files
print()
print("--- Test Files ---")
test_path = os.path.join(os.path.dirname(__file__), "..", "tests", "unit", "test_unified_indexing.py")
assert os.path.exists(test_path), "test_unified_indexing.py missing"
print("tests/unit/test_unified_indexing.py -- exists")
print("PASS: Test files verified")

print()
print("=== ALL WIRING VERIFICATIONS PASSED ===")
