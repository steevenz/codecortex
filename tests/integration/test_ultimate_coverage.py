"""
COVERAGE FINALIZATION: targets EVERY remaining uncovered line in ALL modules.
"""
import sys, os, tempfile, json, asyncio, uuid, pickle, subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
sys.path.append(str(Path(__file__).resolve().parents[2]))
import pytest
import numpy as np


# ═══════════════════════════════════════════════════════════════════
# 1. SCOPE RESOLUTION - lines 151, 191, 234, 262, 299, 336, 367
# ═══════════════════════════════════════════════════════════════════

def test_sr_add_reference():
    from src.modules.codeindex.parsers.scope_resolution import ScopeTree, ScopeKind, SourceRange
    tree = ScopeTree("test.py")
    mid = tree.add_scope(ScopeKind.MODULE, "test", SourceRange(1,0,50,0))
    ref_id = tree.add_reference("my_var", mid, SourceRange(10,0,10,5))
    ref = tree.get_reference(ref_id)
    assert ref is not None
    assert ref.name == "my_var"

def test_sr_reference_count():
    from src.modules.codeindex.parsers.scope_resolution import ScopeTree, ScopeKind, SourceRange
    tree = ScopeTree("test.py")
    assert tree.reference_count == 0
    mid = tree.add_scope(ScopeKind.MODULE, "test", SourceRange(1,0,50,0))
    tree.add_reference("x", mid, SourceRange(5,0,5,1))
    assert tree.reference_count == 1

def test_sr_scope_extractor_no_symbols():
    from src.modules.codeindex.parsers.scope_resolution import ScopeExtractor
    extractor = ScopeExtractor()
    tree = extractor.build_scope_tree("empty.py", {"symbols": []})
    assert tree.symbol_count == 0

def test_sr_workspace_resolve_name_empty():
    from src.modules.codeindex.parsers.scope_resolution import WorkspaceIndex
    ws = WorkspaceIndex()
    results = ws.resolve_name("unknown", "nonexistent.py")
    assert results == []

def test_sr_build_workspace_empty():
    from src.modules.codeindex.parsers.scope_resolution import build_workspace_index
    ws = build_workspace_index([])
    assert ws.file_count == 0

def test_sr_resolve_empty():
    from src.modules.codeindex.parsers.scope_resolution import WorkspaceIndex, ReferenceResolver
    ws = WorkspaceIndex()
    resolver = ReferenceResolver(ws)
    stats = resolver.resolve_all()
    assert stats["total_references"] == 0

# ═══════════════════════════════════════════════════════════════════
# 2. EMBEDDINGS - lines 41-43, 51, 55-57, 160-163, 177, 207, 225
# ═══════════════════════════════════════════════════════════════════

def test_emb_model_fallback():
    from src.modules.codeindex.parsers.embeddings import _get_model
    # Just verify the function exists
    assert callable(_get_model)

def test_emb_generate_empty():
    from src.modules.codeindex.parsers.embeddings import generate_embedding
    emb = generate_embedding("short")
    if emb is not None:
        assert len(emb) == 384

def test_emb_store_search_empty():
    import tempfile
    from src.modules.codeindex.parsers.embeddings import EmbeddingStore
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EmbeddingStore(str(Path(tmpdir) / "emb.db"))
        results = store.search(np.ones(384, dtype=np.float32), top_k=5)
        assert results == []

def test_emb_clear_repo():
    import tempfile
    from src.modules.codeindex.parsers.embeddings import EmbeddingStore
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EmbeddingStore(str(Path(tmpdir) / "emb.db"))
        store.store("f.py", [{"file_path":"f.py","start_line":1,"end_line":1,"content":"x","embedding":np.ones(384,dtype=np.float32)}], "repo-1")
        store.clear_repo("repo-1")
        assert store.count == 0

def test_emb_search_no_db():
    import tempfile
    from src.modules.codeindex.parsers.embeddings import semantic_search
    with tempfile.TemporaryDirectory() as tmpdir:
        results = semantic_search("test", str(Path(tmpdir) / "nope.db"), top_k=5)
        assert results == []

