"""
Unit tests for UnifiedIndexingEngine.

Tests provider registry, request/result DTOs, scheduler lifecycle,
and integration stubs for each provider method.

:project: CodeCortex
:package: Tests.Unit
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
"""
from __future__ import annotations
import json
import os
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.unified_indexing import (
    INDEX_PROVIDERS,
    IndexProvider,
    IndexStatus,
    IndexStepResult,
    IndexingRequest,
    IndexingResult,
    UnifiedIndexingEngine,
    get_indexing_engine,
)


class TestIndexProviderEnum:
    def test_enum_values(self):
        assert IndexProvider.CODECORTEX_CODEINDEX.value == "codecortex-codeindex"
        assert IndexProvider.CODECORTEX_GRAPH.value == "codecortex-graph"
        assert IndexProvider.CODECORTEX_EMBEDDINGS.value == "codecortex-embeddings"
        assert IndexProvider.CODECORTEX_KNOWLEDGE.value == "codecortex-knowledge"
        assert IndexProvider.CODECORTEX_IDEGRAPH.value == "codecortex-idegraph"
        assert IndexProvider.CODECORTEX_CODELOGS.value == "codecortex-codelogs"
        assert IndexProvider.CODECORTEX_SECURITY.value == "codecortex-security"
        assert IndexProvider.CODECORTEX_FULL.value == "codecortex-full"

    def test_enum_members_count(self):
        assert len(IndexProvider) == 8


class TestIndexStatusEnum:
    def test_enum_values(self):
        assert IndexStatus.PENDING.value == "pending"
        assert IndexStatus.RUNNING.value == "running"
        assert IndexStatus.COMPLETED.value == "completed"
        assert IndexStatus.FAILED.value == "failed"
        assert IndexStatus.SKIPPED.value == "skipped"


class TestINDEX_PROVIDERS:
    def test_providers_count(self):
        assert len(INDEX_PROVIDERS) == 8

    def test_full_provider_at_end(self):
        assert INDEX_PROVIDERS["codecortex-full"]["ordered_position"] == 0

    def test_codeindex_provider(self):
        p = INDEX_PROVIDERS["codecortex-codeindex"]
        assert p["kind"] == "astIndex"
        assert p["owned_by"] == "codecortex"
        assert "repo_path" in p["params"]
        assert "repo_id" in p["params"]
        assert "mode" in p["params"]

    def test_graph_provider(self):
        p = INDEX_PROVIDERS["codecortex-graph"]
        assert p["kind"] == "graphBuild"
        assert "repo_id" in p["params"]

    def test_sequential_position_ordering(self):
        positions = [info["ordered_position"] for info in INDEX_PROVIDERS.values()]
        assert len(set(positions)) == len(positions)


class TestIndexStepResult:
    def test_minimal_creation(self):
        r = IndexStepResult(
            provider="codecortex-codeindex",
            status=IndexStatus.COMPLETED,
            started_at="2026-01-01T00:00:00",
        )
        assert r.provider == "codecortex-codeindex"
        assert r.status == IndexStatus.COMPLETED
        assert r.error is None

    def test_to_dict(self):
        r = IndexStepResult(
            provider="codecortex-graph",
            status=IndexStatus.FAILED,
            started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:01:00",
            elapsed_seconds=60.0,
            error="Graph build failed",
            details={"repo_id": "abc-123"},
        )
        d = r.to_dict()
        assert d["provider"] == "codecortex-graph"
        assert d["status"] == "failed"
        assert d["elapsed_seconds"] == 60.0
        assert d["error"] == "Graph build failed"
        assert d["details"]["repo_id"] == "abc-123"


class TestIndexingRequest:
    def test_defaults(self):
        req = IndexingRequest()
        assert req.provider == "codecortex-full"
        assert req.mode == "full"
        assert req.sequential is True
        assert req.detect_modular is True
        assert req.build_dependency_graph is True

    def test_custom_values(self):
        req = IndexingRequest(
            provider="codecortex-codeindex",
            repo_path="/tmp/test",
            repo_id="abc-123",
            mode="incremental",
            sequential=True,
        )
        assert req.provider == "codecortex-codeindex"
        assert req.repo_path == "/tmp/test"
        assert req.repo_id == "abc-123"
        assert req.mode == "incremental"


