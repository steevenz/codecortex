"""
Integration tests for Unified Indexing — verifies cross-module wiring, imports,
and interaction between Unified Search and Unified Indexing.

:project: CodeCortex
:package: TestScaffold
:author: Steeven Andrian
"""
from __future__ import annotations
import os
import sys
import json
import tempfile
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services import (
    UnifiedSearchEngine, SearchRequest, SearchResponse, get_search_engine, SEARCH_PROVIDERS,
    UnifiedIndexingEngine, IndexingRequest, IndexingResult, get_indexing_engine,
    check_index_status, run_full_index,
    SecurityFilter,
)
from src.services.unified_indexing import IndexStatus as IdxStatus, INDEX_PROVIDERS as IDX_PROVIDERS
from src.cli.indexing import INDEX_COMMANDS, build_parser
from src.api.orchestration import ActionRouter, INDEXING_ACTIONS


def test_module_imports():
    """All services import correctly."""
    assert UnifiedSearchEngine is not None
    assert SearchRequest is not None
    assert UnifiedIndexingEngine is not None
    assert IndexingRequest is not None
    assert IdxStatus is not None
    print("PASS: All services imported successfully")


def test_both_engines_created():
    """Both search and indexing engines create successfully."""
    search_engine = get_search_engine()
    indexing_engine = get_indexing_engine()
    assert search_engine is not None
    assert indexing_engine is not None
    assert search_engine is not indexing_engine
    print("PASS: Both engines created successfully")


def test_shared_provider_consistency():
    """Shared providers exist in both search and indexing registries."""
    shared = ["codecortex-codeindex", "codecortex-graph", "codecortex-knowledge"]
    for pid in shared:
        assert pid in SEARCH_PROVIDERS, f"Missing {pid} in SEARCH_PROVIDERS"
        assert pid in IDX_PROVIDERS, f"Missing {pid} in IDX_PROVIDERS"
    print("PASS: Shared providers consistent across both registries")


def test_index_providers_count():
    """INDEX_PROVIDERS has 8 entries (7 single + 1 full)."""
    assert len(IDX_PROVIDERS) == 8
    print("PASS: INDEX_PROVIDERS has 8 providers")


def test_get_providers():
    """get_providers returns 8 providers with correct structure."""
    engine = get_indexing_engine()
    providers = engine.get_providers()
    assert providers["total"] == 8
    assert len(providers["providers"]) == 8
    first = providers["providers"][0]
    assert "id" in first
    assert "name" in first
    assert "kind" in first
    assert "description" in first
    print("PASS: get_providers returns correct structure")


def test_scheduler_lifecycle():
    """Scheduler start/stop/status lifecycle works correctly."""
    engine = UnifiedIndexingEngine()
    temp_dir = tempfile.mkdtemp()

    result = engine.start_scheduler(temp_dir, interval_seconds=300)
    assert result["success"] is True
    assert engine._scheduler_running is True

    status = engine.scheduler_status()
    assert status["running"] is True
    assert status["repo_path"] == temp_dir
    assert status["interval_seconds"] == 300

    result2 = engine.start_scheduler(temp_dir)
    assert result2["success"] is False
    assert "already running" in result2["message"].lower()

    stop = engine.stop_scheduler()
    assert stop["success"] is True
    assert engine._scheduler_running is False

    result3 = engine.stop_scheduler()
    assert result3["success"] is False
    assert "not running" in result3["message"].lower()
    print("PASS: Scheduler lifecycle (start/double/stop/stop-again)")


def test_full_pipeline_targets():
    """Full pipeline provider resolves all 7 targets."""
    engine = UnifiedIndexingEngine()
    targets = engine._get_provider_targets("codecortex-full")
    expected = ["codeindex", "graph", "embeddings", "knowledge",
                "idegraph", "codelogs", "security"]
    for t in expected:
        assert t in targets, f"Missing target: {t}"
    assert len(targets) == 7
    print("PASS: Full pipeline resolves all 7 targets")


def test_single_provider_targets():
    """Individual provider resolves to its single target."""
    engine = UnifiedIndexingEngine()
    tests = {
        "codecortex-codeindex": ["codeindex"],
        "codecortex-graph": ["graph"],
        "codecortex-embeddings": ["embeddings"],
        "codecortex-knowledge": ["knowledge"],
    }
    for pid, expected in tests.items():
        targets = engine._get_provider_targets(pid)
        assert targets == expected, f"{pid}: expected {expected}, got {targets}"
    print("PASS: Single provider targets resolve correctly")


