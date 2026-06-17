"""
Unit tests for Unified Search Engine — all 9 providers.

:project: CodeCortex
:package: Tests.Unit.UnifiedSearch
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
"""
from __future__ import annotations
import os
import json
import re
import pytest
from pathlib import Path
from src.services.unified_search import (
    SearchRequest, SearchResponse, SearchResultItem,
    SEARCH_PROVIDERS, UnifiedSearchEngine, get_search_engine,
    _safe_regex_compile, _safe_regex_search, _validate_path,
    REGEX_TIMEOUT_SECONDS, REGEX_MAX_INPUT_BYTES,
)


# ── DTO Tests ────────────────────────────────────────────
class TestSearchResultItem:
    def test_creation(self):
        item = SearchResultItem(title="test", url="codecortex://test/1",
                                display_url="file.py:10", snippet="code",
                                position=1, score=0.95, metadata={"type": "function"})
        d = item.to_dict()
        assert d["title"] == "test"
        assert d["url"] == "codecortex://test/1"
        assert d["position"] == 1
        assert d["score"] == 0.95
        assert d["metadata"]["type"] == "function"
        assert "citation" in d

    def test_defaults(self):
        item = SearchResultItem(title="x", url="y")
        d = item.to_dict()
        assert d["snippet"] == ""
        assert d["score"] == 1.0
        assert d["content"] is None
        assert d["published_at"] is None


class TestSearchResponse:
    def test_to_dict(self):
        resp = SearchResponse(
            provider="codecortex-combo", query="q",
            results=[
                SearchResultItem(title="r1", url="u1", position=1, score=0.9),
                SearchResultItem(title="r2", url="u2", position=2, score=0.8),
            ],
            usage={"providers_used": 2, "total_results": 2, "search_cost_usd": 0.0},
            metrics={"response_time_ms": 100},
            pagination={"offset": 0, "limit": 20, "total": 2, "has_more": False},
        )
        d = resp.to_dict()
        assert len(d["results"]) == 2
        assert d["pagination"]["total"] == 2
        assert d["pagination"]["has_more"] is False


class TestSearchRequest:
    def test_defaults(self):
        req = SearchRequest(query="test")
        assert req.model == "codecortex-combo"
        assert req.max_results == 20
        assert req.search_type == "all"
        assert req.offset == 0

    def test_all_params(self):
        req = SearchRequest(
            query="hello", model="codecortex-repowt", max_results=10,
            search_type="repo", repo_path="/tmp", offset=5,
            status_filter="modified", commit_range="HEAD~5..HEAD",
            diff_search=True, since="2026-01-01",
            artifact_type="md", include_history=True,
        )
        assert req.status_filter == "modified"
        assert req.commit_range == "HEAD~5..HEAD"
        assert req.diff_search is True
        assert req.offset == 5


# ── Provider Registry Tests ─────────────────────────────────
class TestProviderRegistry:
    def test_nine_providers_registered(self):
        assert len(SEARCH_PROVIDERS) == 10  # 9 regular + combo

    def test_all_provider_ids(self):
        expected = {
            "codecortex-codebase", "codecortex-repowt", "codecortex-filesystem",
            "codecortex-graph", "codecortex-idegraph", "codecortex-knowledge",
            "codecortex-crossproject", "codecortex-codeindex", "codecortex-agentart",
            "codecortex-combo",
        }
        assert set(SEARCH_PROVIDERS.keys()) == expected

    def test_provider_kinds(self):
        kinds = {p["kind"] for p in SEARCH_PROVIDERS.values()}
        assert "repoSearch" in kinds
        assert "crossProjectSearch" in kinds
        assert "indexSearch" in kinds
        assert "artifactSearch" in kinds
        assert "comboSearch" in kinds

    def test_provider_params_contain_query(self):
        for pid, info in SEARCH_PROVIDERS.items():
            if pid != "codecortex-combo":
                assert "query" in info["params"], f"{pid} missing query param"


# ── ReDoS Protection Tests ─────────────────────────────────
class TestReDoSProtection:
    def test_safe_compile_valid(self):
        p = _safe_regex_compile(r"\bdef\s+\w+", re.IGNORECASE)
        assert p.pattern == r"\bdef\s+\w+"

    def test_safe_compile_too_long(self):
        with pytest.raises(ValueError, match="too long"):
            _safe_regex_compile("x" * 2001)

    def test_safe_compile_catastrophic(self):
        with pytest.raises(ValueError, match="catastrophic"):
            _safe_regex_compile(r"(.+)+")

    def test_safe_compile_star_star(self):
        with pytest.raises(ValueError, match="catastrophic"):
            _safe_regex_compile(r"([a-zA-Z]+)*")

    def test_safe_compile_invalid_regex(self):
        with pytest.raises(ValueError, match="Invalid regex"):
            _safe_regex_compile(r"[unclosed")

    def test_safe_search_truncates(self):
        p = re.compile(r"hello")
        results = _safe_regex_search(p, "hello" * 200000, max_chars=5000)
        assert len(results) > 0

    def test_safe_search_empty(self):
        p = re.compile(r"xyz_not_found")
        results = _safe_regex_search(p, "hello world")
        assert results == []


