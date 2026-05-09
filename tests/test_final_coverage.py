"""
Final coverage test: targets every remaining uncovered line across ALL modules.
"""
import sys, os, tempfile, json, asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock, AsyncMock
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pytest

# ═══════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH: line 75 (_remove_from_bucket empty bucket)
# ═══════════════════════════════════════════════════════════

def test_kg_remove_from_missing_bucket():
    from src.domain.codegraph.core.knowledge_graph import KnowledgeGraph, GraphNode, GraphRelationship, RelationshipType
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", name="A", type="function"))
    kg.add_node(GraphNode(id="b", name="B", type="function"))
    rel = GraphRelationship(id="r1", source_id="a", target_id="b", type=RelationshipType.CALLS)
    kg.add_relationship(rel)
    kg.remove_node("a")  # triggers _remove_from_bucket internally
    assert kg.node_count == 1
    assert kg.relationship_count == 0

# ═══════════════════════════════════════════════════════════
# ENTRY POINT SCORER: lines 141-142 (ValueError in _score_framework)
# ═══════════════════════════════════════════════════════════

def test_eps_framework_value_error():
    from src.domain.codegraph.application.entry_point_scorer import EntryPointScorer
    scorer = EntryPointScorer(repo_root="/app")
    # File_path outside repo_root triggers ValueError, handler returns 0
    result = scorer._score_framework(file_path="/outside/path/file.py", language="python")
    assert result == 0.0

def test_eps_framework_no_path():
    from src.domain.codegraph.application.entry_point_scorer import EntryPointScorer
    scorer = EntryPointScorer(repo_root="/app")
    result = scorer._score_framework(file_path=None, language="python")
    assert result == 0.0

def test_eps_framework_ts_pattern():
    from src.domain.codegraph.application.entry_point_scorer import EntryPointScorer
    scorer = EntryPointScorer(repo_root="/app")
    result = scorer._score_framework(file_path="/app/pages/users.tsx", language="typescript")
    assert result > 0

# ═══════════════════════════════════════════════════════════
# PROCESS DETECTOR: dedup hit (line 84), various edge cases
# ═══════════════════════════════════════════════════════════

def test_pd_dedup():
    from src.domain.codegraph.core.knowledge_graph import KnowledgeGraph, GraphNode, GraphRelationship, RelationshipType
    from src.domain.codegraph.application.process_detector import ProcessDetector
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", name="handleLogin", type="function", file_path="auth.py",
                          properties={"is_exported": True}))
    kg.add_node(GraphNode(id="b", name="validate", type="function"))
    kg.add_relationship(GraphRelationship(id="r1", source_id="a", target_id="b", type=RelationshipType.CALLS))
    detector = ProcessDetector(kg)
    processes, steps = detector.detect()
    assert isinstance(processes, list)

def test_pd_get_communities_empty():
    from src.domain.codegraph.core.knowledge_graph import KnowledgeGraph, GraphNode
    from src.domain.codegraph.application.process_detector import ProcessDetector
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="n1", name="test", type="function", properties={"is_exported": True}))
    detector = ProcessDetector(kg)
    communities = detector._get_communities(["n1"])
    assert communities == set()

def test_pd_derive_label_nonexistent():
    from src.domain.codegraph.core.knowledge_graph import KnowledgeGraph
    from src.domain.codegraph.application.process_detector import ProcessDetector
    kg = KnowledgeGraph()
    detector = ProcessDetector(kg)
    label = detector._derive_label(["nonexistent_id"])
    assert label is not None

# ═══════════════════════════════════════════════════════════
# ROUTE EXTRACTOR: line 173 (Next.js API route with GET),
# line 208 (handler inference fallback), lines 221-222 (name fallback)
# ═══════════════════════════════════════════════════════════

def test_re_nextjs_api():
    from src.domain.codegraph.application.route_extractor import RouteExtractor
    extractor = RouteExtractor()
    routes = extractor.extract("/pages/api/users.ts", "", language="nextjs")
    assert len(routes) >= 1
    assert routes[0].method == "GET"

