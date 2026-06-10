"""
Single unified code_refactor tool (code_tester pattern).
12 actions: impact, rename, move, change_signature, extract_function,
inline_function, preview, apply, rename_file, rename_folder, move_file, modularize.
Depends on: repo_index (AST+graph), filesystem (read/write), git (commit).

:project: CodeCortex
:package: Modules.Coderefactor.Api.Tools
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRefactor-v1.0
"""

from __future__ import annotations
from typing import Optional, Dict, Any, Callable
from dataclasses import asdict
from mcp.server.fastmcp import FastMCP
from src.core import api_response, new_request_id

def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """
    Register unified code_refactor tool.
    Single tool with action-based dispatch (like code_tester).

    8 actions: impact, rename, move, change_signature,
               extract_function, inline_function, preview, apply.
    """

    @mcp.tool()
    async def code_refactor(
        repo_id: str,
        action: str,
        target_symbol: str,
        changes: Optional[Dict[str, Any]] = None,
        dry_run: bool = True,
    ) -> dict:
        """
        Safe, semantic code refactoring powered by AST (Tree-Sitter) and Knowledge Graph.

        Operates on top of repo_index. Run repo_analyze first to build AST + graph.
        Always starts with dry_run=True. Use action='impact' first to assess blast radius.

        @param repo_id: Repository UUID (from repo_list).
        @param action: Refactoring operation:
            "impact"             — Blast radius analysis (read-only).
            "rename"             — Semantic rename of a symbol across all files.
            "move"               — Move a class/function to another file.
            "change_signature"   — Add/remove/reorder function parameters.
            "extract_function"   — Extract selected lines into a new function.
            "inline_function"    — Inline a function at all call sites.
            "preview"            — Show diff for any action without applying.
            "apply"              — Execute a previously previewed plan.
            "rename_file"        — Rename file, update all imports across codebase.
            "rename_folder"      — Rename directory, batch update all imports.
            "move_file"          — Move file to another directory, update imports.
            "modularize"         — Split monolithic file into DDD-aligned modules (AI-assisted clustering).
        @param target_symbol: Target in "file_path:line" or "module::name" format.
        @param changes: Action-specific change details:
            rename       → {"new_name": "newFunctionName"}
            move         → {"target_file": "src/new_location.py"}
            signature    → {"add_params": [...], "remove_params": [...]}
            extract      → {"new_name": "helperFunc", "start_line": 10, "end_line": 20}
            rename_file  → {"new_path": "src/services/new_name.py"}
            rename_folder → {"new_name": "new_module_name"}
            move_file    → {"target_dir": "src/domain/billing/services"}
            modularize   → {"target_domain": "src/domain/billing", "strategy": "auto"}
            inline   → {}
        @param dry_run: When True (default), preview changes without applying.
            Set to False to execute. Always dry_run on first call.
        @return: Refactoring result with changes, blast radius, and commit hash (if applied).
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()

        valid_actions = ("impact", "rename", "move", "change_signature",
                         "extract_function", "inline_function", "preview", "apply",
                         "rename_file", "rename_folder", "move_file", "modularize")
        if action not in valid_actions:
            return api_response(success=False, status_code=400,
                message=f"Unknown action '{action}'. Valid: {', '.join(valid_actions)}",
                data=None, request_id=request_id, error_code="REF_400")

        # ── Auto-index guard: if knowledge graph is empty, trigger indexing first ──
        try:
            idx_status = await orchestrator.index_service.get_index_status(repo_id)
            if idx_status.get("symbol_count", 0) == 0:
                await orchestrator.index_service.index_repository(repo_id)
        except Exception:
            pass  # Non-fatal — continue, service handles missing graph gracefully

        resolved_action = action
        resolved_dry = dry_run

        # preview = dry_run alias
        if action == "preview":
            resolved_action = changes.get("preview_action", "rename") if changes else "rename"
            resolved_dry = True
        # apply = execute a plan (forces dry_run=False)
        if action == "apply":
            resolved_action = changes.get("apply_action", "rename") if changes else "rename"
            resolved_dry = False

        changes_dict = changes or {}

        try:
            # Parse target_symbol: "file_path:line" or "module::name"
            source_file, symbol_name = _parse_target(target_symbol)

            if resolved_action == "impact":
                result = await orchestrator.refactor_service.analyze_impact(
                    repo_id, symbol_name, source_file)
                data = asdict(result)
                return api_response(success=True, insight="code_refactor", status_code=200,
                    message=result.summary, data=data, request_id=request_id)

            elif resolved_action == "rename":
                new_name = changes_dict.get("new_name", "")
                if not new_name:
                    return api_response(success=False, status_code=400,
                        message="changes.new_name required for rename",
                        data=None, request_id=request_id, error_code="REF_400")
                result = await orchestrator.refactor_service.rename_symbol(
                    repo_id, symbol_name, source_file, new_name, dry_run=resolved_dry)
                return _refactor_response(result, request_id)

            elif resolved_action == "move":
                target_file = changes_dict.get("target_file", "")
                if not target_file:
                    return api_response(success=False, status_code=400,
                        message="changes.target_file required for move",
                        data=None, request_id=request_id, error_code="REF_400")
                result = await orchestrator.refactor_service.move_code_element(
                    repo_id, symbol_name, source_file, target_file, dry_run=resolved_dry)
                return _refactor_response(result, request_id)

            elif resolved_action in ("change_signature", "extract_function", "inline_function"):
                svc = orchestrator.refactor_service
                if resolved_action == "change_signature":
                    result = await svc.change_signature(
                        repo_id, target_symbol, changes_dict, dry_run=resolved_dry)
                elif resolved_action == "extract_function":
                    result = await svc.extract_function(
                        repo_id, target_symbol, changes_dict, dry_run=resolved_dry)
                else:
                    result = await svc.inline_function(
                        repo_id, target_symbol, changes_dict, dry_run=resolved_dry)
                return _refactor_response(result, request_id)

            elif resolved_action == "rename_file":
                new_path = changes_dict.get("new_path", "")
                if not new_path:
                    return api_response(success=False, status_code=400,
                        message="changes.new_path required for rename_file",
                        data=None, request_id=request_id, error_code="REF_400")
                result = await orchestrator.refactor_service.rename_file(
                    repo_id, target_symbol, new_path, dry_run=resolved_dry)
                return _refactor_response(result, request_id)

            elif resolved_action == "rename_folder":
                new_name = changes_dict.get("new_name", "")
                if not new_name:
                    return api_response(success=False, status_code=400,
                        message="changes.new_name required for rename_folder",
                        data=None, request_id=request_id, error_code="REF_400")
                result = await orchestrator.refactor_service.rename_folder(
                    repo_id, target_symbol, new_name, dry_run=resolved_dry)
                return _refactor_response(result, request_id)

            elif resolved_action == "move_file":
                target_dir = changes_dict.get("target_dir", "")
                if not target_dir:
                    return api_response(success=False, status_code=400,
                        message="changes.target_dir required for move_file",
                        data=None, request_id=request_id, error_code="REF_400")
                delete_source = changes_dict.get("delete_source", False)
                result = await orchestrator.refactor_service.move_file(
                    repo_id, target_symbol, target_dir, delete_source=delete_source, dry_run=resolved_dry)
                return _refactor_response(result, request_id)

            elif resolved_action == "modularize":
                target_domain = changes_dict.get("target_domain", "")
                strategy = changes_dict.get("strategy", "auto")
                result = await orchestrator.refactor_service.modularize(
                    repo_id, target_symbol, target_domain=target_domain, strategy=strategy, dry_run=resolved_dry)
                return _refactor_response(result, request_id)

            else:
                return api_response(success=False, status_code=400,
                    message=f"Unhandled action: {resolved_action}",
                    data=None, request_id=request_id, error_code="REF_400")

        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"Refactoring failed ({resolved_action}): {str(e)}",
                data=None, error_code="REF_500", request_id=request_id)
        finally:
            if action not in ("impact",):
                orchestrator.db.close()

    def _parse_target(target: str) -> tuple:
        """Parse target_symbol into (source_file, symbol_name).

        Supports formats:
          - "path/to/file.py:42"        → file + line (line ignored for now)
          - "path/to/file.py::FunctionName" → file + symbol
          - "module::FunctionName"       → module path + symbol
        """
        if "::" in target:
            parts = target.split("::", 1)
            source_file = parts[0]
            symbol_name = parts[1]
        elif ":" in target:
            parts = target.rsplit(":", 1)
            source_file = parts[0]
            symbol_name = parts[1] if parts[1].strip() and not parts[1].strip().isdigit() else ""
        else:
            source_file = target
            symbol_name = ""
        return source_file, symbol_name

    def _refactor_response(result, request_id: str) -> dict:
        """Convert RefactorResult to API response."""
        data = {
            "status": result.status,
            "message": result.message,
            "repository_id": result.repository_id,
            "action": result.action,
            "changes": [asdict(c) for c in result.changes] if result.changes else [],
            "blast_radius": asdict(result.blast_radius) if result.blast_radius else None,
            "commit_hash": result.commit_hash,
            "validation_result": result.validation_result,
        }
        status_code = 200 if result.status != "error" else 400
        return api_response(success=result.status != "error", status_code=status_code,
                            message=result.message, data=data, request_id=request_id)
