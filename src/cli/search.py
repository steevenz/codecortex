"""
CodeCortex CLI — Unified Search command (9 providers, 9Router-compatible).

Usage:
  codecortex search <query> [--model PROVIDER] [--type TYPE]
  codecortex search models
  codecortex s <query>
  codecortex find <query>

:project: CodeCortex
:package: CLI.Search
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
"""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
from typing import Any, Dict

SEARCH_COMMANDS: Dict[str, Any] = {}


def _output(data: Any, pretty: bool = True) -> None:
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    buf = sys.stdout.buffer
    buf.write(json.dumps(data, **kwargs, default=str).encode("utf-8", errors="replace"))
    buf.write(b"\n")
    buf.flush()


def _ok(message: str, data: Any = None) -> Dict[str, Any]:
    return {"success": True, "status_code": 200, "message": message, "data": data}


def _err(message: str, code: str = "CLI_ERROR", status: int = 400) -> Dict[str, Any]:
    return {"success": False, "status_code": status, "message": message,
            "data": None, "error_code": code}


_PROVIDER_CHOICES = [
    "codecortex-combo", "codecortex-codebase", "codecortex-repowt",
    "codecortex-filesystem", "codecortex-graph", "codecortex-idegraph",
    "codecortex-knowledge", "codecortex-crossproject", "codecortex-codeindex",
    "codecortex-agentart", "codecortex-codelogs",
]
_TYPE_CHOICES = ["all", "code", "file", "memory", "knowledge", "repo", "log"]


def cmd_search_execute(args_ns: argparse.Namespace) -> Dict[str, Any]:
    from src.services.unified_search import SearchRequest, get_search_engine, SEARCH_PROVIDERS

    query = getattr(args_ns, "query", None)
    if not query:
        return _err("query is required", "CLI_400")

    model = getattr(args_ns, "model", "codecortex-combo")
    if model not in SEARCH_PROVIDERS:
        return _err(f"Unknown provider '{model}'. Available: {list(SEARCH_PROVIDERS.keys())}", "CLI_400")

    req = SearchRequest(
        query=query, model=model,
        max_results=getattr(args_ns, "max_results", 20),
        search_type=getattr(args_ns, "search_type", "all"),
        repo_path=getattr(args_ns, "repo_path", None),
        repo_id=getattr(args_ns, "repo_id", None),
        offset=getattr(args_ns, "offset", 0),
        symbol_type=getattr(args_ns, "symbol_type", "any"),
        language=getattr(args_ns, "language", None),
        file_pattern=getattr(args_ns, "file_pattern", "*"),
        content_regex=getattr(args_ns, "content_regex", None),
        max_depth=getattr(args_ns, "max_depth", 20),
        status_filter=getattr(args_ns, "status_filter", None),
        since=getattr(args_ns, "since", None),
        artifact_type=getattr(args_ns, "artifact_type", None),
        include_signatures=not getattr(args_ns, "no_signatures", False),
        log_levels=getattr(args_ns, "log_levels", None),
        date_from=getattr(args_ns, "date_from", None),
        date_to=getattr(args_ns, "date_to", None),
        auto_index=getattr(args_ns, "auto_index", True),
        force_update=getattr(args_ns, "force_update", False),
        regraph=getattr(args_ns, "regraph", False),
        reindex=getattr(args_ns, "reindex", False),
    )

    engine = get_search_engine()
    try:
        response = asyncio.run(engine.search(req))
    except RuntimeError:
        # Event loop already running — use a new loop in a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, engine.search(req))
            response = future.result(timeout=60)

    raw = getattr(args_ns, "json_output", False)
    if raw:
        return _ok(f"Found {len(response.results)} results", response.to_dict())

    return _ok(
        f"Found {len(response.results)} results across {response.usage.get('providers_used', 0)} providers",
        {
            "provider": response.provider,
            "query": response.query,
            "total_results": len(response.results),
            "total_available": response.usage.get("total_available", 0),
            "providers_used": response.usage.get("providers_used", 0),
            "response_time_ms": response.metrics.get("response_time_ms", 0),
            "pagination": {
                "offset": response.pagination.get("offset", 0) if response.pagination else 0,
                "has_more": response.pagination.get("has_more", False) if response.pagination else False,
            } if response.pagination else None,
            "per_provider": {
                k: v.get("results_found", 0)
                for k, v in response.metrics.get("per_provider", {}).items()
            },
            "results": [
                {
                    "position": r.position, "title": r.title,
                    "display_url": r.display_url, "score": round(r.score, 3),
                    "snippet": (r.snippet or "")[:300],
                    "source_type": r.metadata.get("source_type", "unknown"),
                    "type": r.metadata.get("type", "result"),
                }
                for r in response.results
            ],
            "errors": response.errors if response.errors else None,
        },
    )