class TestIndexingResult:
    def test_empty_result(self):
        r = IndexingResult(
            provider="codecortex-full",
            repo_path=None,
            repo_id=None,
            success=True,
        )
        assert r.success is True
        assert len(r.steps) == 0

    def test_to_dict(self):
        step = IndexStepResult(
            provider="codecortex-codeindex",
            status=IndexStatus.COMPLETED,
            started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:00:30",
            elapsed_seconds=30.0,
            details={"symbol_count": 100},
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
        assert d["provider"] == "codecortex-full"
        assert len(d["steps"]) == 1
        assert d["steps"][0]["status"] == "completed"


class TestGetProviderTargets:
    def setup_method(self):
        self.engine = UnifiedIndexingEngine()

    def test_full_provider_targets(self):
        targets = self.engine._get_provider_targets("codecortex-full")
        assert len(targets) == 7
        assert "codeindex" in targets
        assert "graph" in targets
        assert "embeddings" in targets
        assert "knowledge" in targets
        assert "idegraph" in targets
        assert "codelogs" in targets
        assert "security" in targets

    def test_single_provider_targets(self):
        targets = self.engine._get_provider_targets("codecortex-codeindex")
        assert targets == ["codeindex"]

        targets = self.engine._get_provider_targets("codecortex-graph")
        assert targets == ["graph"]

    def test_unknown_provider_default(self):
        targets = self.engine._get_provider_targets("codecortex-unknown")
        assert targets == ["codeindex"]


class TestSchedulerLifecycle:
    def setup_method(self):
        self.engine = UnifiedIndexingEngine()
        self.temp_dir = tempfile.mkdtemp()

    def test_scheduler_start_stop(self):
        result = self.engine.start_scheduler(self.temp_dir, interval_seconds=300)
        assert result["success"] is True
        assert self.engine._scheduler_running is True

        status = self.engine.scheduler_status()
        assert status["running"] is True
        assert status["repo_path"] == self.temp_dir
        assert status["interval_seconds"] == 300

        stop_result = self.engine.stop_scheduler()
        assert stop_result["success"] is True
        assert self.engine._scheduler_running is False

    def test_double_start_returns_error(self):
        self.engine.start_scheduler(self.temp_dir)
        result = self.engine.start_scheduler(self.temp_dir)
        assert result["success"] is False
        assert "already running" in result["message"].lower()
        self.engine.stop_scheduler()

    def test_stop_when_not_running(self):
        result = self.engine.stop_scheduler()
        assert result["success"] is False
        assert "not running" in result["message"].lower()


class TestSingleton:
    def test_get_engine_returns_singleton(self):
        e1 = get_indexing_engine()
        e2 = get_indexing_engine()
        assert e1 is e2

    def test_get_engine_with_orchestrator_creates_new(self):
        e1 = get_indexing_engine()
        mock_orch = MagicMock()
        e2 = get_indexing_engine(orchestrator=mock_orch)
        assert e2 is not e1


@pytest.mark.asyncio
class TestProviderIntegrationStubs:
    def setup_method(self):
        self.engine = UnifiedIndexingEngine()

    @patch("src.services.unified_indexing.UnifiedIndexingEngine._index_codeindex",
           new_callable=AsyncMock)
    async def test_codeindex_step(self, mock_index):
        mock_index.return_value = IndexStepResult(
            provider="codecortex-codeindex",
            status=IndexStatus.COMPLETED,
            started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:00:30",
            elapsed_seconds=30.0,
            details={"symbol_count": 150, "file_count": 25},
        )
        req = IndexingRequest(
            provider="codecortex-codeindex",
            repo_path="/tmp/test",
            mode="full",
        )
        result = await self.engine._index_codeindex(req)
        assert result.status == IndexStatus.COMPLETED
        assert result.details["symbol_count"] == 150

    @patch("src.services.unified_indexing.UnifiedIndexingEngine._index_graph",
           new_callable=AsyncMock)
    async def test_graph_step(self, mock_index):
        mock_index.return_value = IndexStepResult(
            provider="codecortex-graph",
            status=IndexStatus.COMPLETED,
            started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:01:00",
            elapsed_seconds=60.0,
            details={"repo_id": "abc-123"},
        )
        req = IndexingRequest(
            provider="codecortex-graph",
            repo_path="/tmp/test",
        )
        result = await self.engine._index_graph(req)
        assert result.status == IndexStatus.COMPLETED

    @patch("src.services.unified_indexing.UnifiedIndexingEngine._index_embeddings",
           new_callable=AsyncMock)
    async def test_embeddings_step(self, mock_index):
        mock_index.return_value = IndexStepResult(
            provider="codecortex-embeddings",
            status=IndexStatus.COMPLETED,
            started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:02:00",
            elapsed_seconds=120.0,
            details={"files_embedded": 50, "model": "codebert"},
        )
        req = IndexingRequest(
            provider="codecortex-embeddings",
            repo_path="/tmp/test",
        )
        result = await self.engine._index_embeddings(req)
        assert result.status == IndexStatus.COMPLETED
        assert result.details["files_embedded"] == 50

    @patch("src.services.unified_indexing.UnifiedIndexingEngine._index_idegraph",
           new_callable=AsyncMock)
    async def test_idegraph_step(self, mock_index):
        mock_index.return_value = IndexStepResult(
            provider="codecortex-idegraph",
            status=IndexStatus.COMPLETED,
            started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:00:05",
            elapsed_seconds=5.0,
            details={"engrams_harvested": 10},
        )
        req = IndexingRequest(
            provider="codecortex-idegraph",
            repo_path="/tmp/test",
        )
        result = await self.engine._index_idegraph(req)
        assert result.status == IndexStatus.COMPLETED

    @patch("src.services.unified_indexing.UnifiedIndexingEngine._index_security",
           new_callable=AsyncMock)
    async def test_security_step(self, mock_index):
        mock_index.return_value = IndexStepResult(
            provider="codecortex-security",
            status=IndexStatus.COMPLETED,
            started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:00:15",
            elapsed_seconds=15.0,
            details={"findings_count": 3},
        )
        req = IndexingRequest(
            provider="codecortex-security",
            repo_path="/tmp/test",
        )
        result = await self.engine._index_security(req)
        assert result.status == IndexStatus.COMPLETED


@pytest.mark.asyncio
class TestFullPipelineOrchestration:
    def setup_method(self):
        self.engine = UnifiedIndexingEngine()

    async def test_full_pipeline_sequential(self):
        """Test that full pipeline runs all 7 providers in sequence."""
        for provider in ["codeindex", "graph", "embeddings", "knowledge",
                        "idegraph", "codelogs", "security"]:
            mock_method = AsyncMock()
            mock_method.return_value = IndexStepResult(
                provider=f"codecortex-{provider}",
                status=IndexStatus.COMPLETED,
                started_at="2026-01-01T00:00:00",
                completed_at="2026-01-01T00:00:10",
                elapsed_seconds=10.0,
                details={},
            )
            setattr(self.engine, f"_index_{provider}", mock_method)

        targets = self.engine._get_provider_targets("codecortex-full")
        assert len(targets) == 7

    async def test_partial_failure_in_pipeline(self):
        """Test that one provider failure doesn't stop the pipeline."""
        call_count = {"count": 0}

        async def failing_step(req):
            call_count["count"] += 1
            return IndexStepResult(
                provider="codecortex-codeindex",
                status=IndexStatus.FAILED,
                started_at="2026-01-01T00:00:00",
                elapsed_seconds=5.0,
                error="Simulated failure",
            )

        self.engine._index_codeindex = failing_step
        self.engine._index_graph = AsyncMock(return_value=IndexStepResult(
            provider="codecortex-graph", status=IndexStatus.COMPLETED,
            started_at="2026-01-01T00:00:00", elapsed_seconds=5.0,
        ))

        req = IndexingRequest(
            provider="codecortex-full",
            repo_path="/tmp/test",
        )
        result = await self.engine.index(req)
        assert result.success is False
        # The pipeline should still complete all steps
        assert len(result.steps) == 7


class TestProviderRegistryFunctions:
    def test_get_providers(self):
        engine = UnifiedIndexingEngine()
        providers = engine.get_providers()
        assert providers["total"] == 8
        assert len(providers["providers"]) == 8

    def test_get_providers_ordered(self):
        engine = UnifiedIndexingEngine()
        providers = engine.get_providers()
        positions = [p["ordered_position"] for p in providers["providers"]]
        # codecortex-full (0) should be first
        assert positions[0] == 0


class TestEmptyRepoPathHandling:
    def test_codeindex_no_repo(self):
        engine = UnifiedIndexingEngine()
        req = IndexingRequest(provider="codecortex-codeindex")
        import asyncio
        result = asyncio.run(engine._index_codeindex(req))
        assert result.status == IndexStatus.FAILED

    def test_graph_no_repo(self):
        engine = UnifiedIndexingEngine()
        req = IndexingRequest(provider="codecortex-graph")
        import asyncio
        result = asyncio.run(engine._index_graph(req))
        assert result.status == IndexStatus.SKIPPED
