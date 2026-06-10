"""
CodeIndex CLI — Command-Line Interface for the CodeIndex domain.

Commands:
  status      Check indexing status (symbol/file/edge count, languages, last indexed)
  index       Full re-index a repository (AST parse all files)
  incremental Index only files changed since last index (git diff)
  files       Index specific files by relative path
  pre_scan    Pre-scan Python imports for cross-file call resolution
  export      Export symbol table as structured JSON

:project: CodeCortex
:package: Modules.Codeindex.Api.Cli
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

DOMAIN = "codeindex"
ALIASES = ["ci"]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _output(data: Any, pretty: bool = True) -> None:
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    text = json.dumps(data, **kwargs, default=str)
    buf = sys.stdout.buffer
    buf.write(text.encode("utf-8", errors="replace"))
    buf.write(b"\n")
    buf.flush()


def _ok(message: str, data: Any = None) -> Dict[str, Any]:
    return {"success": True, "status_code": 200, "message": message, "data": data}


def _err(message: str, code: str = "CI_CLI_ERROR", status: int = 400) -> Dict[str, Any]:
    return {"success": False, "status_code": status, "message": message, "data": {"explanation": f"No relevant data is available because an error occurred: {message}"}, "error_code": code}


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


@contextlib.contextmanager
def _ci_ctx():
    """Lazy orchestrator lifecycle — creates DB, yields it, closes on exit."""
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        yield orch
    finally:
        orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 1. status
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ci_status(args_ns: argparse.Namespace) -> Dict:
    """Check indexing status for a repository."""
    repo_id: str = args_ns.repo_id
    with _ci_ctx() as orch:
        status_data = _run_async(orch.index_service.get_index_status(repo_id))
        return _ok(
            f"Status: {status_data['symbol_count']} symbols, "
            f"{status_data['file_count']} files, "
            f"{status_data['edge_count']} edges",
            status_data,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. index
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ci_index(args_ns: argparse.Namespace) -> Dict:
    """Full re-index of a repository."""
    import time

    repo_id: Optional[str] = getattr(args_ns, "repo_id", None)
    path: Optional[str] = getattr(args_ns, "path", None)

    if not repo_id and not path:
        return _err("Provide --repo-id or --path", "CI_CLI_MISSING_ARG")

    with _ci_ctx() as orch:
        start = time.time()
        if not repo_id and path:
            resolved = Path(path).resolve()
            if not resolved.exists() or not resolved.is_dir():
                return _err(f"Path not found or not a directory: {path}", "CI_CLI_BAD_PATH")
            repo_id = _run_async(orch.repo_service.sync_repository(str(resolved)))

        _run_async(orch.index_service.index_repository(repo_id))
        duration_s = round(time.time() - start, 2)
        post_status = _run_async(orch.index_service.get_index_status(repo_id))
        symbols_per_sec = round(post_status["symbol_count"] / duration_s, 1) if duration_s > 0 else 0
        files_per_sec = round(post_status["file_count"] / duration_s, 1) if duration_s > 0 else 0

        return _ok(
            f"Indexing completed: {post_status['symbol_count']} symbols, "
            f"{post_status['file_count']} files in {duration_s}s",
            {
                "repo_id": repo_id,
                "symbol_count": post_status["symbol_count"],
                "file_count": post_status["file_count"],
                "edge_count": post_status["edge_count"],
                "languages": post_status["languages"],
                "duration_s": duration_s,
                "metrics": {
                    "symbols_per_sec": symbols_per_sec,
                    "files_per_sec": files_per_sec,
                },
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. incremental
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ci_incremental(args_ns: argparse.Namespace) -> Dict:
    """Index only files changed since last index (git diff)."""
    import time

    repo_id: str = args_ns.repo_id
    with _ci_ctx() as orch:
        start = time.time()
        result = _run_async(orch.repo_service.sync_repository_incremental(repo_id))
        vcs_meta = {}
        if isinstance(result, tuple) and len(result) == 3:
            repo_id, changed, vcs_meta = result
        elif isinstance(result, tuple) and len(result) == 2:
            repo_id, changed = result
        else:
            changed = []
        if changed:
            _run_async(orch.index_service.index_files(repo_id, changed))
        duration_s = round(time.time() - start, 2)
        fallback = vcs_meta.get("fallback_to_full_sync", False)
        msg = (f"Incremental (fallback full sync, {vcs_meta.get('fallback_reason','')}): "
               f"{len(changed or [])} file(s) in {duration_s}s"
               if fallback else
               f"Incremental ({vcs_meta.get('vcs_type', 'git')}): "
               f"{len(changed or [])} file(s) re-indexed in {duration_s}s")
        return _ok(msg, {
            "repo_id": repo_id,
            "changed_files": changed or [],
            "files_changed": len(changed or []),
            "vcs_type": vcs_meta.get("vcs_type", "git"),
            "fallback_to_full_sync": fallback,
            "fallback_reason": vcs_meta.get("fallback_reason"),
            "duration_s": duration_s,
        })


# ─────────────────────────────────────────────────────────────────────────────
# 4. files
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ci_files(args_ns: argparse.Namespace) -> Dict:
    """Index specific files by relative path."""
    import time

    repo_id: str = args_ns.repo_id
    files: List[str] = args_ns.files

    if not files:
        return _err("At least one file path is required", "CI_CLI_MISSING_ARG")

    with _ci_ctx() as orch:
        start = time.time()
        result = _run_async(orch.index_service.index_files(repo_id, files))
        duration_s = round(time.time() - start, 2)
        return _ok(
            f"Indexed {result.get('files_indexed', 0)}/{len(files)} file(s) in {duration_s}s",
            {**result, "duration_s": duration_s},
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. pre_scan
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ci_pre_scan(args_ns: argparse.Namespace) -> Dict:
    """Pre-scan Python imports for cross-file call resolution."""
    import time

    repo_id: Optional[str] = getattr(args_ns, "repo_id", None)
    path: Optional[str] = getattr(args_ns, "path", None)

    if not repo_id and not path:
        return _err("Provide --repo-id or --path", "CI_CLI_MISSING_ARG")

    with _ci_ctx() as orch:
        start = time.time()
        if not repo_id and path:
            resolved = Path(path).resolve()
            if not resolved.exists() or not resolved.is_dir():
                return _err(f"Path not found or not a directory: {path}", "CI_CLI_BAD_PATH")
            repo_id = _run_async(orch.repo_service.sync_repository(str(resolved)))

        imports_map = _run_async(orch.index_service.pre_scan_repository(repo_id))
        total = sum(len(v) for v in imports_map.values())
        duration_s = round(time.time() - start, 2)
        return _ok(
            f"Pre-scan: {len(imports_map)} modules, {total} symbols in {duration_s}s",
            {"repo_id": repo_id, "modules": len(imports_map), "symbols": total, "duration_s": duration_s},
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. export
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ci_export(args_ns: argparse.Namespace) -> Dict:
    """Export symbol table as structured JSON."""
    import time

    repo_id: str = args_ns.repo_id
    limit: int = getattr(args_ns, "limit", 500)

    with _ci_ctx() as orch:
        start = time.time()
        export_data = _run_async(orch.index_service.export_index(repo_id, limit=limit))
        duration_s = round(time.time() - start, 2)

        # Optional: write to file if --output specified
        output_path: Optional[str] = getattr(args_ns, "output", None)
        if output_path:
            try:
                out = Path(output_path)
                out.write_text(
                    json.dumps(export_data, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8",
                )
                return _ok(
                    f"Export saved: {export_data['symbol_count']} symbols, "
                    f"{export_data['file_count']} files → {out}",
                    {**export_data, "duration_s": duration_s, "output_file": str(out)},
                )
            except Exception as exc:
                return _err(f"Failed to write output file: {exc}", "CI_CLI_IO_ERROR", 500)

        return _ok(
            f"Export: {export_data['symbol_count']} symbols, "
            f"{export_data['file_count']} files, {export_data['edge_count']} edges",
            {**export_data, "duration_s": duration_s},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Command registry
# ─────────────────────────────────────────────────────────────────────────────

CI_COMMANDS: Dict[str, Any] = {
    "status":      cmd_ci_status,
    "index":       cmd_ci_index,
    "incremental": cmd_ci_incremental,
    "files":       cmd_ci_files,
    "pre_scan":    cmd_ci_pre_scan,
    "prescan":     cmd_ci_pre_scan,
    "export":      cmd_ci_export,
}


# ─────────────────────────────────────────────────────────────────────────────
# Argument parser builder
# ─────────────────────────────────────────────────────────────────────────────

def build_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "codeindex", aliases=["ci"],
        help="AST indexing — status, index, incremental, files, export",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
CodeIndex — AST Indexing Management

Commands:
  status      Check indexing status (symbol/file/edge count, languages, last indexed)
  index       Full re-index a repository (AST parse all files)
  incremental Index only changed files since last index (git diff)
  files       Index specific files by relative path
  pre_scan    Pre-scan Python imports for cross-file call resolution
  export      Export symbol table as structured JSON

Examples:
  codecortex ci status --repo-id <uuid>
  codecortex ci index --path /path/to/project
  codecortex ci index --repo-id <uuid>
  codecortex ci incremental --repo-id <uuid>
  codecortex ci files --repo-id <uuid> src/service.py src/models.py
  codecortex ci pre_scan --repo-id <uuid>
  codecortex ci pre_scan --path /path/to/project
  codecortex ci export --repo-id <uuid>
  codecortex ci export --repo-id <uuid> --limit 1000 --output symbols.json
        """,
    )
    sp = p.add_subparsers(dest="ci_action", required=True)

    # ── status ────────────────────────────────────────────────────────────
    stp = sp.add_parser("status", help="Check indexing status for a repository")
    stp.add_argument("--repo-id", dest="repo_id", required=True,
                     help="Repository UUID (use 'codecortex repo list' to find)")

    # ── index ─────────────────────────────────────────────────────────────
    idxp = sp.add_parser("index", help="Full re-index of a repository")
    idxp.add_argument("--repo-id", dest="repo_id", default=None,
                      help="Repository UUID (mutually exclusive with --path)")
    idxp.add_argument("--path", default=None,
                      help="Absolute path to repository root (auto-registers if not synced)")

    # ── incremental ───────────────────────────────────────────────────────
    incp = sp.add_parser("incremental", help="Index only files changed since last index")
    incp.add_argument("--repo-id", dest="repo_id", required=True,
                      help="Repository UUID")

    # ── files ─────────────────────────────────────────────────────────────
    flp = sp.add_parser("files", help="Index specific files by relative path")
    flp.add_argument("--repo-id", dest="repo_id", required=True,
                     help="Repository UUID")
    flp.add_argument("files", nargs="+",
                     help="Relative file paths to index (e.g. src/service.py src/models.py)")

    # ── pre_scan ──────────────────────────────────────────────────────────
    psp = sp.add_parser("pre_scan", aliases=["prescan"],
                        help="Pre-scan Python imports for cross-file call resolution")
    psp.add_argument("--repo-id", dest="repo_id", default=None,
                     help="Repository UUID (mutually exclusive with --path)")
    psp.add_argument("--path", default=None,
                     help="Absolute path to repository root")

    # ── export ────────────────────────────────────────────────────────────
    exp = sp.add_parser("export", help="Export symbol table as structured JSON")
    exp.add_argument("--repo-id", dest="repo_id", required=True,
                     help="Repository UUID")
    exp.add_argument("--limit", type=int, default=500, metavar="N",
                     help="Max symbols to export (default: 500, max: 5000)")
    exp.add_argument("--output", "-o", default=None, metavar="FILE",
                     help="Write output to file instead of stdout (e.g. symbols.json)")