def cmd_search_models(args_ns: argparse.Namespace) -> Dict[str, Any]:
    from src.services.unified_search import SEARCH_PROVIDERS
    return _ok("Available search providers (9 total)", {
        "total": len(SEARCH_PROVIDERS),
        "providers": [
            {"id": pid, "name": info["name"], "kind": info["kind"],
             "description": info["description"]}
            for pid, info in SEARCH_PROVIDERS.items()
        ],
    })


SEARCH_COMMANDS["search"] = cmd_search_execute
SEARCH_COMMANDS["models"] = cmd_search_models


def build_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "search", aliases=["s", "find", "unified-search"],
        help="Unified search across all 9 CodeCortex providers (9Router-compatible)",
    )
    sp = p.add_subparsers(dest="search_action", required=True)

    sch = sp.add_parser("search", help="Execute unified search across 9 providers")
    sch.add_argument("query", help="Search query string")
    sch.add_argument("--model", "-m", default="codecortex-combo", choices=_PROVIDER_CHOICES,
                     help="Provider ID (default: codecortex-combo)")
    sch.add_argument("--type", "-t", dest="search_type", default="all",
                     choices=_TYPE_CHOICES, help="Search type (default: all)")
    sch.add_argument("--max-results", "-n", type=int, default=20, dest="max_results",
                     help="Maximum results (default: 20)")
    sch.add_argument("--offset", type=int, default=0, help="Pagination offset")
    sch.add_argument("--repo-path", "-p", dest="repo_path", help="Repository path")
    sch.add_argument("--repo-id", "-r", dest="repo_id", help="Repository UUID")
    sch.add_argument("--file-pattern", default="*", dest="file_pattern",
                     help="File glob pattern (default: *)")
    sch.add_argument("--content-regex", dest="content_regex", help="Content regex")
    sch.add_argument("--max-depth", type=int, default=20, dest="max_depth", help="Max depth")
    sch.add_argument("--symbol-type", default="any", dest="symbol_type",
                     choices=["any", "function", "class", "variable", "module", "method"])
    sch.add_argument("--language", "-l", help="Programming language filter")
    sch.add_argument("--status-filter", dest="status_filter",
                     help="Git status filter (modified, added, deleted, untracked)")
    sch.add_argument("--since", help="Git log since date/ref")
    sch.add_argument("--artifact-type", dest="artifact_type",
                     help=".agents artifact type (md, yml, json, py, etc.)")
    sch.add_argument("--no-signatures", action="store_true", dest="no_signatures",
                     help="Exclude function signatures from results")
    sch.add_argument("--json", action="store_true", dest="json_output",
                     help="Output raw 9Router-format JSON")
    sch.add_argument("--force-update", action="store_true", dest="force_update",
                     help="Force index update before search")
    sch.add_argument("--regraph", action="store_true",
                     help="Force graph rebuild before search")
    sch.add_argument("--reindex", action="store_true",
                     help="Force code index rebuild before search")
    sch.add_argument("--log-levels", dest="log_levels",
                     help="Comma-separated log levels (ERROR,WARN,INFO,DEBUG) for codelogs provider")
    sch.add_argument("--date-from", dest="date_from",
                     help="Start date (ISO) for codelogs time-range filter")
    sch.add_argument("--date-to", dest="date_to",
                     help="End date (ISO) for codelogs time-range filter")
    sch.add_argument("--no-auto-index", action="store_false", dest="auto_index",
                     help="Disable automatic indexing on empty data")

    sp.add_parser("models", help="List all 9 available search providers")