# ── Path Validation Tests ──────────────────────────────────
class TestPathValidation:
    def test_valid_path(self):
        p = _validate_path(os.getcwd())
        assert p == Path(os.getcwd()).resolve()

    def test_traversal_denied(self):
        if os.name == "nt":
            disallowed = "C:\\WINDOWS\\System32"
        else:
            disallowed = "/etc"
        with pytest.raises(ValueError, match="traversal"):
            _validate_path(disallowed)

    def test_custom_allowed_roots(self):
        p = _validate_path(os.getcwd(), allowed_roots=[os.getcwd()])
        assert p == Path(os.getcwd()).resolve()


# ── Filesystem Search Tests ───────────────────────────────
class TestFilesystemSearch:
    @pytest.mark.asyncio
    async def test_basic_content_match(self, tmp_path):
        f = tmp_path / "sample.py"
        f.write_text("def hello_world():\n    return 'hello'\n")
        engine = get_search_engine()
        req = SearchRequest(query="hello_world", model="codecortex-filesystem",
                           max_results=5, repo_path=str(tmp_path))
        items, meta, err = await engine._search_filesystem(req)
        assert err is None
        assert len(items) >= 1
        assert any("hello_world" in r.snippet for r in items)

    @pytest.mark.asyncio
    async def test_no_match(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("nothing here")
        engine = get_search_engine()
        req = SearchRequest(query="xyz_nonexistent_abc", model="codecortex-filesystem",
                           max_results=5, repo_path=str(tmp_path))
        items, meta, err = await engine._search_filesystem(req)
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_content_regex_search(self, tmp_path):
        f = tmp_path / "config.py"
        f.write_text("DATABASE_URL = 'postgresql://localhost:5432'\n")
        engine = get_search_engine()
        req = SearchRequest(query="DATABASE", content_regex=r"DATABASE_URL\s*=\s*'(.+)'",
                           model="codecortex-filesystem", max_results=5,
                           repo_path=str(tmp_path))
        items, meta, err = await engine._search_filesystem(req)
        assert err is None
        assert len(items) >= 1

    @pytest.mark.asyncio
    async def test_regex_catastrophic_rejected(self, tmp_path):
        engine = get_search_engine()
        req = SearchRequest(query="test", content_regex=r"(.+)+",
                           model="codecortex-filesystem", max_results=5,
                           repo_path=str(tmp_path))
        items, meta, err = await engine._search_filesystem(req)
        assert err is not None
        assert "catastrophic" in err.lower()

    @pytest.mark.asyncio
    async def test_max_depth_respected(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        (deep / "deep.py").write_text("x=1")
        engine = get_search_engine()
        req = SearchRequest(query="x=1", model="codecortex-filesystem",
                           max_results=5, repo_path=str(tmp_path), max_depth=2)
        items, meta, err = await engine._search_filesystem(req)
        assert len(items) == 0  # Should not reach depth 4

    @pytest.mark.asyncio
    async def test_skip_dirs_ignored(self, tmp_path):
        ng = tmp_path / "node_modules"
        ng.mkdir()
        (ng / "ignored.py").write_text("secret")
        engine = get_search_engine()
        req = SearchRequest(query="secret", model="codecortex-filesystem",
                           max_results=5, repo_path=str(tmp_path))
        items, meta, err = await engine._search_filesystem(req)
        assert len(items) == 0  # node_modules skipped


# ── Repository Working Tree Tests ────────────────────────
class TestRepoWT:
    @pytest.mark.asyncio
    async def test_non_git_dir(self, tmp_path):
        engine = get_search_engine()
        req = SearchRequest(query="test", model="codecortex-repowt",
                           max_results=5, repo_path=str(tmp_path))
        items, meta, err = await engine._search_repowt(req)
        assert err is not None
        assert "no git repo" in err.lower()


# ── Agent Artifact Search Tests ──────────────────────────
class TestAgentArtifact:
    @pytest.mark.asyncio
    async def test_no_agents_dir(self, tmp_path):
        engine = get_search_engine()
        req = SearchRequest(query="test", model="codecortex-agentart",
                           max_results=5, repo_path=str(tmp_path))
        items, meta, err = await engine._search_agentart(req)
        assert err is not None
        assert ".agents" in err.lower()

    @pytest.mark.asyncio
    async def test_search_agents_artifacts(self, tmp_path):
        agents = tmp_path / ".agents"
        agents.mkdir()
        (agents / "AGENTS.md").write_text("version: 2.0.0\nproject: TestAgent\n")
        (agents / "agents.yml").write_text("rules:\n  - always_apply: true\n")
        engine = get_search_engine()
        req = SearchRequest(query="version", model="codecortex-agentart",
                           max_results=5, repo_path=str(tmp_path))
        items, meta, err = await engine._search_agentart(req)
        assert err is None
        assert len(items) >= 1
        assert any("AGENTS.md" in r.title for r in items)

    @pytest.mark.asyncio
    async def test_artifact_type_filter(self, tmp_path):
        agents = tmp_path / ".agents"
        agents.mkdir()
        (agents / "config.yml").write_text("key: value")
        (agents / "script.py").write_text("# python code")
        engine = get_search_engine()
        req = SearchRequest(query="key", model="codecortex-agentart",
                           max_results=5, repo_path=str(tmp_path),
                           artifact_type="yml")
        items, meta, err = await engine._search_agentart(req)
        assert err is None
        assert any("config.yml" in r.title for r in items)


# ── Combo Orchestration Tests ────────────────────────────
class TestComboSearch:
    @pytest.mark.asyncio
    async def test_combo_all_providers_run(self):
        engine = get_search_engine()
        req = SearchRequest(query="test", model="codecortex-combo", max_results=3)
        resp = await engine.search(req)
        assert resp.provider == "codecortex-combo"
        assert resp.usage["total_results"] >= 0
        # All 9 providers should be attempted
        assert len(resp.metrics["per_provider"]) == 9

    @pytest.mark.asyncio
    async def test_search_type_code(self):
        engine = get_search_engine()
        req = SearchRequest(query="test", model="codecortex-combo",
                           max_results=3, search_type="code")
        resp = await engine.search(req)
        assert resp.provider == "codecortex-combo"
        # code type targets 4 providers
        per = resp.metrics["per_provider"]
        assert "codecortex-codebase" in per
        assert "codecortex-graph" in per

    @pytest.mark.asyncio
    async def test_result_positioning(self):
        engine = get_search_engine()
        req = SearchRequest(query="import", model="codecortex-combo", max_results=5)
        resp = await engine.search(req)
        positions = [r.position for r in resp.results]
        assert positions == list(range(1, len(positions) + 1))
        if len(resp.results) >= 2:
            assert resp.results[0].score >= resp.results[-1].score

    @pytest.mark.asyncio
    async def test_pagination(self):
        engine = get_search_engine()
        req = SearchRequest(query="import", model="codecortex-combo",
                           max_results=3, offset=0)
        resp = await engine.search(req)
        assert resp.pagination is not None
        assert resp.pagination["offset"] == 0
        assert resp.pagination["limit"] == 3
        assert "total" in resp.pagination
        assert "has_more" in resp.pagination

    @pytest.mark.asyncio
    async def test_result_filter(self):
        engine = get_search_engine()
        req = SearchRequest(query="import", model="codecortex-combo",
                           max_results=5,
                           result_filter={"source_type": ["filesystem"]})
        resp = await engine.search(req)
        for r in resp.results:
            assert r.metadata.get("source_type") == "filesystem"

    @pytest.mark.asyncio
    async def test_response_format_9router(self):
        engine = get_search_engine()
        req = SearchRequest(query="test", model="codecortex-codebase", max_results=3)
        resp = await engine.search(req)
        d = resp.to_dict()
        assert "provider" in d
        assert "query" in d
        assert "results" in d
        assert "usage" in d
        assert "metrics" in d
        assert "errors" in d
        if d["results"]:
            r = d["results"][0]
            assert "title" in r
            assert "url" in r
            assert "snippet" in r
            assert "score" in r
            assert "citation" in r
            assert "metadata" in r

    @pytest.mark.asyncio
    async def test_errors_captured_for_failed_providers(self):
        engine = get_search_engine()
        req = SearchRequest(query="test", model="codecortex-combo", max_results=3)
        resp = await engine.search(req)
        # Each error should have provider and message
        for e in resp.errors:
            assert "provider" in e
            assert "message" in e


# ── Engine Tests ─────────────────────────────────────────
class TestUnifiedSearchEngine:
    def test_singleton(self):
        e1 = get_search_engine()
        e2 = get_search_engine()
        assert e1 is e2

    def test_citation_format(self):
        engine = get_search_engine()
        cit = engine._build_citation("test-provider", 5)
        assert cit["provider"] == "test-provider"
        assert cit["rank"] == 5
        assert "retrieved_at" in cit

    def test_result_filter_functional(self):
        engine = get_search_engine()
        items = [
            SearchResultItem(title="a", url="x", score=0.9,
                            metadata={"source_type": "codebase", "type": "function"}),
            SearchResultItem(title="b", url="y", score=0.5,
                            metadata={"source_type": "filesystem", "type": "file"}),
        ]
        filtered = engine._apply_result_filter(items, {"source_type": ["codebase"]})
        assert len(filtered) == 1
        assert filtered[0].metadata["source_type"] == "codebase"

        filtered2 = engine._apply_result_filter(items, {"min_score": 0.7})
        assert len(filtered2) == 1
        assert filtered2[0].score == 0.9