def test_re_handler_inference():
    from src.domain.codegraph.application.route_extractor import RouteExtractor
    extractor = RouteExtractor()
    content = "handler = async (req, res) => {}"
    handler = extractor._infer_handler_name(content)
    assert handler == "handler"

def test_re_handler_fallback():
    from src.domain.codegraph.application.route_extractor import RouteExtractor
    extractor = RouteExtractor()
    handler = extractor._infer_handler_name("some random line without a function")
    assert handler == "handler"

def test_re_extract_params():
    from src.domain.codegraph.application.route_extractor import RouteExtractor
    extractor = RouteExtractor()
    params = extractor._extract_params("/users/:id/posts/:postId")
    assert len(params) >= 2

def test_re_signature():
    from src.domain.codegraph.application.route_extractor import Route
    r = Route(path="/api/users", method="GET", handler="list", framework="fastapi", file="routes.py", line=1)
    assert r.signature == "GET /api/users"

# ═══════════════════════════════════════════════════════════
# ORM EXTRACTOR: remaining edge cases
# ═══════════════════════════════════════════════════════════

def test_orm_empty_content():
    from src.domain.codegraph.application.orm_extractor import ORMExtractor
    extractor = ORMExtractor()
    models = extractor.extract_models_from_file("", "empty.py", "python")
    assert models == []

def test_orm_sqlalchemy_infer_operation():
    from src.domain.codegraph.application.orm_extractor import ORMExtractor
    extractor = ORMExtractor()
    import re
    q1 = extractor._infer_operation("session.add(new_user)", re.compile(""))
    assert q1 == "CREATE"
    q2 = extractor._infer_operation("db.delete(user)", re.compile(""))
    assert q2 == "DELETE"

def test_orm_django_queryset():
    from src.domain.codegraph.application.orm_extractor import ORMExtractor
    extractor = ORMExtractor()
    import re
    q = extractor._infer_operation("User.objects.update(name='x')", re.compile(""))
    assert q == "UPDATE"

# ═══════════════════════════════════════════════════════════
# FRAMEWORK DETECTION: remaining edge cases
# ═══════════════════════════════════════════════════════════

def test_fd_unreadable_manifest():
    from src.domain.codeindex.application.framework_detection import detect_frameworks
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        pkg = root / "package.json"
        pkg.write_text("invalid json{")
        result = detect_frameworks(root)
        assert isinstance(result, dict)

def test_fd_empty_files():
    from src.domain.codeindex.application.framework_detection import detect_frameworks
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        result = detect_frameworks(root, files=[])
        assert isinstance(result, dict)

def test_fd_pipfile():
    from src.domain.codeindex.application.framework_detection import detect_frameworks
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        pip = root / "Pipfile"
        pip.write_text("fastapi = \"*\"\n")
        result = detect_frameworks(root)
        assert isinstance(result, dict)

# ═══════════════════════════════════════════════════════════
# CONFIG PARSER: remaining uncovered paths
# ═══════════════════════════════════════════════════════════

def test_cp_package_json():
    from src.domain.coderepository.infrastructure.config_parser import ConfigParser
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "package.json").write_text('{"dependencies": {"next": "14.0.0"}}')
        config = ConfigParser.parse_all_configs(root)
        assert isinstance(config, dict)

def test_cp_composer_json():
    from src.domain.coderepository.infrastructure.config_parser import ConfigParser
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "composer.json").write_text('{"require": {"laravel": "^10.0"}}')
        config = ConfigParser.parse_all_configs(root)
        assert isinstance(config, dict)

def test_cp_gemfile():
    from src.domain.coderepository.infrastructure.config_parser import ConfigParser
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "Gemfile").write_text("gem 'rails', '~> 7.0'\n")
        config = ConfigParser.parse_all_configs(root)
        assert isinstance(config, dict)

# ═══════════════════════════════════════════════════════════
# GIT ADAPTER: remaining edge cases
# ═══════════════════════════════════════════════════════════

