"""
CodeCortex Unified Search API — 9Router-compatible /v1/search endpoint.

POST /v1/search       — Orchestrate all 9 CodeCortex search providers.
GET  /v1/models/search — List available search providers (9Router discovery).
GET  /v1/models/info   — Get per-provider parameters and pricing.

:project: CodeCortex
:package: Server.SearchAPI
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-API-v1.0
"""
from __future__ import annotations
import time
import logging
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.services.unified_search import (
    SearchRequest,
    SearchResponse,
    SEARCH_PROVIDERS,
    get_search_engine,
)
from src.core import api_response, new_request_id

logger = logging.getLogger("CodeCortex.Server.SearchAPI")


class SearchAPIRequest(BaseModel):
    model: str = Field(default="codecortex-combo",
                       description="Search provider ID (9 options + combo).")
    provider: Optional[str] = Field(default=None, description="Alias for 'model'.")
    query: str = Field(..., min_length=1, description="Search query string.")
    max_results: int = Field(default=20, ge=1, le=200, description="Maximum results.")
    search_type: str = Field(default="all",
                              description="all|code|file|memory|knowledge|repo.")
    repo_path: Optional[str] = Field(default=None, description="Repository path.")
    repo_id: Optional[str] = Field(default=None, description="Repository UUID.")
    offset: int = Field(default=0, ge=0, description="Pagination offset.")
    symbol_type: str = Field(default="any", description="Symbol type filter.")
    language: Optional[str] = Field(default=None, description="Programming language filter.")
    file_pattern: str = Field(default="*", description="File glob pattern(s).")
    content_regex: Optional[str] = Field(default=None, description="Content regex (ReDoS-safe).")
    recursive: bool = Field(default=True, description="Search recursively.")
    max_depth: int = Field(default=20, ge=1, le=50, description="Max directory depth.")
    search_mode: str = Field(default="keyword", description="keyword|glob|regex|fuzzy|boolean.")
    project_name: Optional[str] = Field(default=None, description="IDE project filter.")
    ide_name: Optional[str] = Field(default=None, description="IDE filter.")
    knowledge_type: Optional[str] = Field(default=None, description="Knowledge type filter.")
    direction: str = Field(default="both", description="Graph direction.")
    relation_type: Optional[str] = Field(default=None, description="Graph relation filter.")
    graph_max_depth: int = Field(default=3, ge=1, le=10, description="Graph traversal depth.")
    status_filter: Optional[str] = Field(default=None, description="Git status filter.")
    commit_range: Optional[str] = Field(default=None, description="Git commit range.")
    diff_search: bool = Field(default=False, description="Search git diffs.")
    since: Optional[str] = Field(default=None, description="Since date/timestamp.")
    min_references: int = Field(default=1, ge=1, description="Min cross-project refs.")
    include_signatures: bool = Field(default=True, description="Include function signatures.")
    artifact_type: Optional[str] = Field(default=None, description=".agents artifact type.")
    version: Optional[str] = Field(default=None, description="Artifact version filter.")
    include_history: bool = Field(default=False, description="Include artifact history.")
    auto_index: bool = Field(default=True, description="Auto-index on empty/stale data.")
    force_update: bool = Field(default=False, description="Force index update.")
    regraph: bool = Field(default=False, description="Force graph rebuild.")
    reindex: bool = Field(default=False, description="Force code index rebuild.")
    result_filter: Optional[Dict[str, Any]] = Field(default=None,
                                                     description="Result filter criteria.")


async def search_endpoint(body: SearchAPIRequest) -> Dict[str, Any]:
    t0 = time.monotonic()
    provider = body.provider or body.model

    # Path traversal validation
    if body.repo_path:
        try:
            from pathlib import Path
            resolved = Path(body.repo_path).resolve()
            if not resolved.exists():
                return api_response(
                    success=False, status_code=400,
                    message=f"Repository path does not exist: {body.repo_path}",
                    data=None, request_id=new_request_id(), error_code="SEARCH_003",
                )
            # Prevent traversal outside home directory
            home = Path.home().resolve()
            if not str(resolved).startswith(str(home)):
                return api_response(
                    success=False, status_code=403,
                    message=f"Path traversal denied: {body.repo_path}",
                    data=None, request_id=new_request_id(), error_code="SEARCH_004",
                )
        except Exception as e:
            return api_response(
                success=False, status_code=400,
                message=f"Invalid repo_path: {e}",
                data=None, request_id=new_request_id(), error_code="SEARCH_005",
            )

    req = SearchRequest(
        query=body.query, model=provider, max_results=body.max_results,
        search_type=body.search_type, repo_path=body.repo_path,
        repo_id=body.repo_id, offset=body.offset,
        symbol_type=body.symbol_type, language=body.language,
        file_pattern=body.file_pattern, content_regex=body.content_regex,
        recursive=body.recursive, max_depth=body.max_depth,
        search_mode=body.search_mode, project_name=body.project_name,
        ide_name=body.ide_name, knowledge_type=body.knowledge_type,
        direction=body.direction, relation_type=body.relation_type,
        graph_max_depth=body.graph_max_depth,
        status_filter=body.status_filter, commit_range=body.commit_range,
        diff_search=body.diff_search, since=body.since,
        min_references=body.min_references, include_signatures=body.include_signatures,
        artifact_type=body.artifact_type, version=body.version,
        include_history=body.include_history, result_filter=body.result_filter,
        auto_index=body.auto_index, force_update=body.force_update,
        regraph=body.regraph, reindex=body.reindex,
    )

    if provider not in SEARCH_PROVIDERS:
        return api_response(
            success=False, status_code=400,
            message=f"Unknown provider '{provider}'. Available: {list(SEARCH_PROVIDERS.keys())}",
            data=None, request_id=new_request_id(), error_code="SEARCH_001",
        )

    engine = get_search_engine()
    result = await engine.search(req)
    elapsed = int((time.monotonic() - t0) * 1000)

    response_data = result.to_dict()
    response_data.setdefault("metrics", {})["api_overhead_ms"] = (
        elapsed - response_data.get("metrics", {}).get("response_time_ms", 0)
    )
    return response_data


async def models_endpoint() -> Dict[str, Any]:
    models_list = []
    for pid, info in SEARCH_PROVIDERS.items():
        models_list.append({
            "id": pid, "name": info["name"], "kind": info["kind"],
            "description": info["description"], "owned_by": info["owned_by"],
            "params": info["params"],
        })
    return {"object": "list", "data": models_list}


async def models_info_endpoint(id: str) -> Dict[str, Any]:
    if id not in SEARCH_PROVIDERS:
        return api_response(
            success=False, status_code=404,
            message=f"Provider '{id}' not found",
            data=None, request_id=new_request_id(), error_code="SEARCH_002",
        )
    info = SEARCH_PROVIDERS[id]
    return {
        "id": info["id"], "name": info["name"], "kind": info["kind"],
        "description": info["description"], "owned_by": info["owned_by"],
        "params": info["params"],
        "pricing": {"type": "free", "cost_per_query_usd": 0.0},
    }