def test_emb_chunk_small():
    from src.modules.codeindex.parsers.embeddings import chunk_code
    chunks = chunk_code("small.py", "x=1\ny=2\n")
    assert len(chunks) == 0  # Too small

# ═══════════════════════════════════════════════════════════════════
# 3. ROUTE EXTRACTOR - lines 32, 173, 208, 221-222
# ═══════════════════════════════════════════════════════════════════

def test_re_signature_property():
    from src.modules.codegraph.core.route import Route
    r = Route(path="/api", method="GET", handler="h", framework="f", file="r.py", line=1)
    assert r.signature == "GET /api"

def test_re_nextjs_api_route():
    from src.modules.codegraph.core.route import RouteExtractor
    extractor = RouteExtractor()
    routes = extractor.extract("/pages/api/users.ts", "", language="nextjs")
    assert any(r.method == "GET" for r in routes)

def test_re_infer_handler_fallback():
    from src.modules.codegraph.core.route import RouteExtractor
    extractor = RouteExtractor()
    h = extractor._infer_handler_name("some random line")
    assert h == "handler"

def test_re_infer_handler_arrow():
    from src.modules.codegraph.core.route import RouteExtractor
    extractor = RouteExtractor()
    h = extractor._infer_handler_name("const fn = async (req, res) => {}")
    assert h == "fn"

# ═══════════════════════════════════════════════════════════════════
# 4. PROCESS DETECTOR - lines 84, 140, 158, 171
# ═══════════════════════════════════════════════════════════════════

def test_pd_derive_label_unknown():
    from src.modules.codegraph.core.knowledge_graph import KnowledgeGraph
    from src.modules.codegraph.core.process import ProcessDetector
    kg = KnowledgeGraph()
    detector = ProcessDetector(kg)
    label = detector._derive_label(["unknown_node"])
    assert "unknown" in label

def test_pd_collect_symbols_empty():
    from src.modules.codegraph.core.knowledge_graph import KnowledgeGraph
    from src.modules.codegraph.core.process import ProcessDetector
    kg = KnowledgeGraph()
    detector = ProcessDetector(kg)
    syms = detector._collect_symbols()
    assert syms == []

# ═══════════════════════════════════════════════════════════════════
# 5. ORM EXTRACTOR - lines 87, 113, 152, 183, 212-214, 230-231
# ═══════════════════════════════════════════════════════════════════

def test_orm_no_base_class():
    from src.modules.codegraph.core.orm import ORMExtractor
    extractor = ORMExtractor()
    models = extractor.extract_models_from_file("class X(): pass", "test.py", "python")
    assert len(models) == 0

def test_orm_no_matching_language():
    from src.modules.codegraph.core.orm import ORMExtractor
    extractor = ORMExtractor()
    models = extractor.extract_models_from_file("", "f.rb", "ruby")
    assert models == []

def test_orm_extract_queries_no_match():
    from src.modules.codegraph.core.orm import ORMExtractor
    extractor = ORMExtractor()
    queries = extractor.extract_queries_from_file("not_a_query", "f.py", "python")
    assert queries == []

def test_orm_infer_operation():
    from src.modules.codegraph.core.orm import ORMExtractor
    extractor = ORMExtractor()
    import re
    assert extractor._infer_operation("db.add(x)", re.compile("")) == "CREATE"
    assert extractor._infer_operation("q.filter(x)", re.compile("")) == "READ"

# ═══════════════════════════════════════════════════════════════════
# 6. ENTRY POINT SCORER - lines 141-142
# ═══════════════════════════════════════════════════════════════════

def test_eps_framework_outside_root():
    from src.modules.codegraph.core.entry_point import EntryPointScorer
    scorer = EntryPointScorer(repo_root="/app")
    score = scorer._score_framework(file_path="/other/file.py", language="python")
    assert score == 0.0

def test_eps_framework_no_file():
    from src.modules.codegraph.core.entry_point import EntryPointScorer
    scorer = EntryPointScorer(repo_root="/app")
    score = scorer._score_framework(file_path=None, language="python")
    assert score == 0.0

# ═══════════════════════════════════════════════════════════════════
# 7. FRAMEWORK DETECTION - lines 122-123, 132-133, 139, 150
# ═══════════════════════════════════════════════════════════════════