def test_step_result_dto():
    """IndexStepResult DTO serializes correctly."""
    from src.services.unified_indexing import IndexStepResult
    r = IndexStepResult(
        provider="codecortex-codeindex",
        status=IdxStatus.COMPLETED,
        started_at="2026-01-01T00:00:00",
        completed_at="2026-01-01T00:00:30",
        elapsed_seconds=30.0,
        details={"symbol_count": 150, "file_count": 25},
    )
    d = r.to_dict()
    assert d["provider"] == "codecortex-codeindex"
    assert d["status"] == "completed"
    assert d["elapsed_seconds"] == 30.0
    assert d["details"]["symbol_count"] == 150
    print("PASS: IndexStepResult DTO serialization")


def test_indexing_result_dto():
    """IndexingResult DTO serializes correctly."""
    from src.services.unified_indexing import IndexStepResult
    step = IndexStepResult(
        provider="codecortex-codeindex",
        status=IdxStatus.COMPLETED,
        started_at="2026-01-01T00:00:00",
    )
    r = IndexingResult(
        provider="codecortex-full",
        repo_path="/tmp/test",
        repo_id="abc-123",
        success=True,
        steps=[step],
        started_at="2026-01-01T00:00:00",
        completed_at="2026-01-01T00:01:00",
        total_elapsed_seconds=60.0,
    )
    d = r.to_dict()
    assert d["success"] is True
    assert len(d["steps"]) == 1
    assert d["steps"][0]["status"] == "completed"
    print("PASS: IndexingResult DTO serialization")


def test_empty_repo_handling():
    """Providers return appropriate status for empty repos."""
    engine = UnifiedIndexingEngine()

    r1 = asyncio.run(engine._index_codeindex(IndexingRequest(provider="codecortex-codeindex")))
    assert r1.status == IdxStatus.FAILED
    assert r1.error is not None
    print(f"PASS: Empty codeindex returns failed: {r1.status.value}")

    r2 = asyncio.run(engine._index_graph(IndexingRequest(provider="codecortex-graph")))
    assert r2.status == IdxStatus.SKIPPED
    print(f"PASS: Empty graph returns skipped: {r2.status.value}")

    r3 = asyncio.run(engine._index_embeddings(IndexingRequest(provider="codecortex-embeddings")))
    assert r3.status == IdxStatus.SKIPPED
    print(f"PASS: Empty embeddings returns skipped: {r3.status.value}")


def test_cli_parser():
    """CLI parser builds without errors."""
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    build_parser(subparsers)
    print("PASS: CLI parser built successfully")


def test_orchestration_actions():
    """INDEXING_ACTIONS registered in ActionRouter."""
    assert "run" in INDEXING_ACTIONS
    assert "schedule" in INDEXING_ACTIONS
    assert "stop" in INDEXING_ACTIONS
    assert "status" in INDEXING_ACTIONS
    assert "providers" in INDEXING_ACTIONS
    assert len(INDEXING_ACTIONS) == 5
    print("PASS: All 5 indexing actions registered in ActionRouter")


def test_search_engine_auto_index_reference():
    """Search engine references auto_indexer which is compatible with unified_indexing."""
    from src.services.unified_search import UnifiedSearchEngine
    engine = UnifiedSearchEngine()

    # Search engine has the _search_with_context method that calls run_full_index
    assert hasattr(engine, "_search_with_context")
    print("PASS: UnifiedSearch references auto_indexer for compatibility")


def test_documentation_exists():
    """Documentation files exist for unified-indexing."""
    base = os.path.join(os.path.dirname(__file__), "..", "docs", "features", "unified-indexing")
    for f in ["concept.md", "usage.md"]:
        path = os.path.join(base, f)
        assert os.path.exists(path), f"Missing doc: {path}"
    print("PASS: Documentation files exist")


if __name__ == "__main__":
    test_module_imports()
    test_both_engines_created()
    test_shared_provider_consistency()
    test_index_providers_count()
    test_get_providers()
    test_scheduler_lifecycle()
    test_full_pipeline_targets()
    test_single_provider_targets()
    test_step_result_dto()
    test_indexing_result_dto()
    test_empty_repo_handling()
    test_cli_parser()
    test_orchestration_actions()
    test_search_engine_auto_index_reference()
    test_documentation_exists()
    print()
    print("ALL INTEGRATION TESTS PASSED")
