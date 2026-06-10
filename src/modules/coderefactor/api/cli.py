"""
CodeRefactor CLI — Command-Line Interface for the coderefactor domain.

Commands:
  impact       Blast radius analysis for a symbol (read-only)
  rename       Semantic rename of a symbol across the codebase
  move         Move a class/function to another file
  signature    Add/remove/reorder function parameters
  extract      Extract selected lines into a new function
  inline       Inline a function at all call sites
  rename-file  Rename a file and update all imports
  rename-folder  Rename a directory and batch update imports
  move-file    Move a file to another directory, update imports
  modularize   Split a monolithic file into DDD-aligned modules

:project: CodeCortex
:package: Modules.Coderefactor.Api.Cli
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRefactor-v1.0
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

DOMAIN = "coderefactor"
ALIASES = ["refactor", "ref"]


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


def _err(message: str, code: str = "REF_CLI_ERROR", status: int = 400) -> Dict[str, Any]:
    return {"success": False, "status_code": status, "message": message, "data": None, "error_code": code}


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


@contextlib.contextmanager
def _ref_ctx():
    """Lazy orchestrator lifecycle — creates DB, yields it, closes on exit."""
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        yield orch
    finally:
        orch.db.close()


def _fmt_changes(changes: list) -> list:
    """Serialise RefactorChange dataclasses to plain dicts."""
    from dataclasses import asdict
    return [asdict(c) if hasattr(c, "__dataclass_fields__") else c for c in (changes or [])]


def _fmt_result(result) -> Dict[str, Any]:
    """Flatten RefactorResult to a serialisable dict."""
    from dataclasses import asdict
    return {
        "status": result.status,
        "message": result.message,
        "repository_id": result.repository_id,
        "action": result.action,
        "changes": _fmt_changes(result.changes),
        "blast_radius": asdict(result.blast_radius) if result.blast_radius else None,
        "commit_hash": result.commit_hash,
        "validation_result": result.validation_result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. impact
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ref_impact(args_ns: argparse.Namespace) -> Dict:
    """Blast radius analysis for a symbol (read-only)."""
    repo_id: str = args_ns.repo_id
    target: str = args_ns.target
    with _ref_ctx() as orch:
        source_file, symbol_name = _parse_target(target)
        result = _run_async(
            orch.refactor_service.analyze_impact(repo_id, symbol_name, source_file)
        )
        from dataclasses import asdict
        return _ok(result.summary, asdict(result))


# ─────────────────────────────────────────────────────────────────────────────
# 2. rename
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ref_rename(args_ns: argparse.Namespace) -> Dict:
    """Semantic rename of a symbol across the codebase."""
    repo_id: str = args_ns.repo_id
    target: str = args_ns.target
    new_name: str = args_ns.new_name
    dry_run: bool = not getattr(args_ns, "apply", False)

    if not new_name:
        return _err("--new-name is required", "REF_CLI_MISSING_ARG")

    with _ref_ctx() as orch:
        source_file, symbol_name = _parse_target(target)
        result = _run_async(
            orch.refactor_service.rename_symbol(repo_id, symbol_name, source_file, new_name, dry_run=dry_run)
        )
        data = _fmt_result(result)
        mode = "applied" if not dry_run else "preview"
        return _ok(f"rename [{mode}]: {result.message}", data)


# ─────────────────────────────────────────────────────────────────────────────
# 3. move
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ref_move(args_ns: argparse.Namespace) -> Dict:
    """Move a class/function to another file."""
    repo_id: str = args_ns.repo_id
    target: str = args_ns.target
    target_file: str = args_ns.target_file
    dry_run: bool = not getattr(args_ns, "apply", False)

    with _ref_ctx() as orch:
        source_file, symbol_name = _parse_target(target)
        result = _run_async(
            orch.refactor_service.move_code_element(repo_id, symbol_name, source_file, target_file, dry_run=dry_run)
        )
        data = _fmt_result(result)
        mode = "applied" if not dry_run else "preview"
        return _ok(f"move [{mode}]: {result.message}", data)


# ─────────────────────────────────────────────────────────────────────────────
# 4. signature
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ref_signature(args_ns: argparse.Namespace) -> Dict:
    """Add/remove/reorder function parameters."""
    repo_id: str = args_ns.repo_id
    target: str = args_ns.target
    dry_run: bool = not getattr(args_ns, "apply", False)

    changes: Dict[str, Any] = {}
    add_raw: Optional[str] = getattr(args_ns, "add_params", None)
    remove_raw: Optional[str] = getattr(args_ns, "remove_params", None)
    reorder_raw: Optional[str] = getattr(args_ns, "reorder", None)

    if add_raw:
        try:
            changes["add_params"] = json.loads(add_raw)
        except json.JSONDecodeError:
            return _err("--add-params must be valid JSON list, e.g. '[{\"name\":\"x\"}]'", "REF_CLI_BAD_JSON")
    if remove_raw:
        changes["remove_params"] = [p.strip() for p in remove_raw.split(",") if p.strip()]
    if reorder_raw:
        changes["reorder"] = [p.strip() for p in reorder_raw.split(",") if p.strip()]

    if not changes:
        return _err("Provide at least one of --add-params, --remove-params, --reorder", "REF_CLI_MISSING_ARG")

    with _ref_ctx() as orch:
        result = _run_async(
            orch.refactor_service.change_signature(repo_id, target, changes, dry_run=dry_run)
        )
        data = _fmt_result(result)
        mode = "applied" if not dry_run else "preview"
        return _ok(f"change_signature [{mode}]: {result.message}", data)


# ─────────────────────────────────────────────────────────────────────────────
# 5. extract
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ref_extract(args_ns: argparse.Namespace) -> Dict:
    """Extract selected lines into a new function."""
    repo_id: str = args_ns.repo_id
    target: str = args_ns.target
    new_name: str = args_ns.new_name
    start_line: int = args_ns.start_line
    end_line: int = args_ns.end_line
    dry_run: bool = not getattr(args_ns, "apply", False)

    if start_line >= end_line:
        return _err("--start-line must be less than --end-line", "REF_CLI_BAD_RANGE")

    changes = {"new_name": new_name, "start_line": start_line, "end_line": end_line}
    with _ref_ctx() as orch:
        result = _run_async(
            orch.refactor_service.extract_function(repo_id, target, changes, dry_run=dry_run)
        )
        data = _fmt_result(result)
        mode = "applied" if not dry_run else "preview"
        return _ok(f"extract_function [{mode}]: {result.message}", data)


# ─────────────────────────────────────────────────────────────────────────────
# 6. inline
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ref_inline(args_ns: argparse.Namespace) -> Dict:
    """Inline a function at all call sites."""
    repo_id: str = args_ns.repo_id
    target: str = args_ns.target
    dry_run: bool = not getattr(args_ns, "apply", False)

    with _ref_ctx() as orch:
        result = _run_async(
            orch.refactor_service.inline_function(repo_id, target, {}, dry_run=dry_run)
        )
        data = _fmt_result(result)
        mode = "applied" if not dry_run else "preview"
        return _ok(f"inline_function [{mode}]: {result.message}", data)


# ─────────────────────────────────────────────────────────────────────────────
# 7. rename-file
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ref_rename_file(args_ns: argparse.Namespace) -> Dict:
    """Rename a file and update all imports."""
    repo_id: str = args_ns.repo_id
    target: str = args_ns.target
    new_path: str = args_ns.new_path
    dry_run: bool = not getattr(args_ns, "apply", False)

    with _ref_ctx() as orch:
        result = _run_async(
            orch.refactor_service.rename_file(repo_id, target, new_path, dry_run=dry_run)
        )
        data = _fmt_result(result)
        mode = "applied" if not dry_run else "preview"
        return _ok(f"rename_file [{mode}]: {result.message}", data)


# ─────────────────────────────────────────────────────────────────────────────
# 8. rename-folder
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ref_rename_folder(args_ns: argparse.Namespace) -> Dict:
    """Rename a directory and batch update all imports."""
    repo_id: str = args_ns.repo_id
    target: str = args_ns.target
    new_name: str = args_ns.new_name
    dry_run: bool = not getattr(args_ns, "apply", False)

    with _ref_ctx() as orch:
        result = _run_async(
            orch.refactor_service.rename_folder(repo_id, target, new_name, dry_run=dry_run)
        )
        data = _fmt_result(result)
        mode = "applied" if not dry_run else "preview"
        return _ok(f"rename_folder [{mode}]: {result.message}", data)


# ─────────────────────────────────────────────────────────────────────────────
# 9. move-file
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ref_move_file(args_ns: argparse.Namespace) -> Dict:
    """Move a file to another directory and update imports."""
    repo_id: str = args_ns.repo_id
    target: str = args_ns.target
    target_dir: str = args_ns.target_dir
    delete_source: bool = getattr(args_ns, "delete_source", False)
    dry_run: bool = not getattr(args_ns, "apply", False)

    with _ref_ctx() as orch:
        result = _run_async(
            orch.refactor_service.move_file(repo_id, target, target_dir, delete_source=delete_source, dry_run=dry_run)
        )
        data = _fmt_result(result)
        mode = "applied" if not dry_run else "preview"
        return _ok(f"move_file [{mode}]: {result.message}", data)


# ─────────────────────────────────────────────────────────────────────────────
# 10. modularize
# ─────────────────────────────────────────────────────────────────────────────

def cmd_ref_modularize(args_ns: argparse.Namespace) -> Dict:
    """Split a monolithic file into DDD-aligned modules (AI-assisted clustering)."""
    repo_id: str = args_ns.repo_id
    target: str = args_ns.target
    target_domain: str = getattr(args_ns, "target_domain", "")
    strategy: str = getattr(args_ns, "strategy", "auto")
    dry_run: bool = not getattr(args_ns, "apply", False)

    with _ref_ctx() as orch:
        result = _run_async(
            orch.refactor_service.modularize(repo_id, target, target_domain=target_domain, strategy=strategy, dry_run=dry_run)
        )
        data = _fmt_result(result)
        mode = "applied" if not dry_run else "preview"
        return _ok(f"modularize [{mode}]: {result.message}", data)


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_target(target: str):
    """Parse target_symbol: 'file::symbol' or 'file:line' or plain path."""
    if "::" in target:
        parts = target.split("::", 1)
        return parts[0], parts[1]
    if ":" in target:
        parts = target.rsplit(":", 1)
        sym = parts[1].strip()
        return parts[0], sym if sym and not sym.isdigit() else ""
    return target, ""


# ─────────────────────────────────────────────────────────────────────────────
# Command registry
# ─────────────────────────────────────────────────────────────────────────────

REF_COMMANDS: Dict[str, Any] = {
    "impact":         cmd_ref_impact,
    "rename":         cmd_ref_rename,
    "move":           cmd_ref_move,
    "signature":      cmd_ref_signature,
    "extract":        cmd_ref_extract,
    "inline":         cmd_ref_inline,
    "rename-file":    cmd_ref_rename_file,
    "rename_file":    cmd_ref_rename_file,
    "rename-folder":  cmd_ref_rename_folder,
    "rename_folder":  cmd_ref_rename_folder,
    "move-file":      cmd_ref_move_file,
    "move_file":      cmd_ref_move_file,
    "modularize":     cmd_ref_modularize,
}

COMMANDS = REF_COMMANDS


# ─────────────────────────────────────────────────────────────────────────────
# Argument parser builder
# ─────────────────────────────────────────────────────────────────────────────

def build_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "coderefactor", aliases=["refactor", "ref"],
        help="Safe semantic refactoring — rename, move, extract, inline, modularize",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
CodeRefactor — Safe Semantic Code Refactoring

Commands:
  impact        Blast radius analysis for a symbol (read-only, always safe)
  rename        Semantic rename of a symbol across the codebase
  move          Move a class/function to another file
  signature     Add/remove/reorder function parameters
  extract       Extract selected lines into a new function
  inline        Inline a function at all call sites
  rename-file   Rename a file and update all imports across codebase
  rename-folder Rename a directory and batch update all imports
  move-file     Move a file to another directory, update imports
  modularize    Split monolithic file into DDD-aligned modules

Safety:
  All destructive commands default to --dry-run (preview mode).
  Pass --apply to execute for real. Always run 'impact' first.

Examples:
  codecortex ref impact --repo-id <uuid> src/service.py::process_order
  codecortex ref rename --repo-id <uuid> src/utils.py::calc --new-name calculate_total
  codecortex ref rename --repo-id <uuid> src/utils.py::calc --new-name calculate_total --apply
  codecortex ref move   --repo-id <uuid> src/utils.py::Helper --target-file src/helpers/core.py
  codecortex ref signature --repo-id <uuid> src/api.py::handle --add-params '[{"name":"debug","default_value":"False"}]'
  codecortex ref extract --repo-id <uuid> src/service.py --new-name validate --start-line 10 --end-line 20
  codecortex ref inline  --repo-id <uuid> src/utils.py::tiny_helper
  codecortex ref rename-file  --repo-id <uuid> src/old.py --new-path src/new_name.py
  codecortex ref rename-folder --repo-id <uuid> src/old_module --new-name new_module
  codecortex ref move-file    --repo-id <uuid> src/utils.py --target-dir src/domain/shared/
  codecortex ref modularize   --repo-id <uuid> src/monolith.py --target-domain src/domain/ --apply
        """,
    )
    sp = p.add_subparsers(dest="ref_action", required=True)

    # ── impact ────────────────────────────────────────────────────────────
    imp = sp.add_parser("impact", help="Blast radius analysis (read-only)")
    imp.add_argument("--repo-id", dest="repo_id", required=True, help="Repository UUID")
    imp.add_argument("target", help="Target in 'file.py::Symbol' or 'file.py' format")

    # ── rename ────────────────────────────────────────────────────────────
    ren = sp.add_parser("rename", help="Semantic rename of a symbol across codebase")
    ren.add_argument("--repo-id", dest="repo_id", required=True, help="Repository UUID")
    ren.add_argument("target", help="Target: 'src/utils.py::old_name'")
    ren.add_argument("--new-name", dest="new_name", required=True, help="Replacement name")
    ren.add_argument("--apply", action="store_true", help="Execute (default: preview only)")

    # ── move ──────────────────────────────────────────────────────────────
    mov = sp.add_parser("move", help="Move a class/function to another file")
    mov.add_argument("--repo-id", dest="repo_id", required=True, help="Repository UUID")
    mov.add_argument("target", help="Target: 'src/utils.py::MyClass'")
    mov.add_argument("--target-file", dest="target_file", required=True, help="Destination file path")
    mov.add_argument("--apply", action="store_true", help="Execute (default: preview only)")

    # ── signature ─────────────────────────────────────────────────────────
    sig = sp.add_parser("signature", help="Add/remove/reorder function parameters")
    sig.add_argument("--repo-id", dest="repo_id", required=True, help="Repository UUID")
    sig.add_argument("target", help="Target: 'src/api.py::handle'")
    sig.add_argument("--add-params", dest="add_params", default=None,
                     metavar="JSON", help='JSON list: \'[{"name":"x","default_value":"None"}]\'')
    sig.add_argument("--remove-params", dest="remove_params", default=None,
                     metavar="LIST", help="Comma-separated param names to remove: 'old_param,verbose'")
    sig.add_argument("--reorder", dest="reorder", default=None,
                     metavar="LIST", help="Comma-separated new param order: 'c,a,b'")
    sig.add_argument("--apply", action="store_true", help="Execute (default: preview only)")

    # ── extract ───────────────────────────────────────────────────────────
    ext = sp.add_parser("extract", help="Extract lines into a new function")
    ext.add_argument("--repo-id", dest="repo_id", required=True, help="Repository UUID")
    ext.add_argument("target", help="Source file: 'src/service.py'")
    ext.add_argument("--new-name", dest="new_name", required=True, help="Name for extracted function")
    ext.add_argument("--start-line", dest="start_line", type=int, required=True, help="First line to extract (1-indexed)")
    ext.add_argument("--end-line", dest="end_line", type=int, required=True, help="Last line to extract (inclusive)")
    ext.add_argument("--apply", action="store_true", help="Execute (default: preview only)")

    # ── inline ────────────────────────────────────────────────────────────
    inl = sp.add_parser("inline", help="Inline a function at all call sites")
    inl.add_argument("--repo-id", dest="repo_id", required=True, help="Repository UUID")
    inl.add_argument("target", help="Target: 'src/utils.py::tiny_helper'")
    inl.add_argument("--apply", action="store_true", help="Execute (default: preview only)")

    # ── rename-file ───────────────────────────────────────────────────────
    rnf = sp.add_parser("rename-file", aliases=["rename_file"],
                        help="Rename a file and update all imports")
    rnf.add_argument("--repo-id", dest="repo_id", required=True, help="Repository UUID")
    rnf.add_argument("target", help="Current file path: 'src/old_name.py'")
    rnf.add_argument("--new-path", dest="new_path", required=True, help="New file path: 'src/new_name.py'")
    rnf.add_argument("--apply", action="store_true", help="Execute (default: preview only)")

    # ── rename-folder ─────────────────────────────────────────────────────
    rnfld = sp.add_parser("rename-folder", aliases=["rename_folder"],
                          help="Rename a directory and batch update all imports")
    rnfld.add_argument("--repo-id", dest="repo_id", required=True, help="Repository UUID")
    rnfld.add_argument("target", help="Current directory path: 'src/old_module'")
    rnfld.add_argument("--new-name", dest="new_name", required=True, help="New directory name (not full path)")
    rnfld.add_argument("--apply", action="store_true", help="Execute (default: preview only)")

    # ── move-file ─────────────────────────────────────────────────────────
    mvf = sp.add_parser("move-file", aliases=["move_file"],
                        help="Move a file to another directory and update imports")
    mvf.add_argument("--repo-id", dest="repo_id", required=True, help="Repository UUID")
    mvf.add_argument("target", help="Source file path: 'src/utils.py'")
    mvf.add_argument("--target-dir", dest="target_dir", required=True,
                     help="Destination directory: 'src/domain/shared/'")
    mvf.add_argument("--delete-source", dest="delete_source", action="store_true",
                     help="Delete source file after move (default: copy only)")
    mvf.add_argument("--apply", action="store_true", help="Execute (default: preview only)")

    # ── modularize ────────────────────────────────────────────────────────
    mod = sp.add_parser("modularize", help="Split monolithic file into DDD modules")
    mod.add_argument("--repo-id", dest="repo_id", required=True, help="Repository UUID")
    mod.add_argument("target", help="Monolithic source file: 'src/monolith.py'")
    mod.add_argument("--target-domain", dest="target_domain", default="",
                     help="Target domain base path: 'src/domain/'")
    mod.add_argument("--strategy", default="auto", choices=["auto", "manual"],
                     help="Clustering strategy (default: auto)")
    mod.add_argument("--apply", action="store_true", help="Execute (default: preview only)")