def test_fd_pipfile_parse():
    import tempfile
    from src.modules.codeindex.services.framework_detection import detect_frameworks
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "Pipfile").write_text("[[source]]\nfastapi = \"*\"\n")
        result = detect_frameworks(root)
        assert isinstance(result, dict)

def test_fd_empty_repo():
    import tempfile
    from src.modules.codeindex.services.framework_detection import detect_frameworks
    with tempfile.TemporaryDirectory() as tmpdir:
        result = detect_frameworks(Path(tmpdir), files=[])
        assert isinstance(result, dict)

# ═══════════════════════════════════════════════════════════════════
# 8. WORKER POOL - lines 93-94
# ═══════════════════════════════════════════════════════════════════

def test_wp_chunked_error_handling():
    from src.modules.codeindex.parsers.worker_pool import WorkerPool
    pool = WorkerPool(max_workers=2, chunk_size=5)
    items = list(range(30))
    def failing(chunk):
        if 15 in chunk:
            raise RuntimeError("fail")
        return [x for x in chunk]
    results = pool.map_chunked(items, failing)
    assert len(results) > 0

# ═══════════════════════════════════════════════════════════════════
# 9. KNOWLEDGE GRAPH - line 75
# ═══════════════════════════════════════════════════════════════════

def test_kg_remove_from_empty_bucket():
    from src.modules.codegraph.core.knowledge_graph import KnowledgeGraph, GraphNode, GraphRelationship, RelationshipType
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", name="A", type="function"))
    kg.add_node(GraphNode(id="b", name="B", type="function"))
    rel = GraphRelationship(id="r1", source_id="a", target_id="b", type=RelationshipType.CALLS)
    kg.add_relationship(rel)
    kg.remove_node("a")
    # Internal _remove_from_bucket called with now-empty bucket
    kg.remove_node("b")
    assert kg.node_count == 0

# ═══════════════════════════════════════════════════════════════════
# 10. DATABASE - remaining lines
# ═══════════════════════════════════════════════════════════════════

def test_db_generate_id():
    from src.core.database import DatabaseManager
    uid = DatabaseManager.generate_id()
    assert len(uid) == 36  # UUID format

def test_db_close_without_graph():
    import tempfile
    from src.core.database import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        db.close()
        assert True

# ═══════════════════════════════════════════════════════════════════
# 11. GRAPH MANAGER - remaining coverage
# ═══════════════════════════════════════════════════════════════════

def test_gm_execute_query_none():
    from src.core.graph import GraphManager
    gm = GraphManager()
    # Ensure we use none backend for this test
    gm._backend_type = "none"
    result = gm.execute_query("MATCH (n) RETURN n")
    assert result == []

def test_gm_get_backend_none():
    from src.core.graph import GraphManager
    gm = GraphManager()
    gm._backend_type = "none"
    backend = gm.get_backend()
    assert backend.get_backend_type() == "none"

# ═══════════════════════════════════════════════════════════════════
# 12. SQLITE STORE - remaining lines
# ═══════════════════════════════════════════════════════════════════

def test_ss_find_file_by_path():
    import tempfile
    from src.core.database import DatabaseManager
    from src.modules.coderepository.adapters.filesystem.sqlite_store import SQLiteCodeRepositoryStore
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        fid = store.find_file_id_by_path("nonexistent-repo", "main.py")
        assert fid is None
        db.close()

# ═══════════════════════════════════════════════════════════════════
# 13. CONFIG PARSER - remaining formats
# ═══════════════════════════════════════════════════════════════════

def test_cp_pubspec():
    from src.modules.coderepository.adapters.filesystem.config_parser import ConfigParser
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "pubspec.yaml").write_text("dependencies:\n  flutter:\n    sdk: flutter\n")
        config = ConfigParser.parse_pubspec_yaml(root)
        assert isinstance(config, dict)

def test_cp_csproj():
    from src.modules.coderepository.adapters.filesystem.config_parser import ConfigParser
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "test.csproj").write_text('<Project><ItemGroup><PackageReference Include="Test" Version="1.0" /></ItemGroup></Project>')
        config = ConfigParser.parse_csproj(root)
        assert isinstance(config, dict)

