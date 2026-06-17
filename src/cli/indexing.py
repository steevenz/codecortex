"""
CodeCortex CLI — Unified Indexing command (7 providers, sequential/periodic).

Usage:
  codecortex indexing run <path> [--provider PROVIDER] [--mode MODE]
  codecortex indexing schedule <path> [--interval SECONDS]
  codecortex indexing stop
  codecortex indexing status
  codecortex indexing providers

:project: CodeCortex
:package: CLI.Indexing
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
"""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
from typing import Any, Dict

INDEX_COMMANDS: Dict[str, Any] = {}


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
    "codecortex-full", "codecortex-codeindex", "codecortex-graph",
    "codecortex-embeddings", "codecortex-knowledge", "codecortex-idegraph",
    "codecortex-codelogs", "codecortex-security",
]
_MODE_CHOICES = ["full", "incremental"]


def cmd_indexing_run(args_ns: argparse.Namespace) -> Dict[str, Any]:
    from src.services.unified_indexing import IndexingRequest, get_indexing_engine

    repo_path = getattr(args_ns, "repo_path", None)
    if not repo_path:
        return _err("repo_path is required", "CLI_400")

    provider = getattr(args_ns, "provider", "codecortex-full")
    mode = getattr(args_ns, "mode", "full")

    req = IndexingRequest(
        provider=provider,
        repo_path=repo_path,
        repo_id=getattr(args_ns, "repo_id", None),
        mode=mode,
        detect_modular=getattr(args_ns, "detect_modular", True),
        build_dependency_graph=getattr(args_ns, "build_dependency_graph", True),
        sequential=True,
    )

    engine = get_indexing_engine()
    try:
        result = asyncio.run(engine.index(req))
    except RuntimeError:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, engine.index(req))
            result = future.result(timeout=600)

    raw = getattr(args_ns, "json_output", False)
    if raw:
        return _ok(f"Indexing {'completed' if result.success else 'failed'}", result.to_dict())

    step_summary = []
    for s in result.steps:
        step_summary.append({
            "provider": s.provider,
            "status": s.status.value,
            "elapsed_seconds": round(s.elapsed_seconds, 2),
            "details": s.details,
            "error": s.error,
        })

    return _ok(
        f"Indexing {'completed' if result.success else 'failed'} — "
        f"{sum(1 for s in result.steps if s.status.value == 'completed')}/{len(result.steps)} steps successful",
        {
            "provider": result.provider,
            "repo_path": result.repo_path,
            "success": result.success,
            "total_elapsed_seconds": round(result.total_elapsed_seconds, 2),
            "steps": step_summary,
        },
    )


def cmd_indexing_schedule(args_ns: argparse.Namespace) -> Dict[str, Any]:
    from src.services.unified_indexing import get_indexing_engine

    repo_path = getattr(args_ns, "repo_path", None)
    if not repo_path:
        return _err("repo_path is required", "CLI_400")

    interval = getattr(args_ns, "interval", 3600)
    engine = get_indexing_engine()
    result = engine.start_scheduler(repo_path, interval_seconds=interval)
    return result


def cmd_indexing_stop(args_ns: argparse.Namespace) -> Dict[str, Any]:
    from src.services.unified_indexing import get_indexing_engine
    engine = get_indexing_engine()
    result = engine.stop_scheduler()
    return result


def cmd_indexing_status(args_ns: argparse.Namespace) -> Dict[str, Any]:
    from src.services.unified_indexing import get_indexing_engine
    engine = get_indexing_engine()
    sched = engine.scheduler_status()
    last = engine.get_last_result()

    return _ok("Indexing scheduler status", {
        "scheduler": sched,
        "last_run": last,
    })


def cmd_indexing_providers(args_ns: argparse.Namespace) -> Dict[str, Any]:
    from src.services.unified_indexing import get_indexing_engine
    engine = get_indexing_engine()
    return _ok("Available index providers (7 total)", engine.get_providers())


INDEX_COMMANDS["run"] = cmd_indexing_run
INDEX_COMMANDS["schedule"] = cmd_indexing_schedule
INDEX_COMMANDS["stop"] = cmd_indexing_stop
INDEX_COMMANDS["status"] = cmd_indexing_status
INDEX_COMMANDS["providers"] = cmd_indexing_providers


def build_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "indexing", aliases=["idx", "index", "unified-index"],
        help="Unified indexing across all 7 CodeCortex providers (sequential/periodic)",
    )
    sp = p.add_subparsers(dest="indexing_action", required=True)

    # run
    run_p = sp.add_parser("run", help="Execute unified indexing across providers")
    run_p.add_argument("repo_path", help="Repository path to index")
    run_p.add_argument("--provider", "-p", default="codecortex-full", choices=_PROVIDER_CHOICES,
                       help="Provider ID (default: codecortex-full)")
    run_p.add_argument("--mode", "-m", default="full", choices=_MODE_CHOICES,
                       help="Indexing mode: full or incremental (default: full)")
    run_p.add_argument("--repo-id", "-r", dest="repo_id", help="Repository UUID")
    run_p.add_argument("--no-modular", action="store_false", dest="detect_modular",
                       help="Disable modular detection in graph build")
    run_p.add_argument("--no-dependency-graph", action="store_false", dest="build_dependency_graph",
                       help="Disable dependency graph build")
    run_p.add_argument("--json", action="store_true", dest="json_output",
                       help="Output raw JSON")

    # schedule
    sched_p = sp.add_parser("schedule", help="Start periodic indexing scheduler")
    sched_p.add_argument("repo_path", help="Repository path to index periodically")
    sched_p.add_argument("--interval", "-i", type=int, default=3600,
                         help="Interval in seconds (default: 3600 = 1 hour, min: 60)")

    # stop
    sp.add_parser("stop", help="Stop periodic indexing scheduler")

    # status
    sp.add_parser("status", help="Show scheduler status and last run result")

    # providers
    sp.add_parser("providers", help="List all 7 available index providers")