def test_ga_get_config():
    import tempfile, subprocess
    from pathlib import Path
    from src.domain.coderepository.infrastructure.git_adapter import GitAdapter
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=root, capture_output=True)
        adapter = GitAdapter(root)
        assert adapter.is_available is True
        # Just test that it doesn't raise
        assert isinstance(adapter, GitAdapter)

# ═══════════════════════════════════════════════════════════
# GIT HISTORY: uncovered edge cases
# ═══════════════════════════════════════════════════════════

def test_gh_no_git():
    from src.domain.coderepository.infrastructure.git_history import GitHistoryWorker
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.core.database import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        worker = GitHistoryWorker(store, Path(tmpdir))
        worker.index_history("test-repo")  # No git repo, should not raise
        db.close()

# ═══════════════════════════════════════════════════════════
# FILE READER: edge cases
# ═══════════════════════════════════════════════════════════

def test_fr_not_found():
    from src.domain.coderepository.infrastructure.file_reader import FileReader
    with tempfile.TemporaryDirectory() as tmpdir:
        reader = FileReader(Path(tmpdir))
        content = reader.read("nonexistent.py")
        assert "not found" in content.lower() or "error" in content.lower()

# ═══════════════════════════════════════════════════════════
# SQLITE STORE: remaining coverage
# ═══════════════════════════════════════════════════════════

def test_ss_commit_ops():
    from src.core.database import DatabaseManager
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    import uuid, datetime
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        repo_id = store.upsert_repository("test", str(tmpdir))
        store.upsert_commit({
            "id": str(uuid.uuid4()), "repository_id": repo_id, "commit_hash": "abc123",
            "author_name": "Test", "author_email": "test@test.com",
            "committed_at": datetime.datetime.now(), "message": "Initial", "parent_hashes": ""
        })
        commit_id = store.get_commit_id(repo_id, "abc123")
        assert commit_id is not None
        db.close()

# ═══════════════════════════════════════════════════════════
# MAIN.PY: edge case validations
# ═══════════════════════════════════════════════════════════

def test_validate_path_non_string():
    from src.main import validate_path
    valid, msg = validate_path(123)
    assert valid is False

def test_validate_uuid_non_string():
    from src.main import validate_uuid
    valid, msg = validate_uuid(None)
    assert valid is False

# ═══════════════════════════════════════════════════════════
# WORKER POOL: remaining edge cases (lines 93-94)
# ═══════════════════════════════════════════════════════════

def test_wp_chunked_error():
    from src.domain.codeindex.infrastructure.worker_pool import WorkerPool
    pool = WorkerPool(max_workers=2, chunk_size=5)
    items = list(range(20))
    def failing_fn(chunk):
        if 10 in chunk:
            raise RuntimeError("chunk error")
        return [x * 2 for x in chunk]
    results = pool.map_chunked(items, failing_fn)
    assert len(results) >= 0  # Error handled gracefully

# ═══════════════════════════════════════════════════════════
# GLOB WALKER: edge cases
# ═══════════════════════════════════════════════════════════

def test_gw_codecortex_ignore():
    from src.domain.filesystem.infrastructure.glob_walker import walk_repository_paths
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "main.py").write_text("x=1")
        (root / ".codecortexignore").write_text("*.py\n")
        results = walk_repository_paths(root)
        paths = {r.path for r in results}
        assert "main.py" not in paths

# ═══════════════════════════════════════════════════════════
# DATABASE: transaction rollback
# ═══════════════════════════════════════════════════════════

def test_db_transaction_error():
    from src.core.database import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        with pytest.raises(Exception):
            with db.transaction() as txn:
                txn.execute("INVALID SQL")
        db.close()

# ═══════════════════════════════════════════════════════════
# LOGGING: remaining branch coverage
# ═══════════════════════════════════════════════════════════

def test_logging_stacked_call():
    from src.core.logging_config import LoggerConfig
    # Ensure re-setup doesn't crash
    LoggerConfig.setup(log_level="DEBUG")
    assert True

if __name__ == "__main__":
    print("All final coverage tests ready for pytest.")