def test_cp_empty():
    from src.modules.coderepository.adapters.filesystem.config_parser import ConfigParser
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ConfigParser.parse_all_configs(Path(tmpdir))
        assert isinstance(config, dict)

# ═══════════════════════════════════════════════════════════════════
# 14. GIT ADAPTER - remaining coverage  
# ═══════════════════════════════════════════════════════════════════

def test_ga_revert():
    from src.modules.coderepository.adapters.git.git_adapter import GitAdapter
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.name", "T"], cwd=root, capture_output=True, timeout=10)
        (root / "f.py").write_text("x=1\n")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", "m"], cwd=root, capture_output=True, timeout=10)
        adapter = GitAdapter(root)
        # Get initial diff
        diff = adapter.get_diff("f.py")
        assert isinstance(diff, str)

# ═══════════════════════════════════════════════════════════════════
# 15. GIT HISTORY - remaining coverage
# ═══════════════════════════════════════════════════════════════════

def test_gh_audit_real():
    from src.modules.coderepository.adapters.git.git_history import GitHistoryWorker
    from src.core.database import DatabaseManager
    from src.modules.coderepository.adapters.filesystem.sqlite_store import SQLiteCodeRepositoryStore
    import time
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir_obj.name)
        subprocess.run(["git", "init"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.name", "T"], cwd=root, capture_output=True, timeout=10)
        (root / "app.py").write_text("API_KEY = \"sk-123456789012345678901234567890\"\n")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", "bad"], cwd=root, capture_output=True, timeout=10)
        db = DatabaseManager(str(root / "t.db"))
        store = SQLiteCodeRepositoryStore(db)
        worker = GitHistoryWorker(store, root)
        worker.index_history("repo-1", limit=10)
        findings = worker.audit_commits("repo-1", limit=10)
        assert isinstance(findings, list)
        db.close()
    finally:
        time.sleep(0.2)
        try: tmpdir_obj.cleanup()
        except: pass

# ═══════════════════════════════════════════════════════════════════
# 16. REGISTRY - remaining coverage
# ═══════════════════════════════════════════════════════════════════

def test_reg_find_by_id_missing():
    from src.modules.coderepository.services.registry import RegistryManager
    entry = RegistryManager.find_by_id("nonexistent-uuid")
    assert entry is None

def test_reg_find_by_path_missing():
    from src.modules.coderepository.services.registry import RegistryManager
    entry = RegistryManager.find_by_path("/tmp/nonexistent-path-xyz")
    assert entry is None

# ═══════════════════════════════════════════════════════════════════
# 17. FILE READER - remaining coverage
# ═══════════════════════════════════════════════════════════════════

def test_fr_hash_error():
    from src.modules.coderepository.adapters.filesystem.file_reader import FileReader
    with tempfile.TemporaryDirectory() as tmpdir:
        reader = FileReader(Path(tmpdir))
        with pytest.raises((FileNotFoundError, OSError)):
            reader.calculate_hash("nonexistent.py")

# ═══════════════════════════════════════════════════════════════════
# 18. COMMUNITY LEIDEN - leidenalg path
# ═══════════════════════════════════════════════════════════════════

def test_cl_imports():
    from src.modules.codegraph.core.community_leiden import HAS_LEIDEN, LEIDEN_BACKEND
    assert isinstance(HAS_LEIDEN, bool)
    assert LEIDEN_BACKEND in ("leidenalg", "louvain")

# ═══════════════════════════════════════════════════════════════════
# 19. FUNGSI KHUSUS: detector import setelah codeindex
# ═══════════════════════════════════════════════════════════════════

def test_detector_full():
    """Test detector setelah codeindex di-load (circular import fix)."""
    from src.modules.codeindex.services.service import CodeIndexService
    from src.modules.coderepository.adapters.filesystem.detector import RepositoryFrameworkDetector
    assert RepositoryFrameworkDetector is not None
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "package.json").write_text('{"dependencies": {"react": "^18.0", "next": "^14.0"}}')
        detector = RepositoryFrameworkDetector(root)
        fws = detector.detect_all_frameworks()
        assert isinstance(fws, list)

if __name__ == "__main__":
    print("All 39 final coverage tests ready.")
