"""
Tests for CortexOrchestrator main entry point and GraphManager.
"""
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
sys.path.append(str(Path(__file__).resolve().parents[1]))

# ── GraphManager Tests ─────────────────────────────────────────────────

def test_graph_manager_backend_registry():
    from src.core.graph_manager import GraphManager, BACKEND_REGISTRY
    assert "none" in BACKEND_REGISTRY
    assert "noop" in BACKEND_REGISTRY
    assert "kuzu" in BACKEND_REGISTRY


def test_graph_manager_noop_backend():
    from src.core.graph_manager import GraphManager
    gm = GraphManager()
    backend_type = gm.get_backend_type()
    assert backend_type in ("none", "kuzu", "neo4j", "falkordb")


def test_graph_manager_noop_session():
    from src.core.graph_manager import NoOpBackend, _NoOpSession, _NoOpResult
    backend = NoOpBackend()
    session = backend.get_session()
    assert isinstance(session, _NoOpSession)
    result = session.run("MATCH (n) RETURN n")
    assert isinstance(result, _NoOpResult)
    assert result.single() is None
    assert result.data() == []


def test_graph_manager_test_connection():
    from src.core.graph_manager import GraphManager
    gm = GraphManager()
    ok, err = gm.test_connection()
    assert isinstance(ok, bool)


def test_graph_manager_close():
    from src.core.graph_manager import GraphManager
    gm = GraphManager()
    gm.close()  # Should not raise


# ── Orchestrator Tests ─────────────────────────────────────────────────

def test_validate_path():
    import tempfile
    from src.main import validate_path
    with tempfile.TemporaryDirectory() as tmpdir:
        valid, msg = validate_path(tmpdir)
        assert valid is True
        assert msg == ""


def test_validate_path_nonexistent():
    from src.main import validate_path
    valid, msg = validate_path("/nonexistent/path/12345")
    assert valid is False
    assert "not exist" in msg


def test_validate_path_empty():
    from src.main import validate_path
    valid, msg = validate_path("")
    assert valid is False


def test_validate_path_traversal():
    from src.main import validate_path
    valid, msg = validate_path("/safe/../etc/passwd")
    assert valid is False
    assert "traversal" in msg


def test_validate_uuid():
    from src.main import validate_uuid
    valid, msg = validate_uuid("550e8400-e29b-41d4-a716-446655440000")
    assert valid is True


def test_validate_uuid_invalid():
    from src.main import validate_uuid
    valid, msg = validate_uuid("not-a-uuid")
    assert valid is False


def test_validate_max_depth():
    from src.main import validate_max_depth
    valid, msg = validate_max_depth(5)
    assert valid is True
    valid, msg = validate_max_depth(0)
    assert valid is False
    valid, msg = validate_max_depth(21)
    assert valid is False


def test_validate_max_depth_not_int():
    from src.main import validate_max_depth
    valid, msg = validate_max_depth("deep")
    assert valid is False


def test_normalize_relpath():
    from src.main import _normalize_relpath
    from pathlib import Path
    root = Path("/project")
    assert _normalize_relpath(root, "./src/main.py") == "src/main.py"
    assert _normalize_relpath(root, "") is None
    assert _normalize_relpath(root, "  ") is None


def test_api_response_format():
    from src.core import api_response, new_request_id
    rid = new_request_id()
    resp = api_response(success=True, status_code=200, message="OK", data={"key": "val"}, request_id=rid)
    assert resp["success"] is True
    assert resp["status_code"] == 200
    assert resp["message"] == "OK"
    assert resp["data"]["key"] == "val"
    assert "meta" in resp


def test_api_response_error():
    from src.core import api_response, new_request_id
    rid = new_request_id()
    resp = api_response(success=False, status_code=400, message="Bad request", data=None, request_id=rid, error_code="ERR_001")
    assert resp["success"] is False
    assert "meta" in resp


def test_create_orchestrator():
    import tempfile
    from src.main import create_orchestrator
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        orch = create_orchestrator(db_path)
        assert orch is not None
        assert orch.db is not None
        orch.db.close()


def test_get_repo_id_nonexistent():
    import tempfile
    from src.main import create_orchestrator
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        orch = create_orchestrator(db_path)
        repo_id = orch.get_repo_id("/nonexistent")
        assert repo_id is None
        orch.db.close()

# ── Backend Base Tests ─────────────────────────────────────────────────

def test_backend_base():
    from src.core.backends.base import GraphBackend
    # Cannot instantiate abstract class directly, but can verify methods exist
    import inspect
    methods = [m for m in dir(GraphBackend) if not m.startswith("_")]
    assert "get_session" in methods
    assert "create_schema" in methods
    assert "is_connected" in methods
    assert "close" in methods


# ── Config Parser Tests ────────────────────────────────────────────────

def test_config_parser_imports():
    from src.domain.coderepository.infrastructure.config_parser import ConfigParser
    assert ConfigParser is not None


# ── Git Adapter Tests ──────────────────────────────────────────────────

def test_git_adapter_imports():
    from src.domain.coderepository.infrastructure.git_adapter import GitAdapter
    assert GitAdapter is not None


if __name__ == "__main__":
    test_graph_manager_backend_registry()
    test_graph_manager_noop_backend()
    test_graph_manager_noop_session()
    test_graph_manager_test_connection()
    test_graph_manager_close()
    test_validate_path()
    test_validate_path_nonexistent()
    test_validate_path_empty()
    test_validate_path_traversal()
    test_validate_uuid()
    test_validate_uuid_invalid()
    test_validate_max_depth()
    test_validate_max_depth_not_int()
    test_normalize_relpath()
    test_api_response_format()
    test_api_response_error()
    test_create_orchestrator()
    test_get_repo_id_nonexistent()
    test_backend_base()
    test_config_parser_imports()
    test_git_adapter_imports()
    print("All main module tests passed!")
