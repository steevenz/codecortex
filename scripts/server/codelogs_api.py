"""
CodeCortex Codelogs API — /v1/codelogs/* REST endpoints.

Provides comprehensive log management through HTTP:
  POST /v1/codelogs/scan       — Scan log directories
  POST /v1/codelogs/search     — Search log entries
  POST /v1/codelogs/graph      — Generate log visualization
  POST /v1/codelogs/discover   — Discover log files systematically
  POST /v1/codelogs/health     — Log health assessment
  POST /v1/codelogs/cleanup    — Remove old log files
  GET  /v1/codelogs/info       — Show configured log directories

All endpoints accept optional 'search_paths' parameter for flexible
custom log path searching, and return standardized JSON responses.

:project: CodeCortex
:package: Server.CodelogsAPI
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-API-v2.0
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.core import api_response, new_request_id

logger = logging.getLogger("CodeCortex.Server.CodelogsAPI")

router = APIRouter(prefix="/v1/codelogs", tags=["codelogs"])


# ── Request Models ───────────────────────────────────────────────

class ScanRequest(BaseModel):
    path: Optional[str] = Field(default=None, description="Project root path")
    search_paths: Optional[str] = Field(default=None, description="Comma-separated additional paths to scan")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    path: Optional[str] = Field(default=None, description="Project root path")
    search_paths: Optional[str] = Field(default=None, description="Comma-separated additional paths")
    log_levels: Optional[str] = Field(default=None, description="Comma-separated log levels (ERROR,WARN,INFO,DEBUG)")
    date_from: Optional[str] = Field(default=None, description="Start date (ISO format)")
    date_to: Optional[str] = Field(default=None, description="End date (ISO format)")
    file_pattern: str = Field(default="*.log", description="Log file pattern")
    max_results: int = Field(default=50, ge=1, le=500, description="Max results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class GraphRequest(BaseModel):
    action: str = Field(default="summary", description="summary|error-frequency|time-trend|anomalies|files|health")
    path: Optional[str] = Field(default=None, description="Project root path")
    search_paths: Optional[str] = Field(default=None, description="Comma-separated additional paths")
    days: int = Field(default=7, ge=1, description="Time window in days")
    file_pattern: str = Field(default="*.log", description="Log file pattern")
    granularity: str = Field(default="hourly", description="hourly|daily")
    max_files: int = Field(default=50, ge=1, le=500, description="Max files to scan")


class DiscoverRequest(BaseModel):
    path: Optional[str] = Field(default=None, description="Project root path")
    search_paths: Optional[str] = Field(default=None, description="Comma-separated additional paths")
    max_results: int = Field(default=200, ge=1, le=1000, description="Max files to return")
    detect_language: bool = Field(default=True, description="Enable language detection")
    detect_os: bool = Field(default=True, description="Enable OS detection")
    detect_servers: bool = Field(default=True, description="Enable server detection")
    detect_databases: bool = Field(default=True, description="Enable database detection")
    detect_dev_tools: bool = Field(default=True, description="Enable local dev tool detection (Laragon, WAMP, XAMPP, MAMP)")


class CleanupRequest(BaseModel):
    path: Optional[str] = Field(default=None, description="Project root path")
    search_paths: Optional[str] = Field(default=None, description="Comma-separated additional paths")
    days: int = Field(default=30, ge=1, description="Max age in days")
    dry_run: bool = Field(default=True, description="Dry-run mode (default: true)")


# ── Helper ───────────────────────────────────────────────────────

def _get_services(request_path: Optional[str] = None):
    from src.modules.codelogs.services.log_service import LogService, LogSearchFilter
    from src.modules.codelogs.services.loggraph_service import LogGraphService

    project_root = request_path or os.environ.get("CODECORTEX_PROJECT_ROOT") or os.getcwd()
    log_svc = LogService(project_root=project_root)
    graph_svc = LogGraphService(log_service=log_svc)
    return log_svc, graph_svc, LogSearchFilter


def _ok(message: str, data: Any, request_id: str) -> Dict[str, Any]:
    return api_response(success=True, status_code=200, message=message, data=data, request_id=request_id)


def _err(message: str, error_code: str, request_id: str, status: int = 400) -> Dict[str, Any]:
    return api_response(success=False, status_code=status, message=message, data=None, request_id=request_id, error_code=error_code)


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/scan")
async def api_scan(body: ScanRequest):
    """Scan log directories and return file metadata."""
    rid = new_request_id()
    try:
        log_svc, _, _ = _get_services(body.path)
        files = log_svc.scan_logs(search_paths=body.search_paths)
        return _ok(f"Found {len(files)} log files", {
            "total_files": len(files),
            "project_root": log_svc._project_root,
            "files": files,
        }, rid)
    except Exception as e:
        return _err(str(e), "CODELOGS_SCAN_ERROR", rid, 500)


@router.post("/search")
async def api_search(body: SearchRequest):
    """Search log entries with filters for level, time range, and text."""
    rid = new_request_id()
    try:
        log_svc, _, LogSearchFilterCls = _get_services(body.path)
        level_list = [l.strip().upper() for l in body.log_levels.split(",")] if body.log_levels else None
        filt = LogSearchFilterCls(
            query=body.query,
            log_levels=level_list,
            date_from=body.date_from,
            date_to=body.date_to,
            file_pattern=body.file_pattern,
            max_results=body.max_results,
            offset=body.offset,
        )
        entries = log_svc.search(filt, search_paths=body.search_paths)
        return _ok(f"Found {len(entries)} log entries", {
            "total_results": len(entries),
            "entries": [e.to_dict() for e in entries],
        }, rid)
    except Exception as e:
        return _err(str(e), "CODELOGS_SEARCH_ERROR", rid, 500)


@router.post("/graph")
async def api_graph(body: GraphRequest):
    """Generate log visualization data (summary, frequency, trends, anomalies)."""
    rid = new_request_id()
    try:
        _, graph_svc, _ = _get_services(body.path)
        kwargs: Dict[str, Any] = dict(
            days=body.days, file_pattern=body.file_pattern,
            max_files=body.max_files, search_paths=body.search_paths,
        )

        actions = {
            "error-frequency": lambda: graph_svc.error_frequency(**kwargs),
            "time-trend": lambda: graph_svc.time_trend(**kwargs, granularity=body.granularity),
            "anomalies": lambda: graph_svc.anomalies(**kwargs),
            "files": lambda: graph_svc.files(**kwargs),
            "health": lambda: graph_svc.health(**kwargs),
        }

        handler = actions.get(body.action)
        if handler:
            data = handler()
        else:
            data = graph_svc.summary(**kwargs)

        return _ok(f"Log graph data (mode: {body.action})", data, rid)
    except Exception as e:
        return _err(str(e), "CODELOGS_GRAPH_ERROR", rid, 500)


@router.post("/discover")
async def api_discover(body: DiscoverRequest):
    """Discover log files via systematic path collection across languages, OS, servers, databases, and local dev tools."""
    rid = new_request_id()
    try:
        _, graph_svc, _ = _get_services(body.path)
        data = graph_svc.discover(
            custom_paths=body.search_paths,
            detect_language=body.detect_language,
            detect_os=body.detect_os,
            detect_servers=body.detect_servers,
            detect_databases=body.detect_databases,
            detect_dev_tools=body.detect_dev_tools,
            max_results=body.max_results,
        )
        return _ok(f"Discovered {data.get('total_files', 0)} log files", data, rid)
    except Exception as e:
        return _err(str(e), "CODELOGS_DISCOVER_ERROR", rid, 500)


@router.post("/health")
async def api_health(body: GraphRequest):
    """Log health assessment — simplified health score and key metrics."""
    rid = new_request_id()
    try:
        _, graph_svc, _ = _get_services(body.path)
        data = graph_svc.health(
            days=body.days, file_pattern=body.file_pattern,
            max_files=body.max_files, search_paths=body.search_paths,
        )
        return _ok(f"Log health: {data.get('status', 'unknown')}", data, rid)
    except Exception as e:
        return _err(str(e), "CODELOGS_HEALTH_ERROR", rid, 500)


@router.post("/cleanup")
async def api_cleanup(body: CleanupRequest):
    """Remove old log files (dry-run by default)."""
    rid = new_request_id()
    try:
        log_svc, _, _ = _get_services(body.path)
        result = log_svc.cleanup(days=body.days, dry_run=body.dry_run, search_paths=body.search_paths)
        return _ok(result["message"], result, rid)
    except Exception as e:
        return _err(str(e), "CODELOGS_CLEANUP_ERROR", rid, 500)


@router.get("/info")
async def api_info(path: Optional[str] = Query(default=None, description="Project root path")):
    """Show configured log directories and detection diagnostics."""
    rid = new_request_id()
    try:
        log_svc, _, _ = _get_services(path)
        roots = log_svc._get_log_roots()
        collector = log_svc.path_collector
        langs = collector._detect_languages() if log_svc._project_root else []
        servers = collector._detect_servers() if log_svc._project_root else []
        databases = collector._detect_databases() if log_svc._project_root else []
        return _ok("Log system diagnostics", {
            "project_root": log_svc._project_root,
            "allowed_log_roots": list(log_svc.ALLOWED_LOG_ROOTS),
            "active_roots": roots,
            "detected_languages": langs,
            "detected_servers": servers,
            "detected_databases": databases,
            "operating_system": collector._detect_os(),
        }, rid)
    except Exception as e:
        return _err(str(e), "CODELOGS_INFO_ERROR", rid, 500)
