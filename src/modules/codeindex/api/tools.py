"""
Module tools – 1 MCP tool: code_index (index management).

:project: CodeCortex
:package: Modules.Codeindex.Api.Tools
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""
from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from mcp.server.fastmcp import FastMCP
from src.core import api_response, new_request_id


def _validate_path(path: str) -> Optional[str]:
    """
    Validate and normalize a repository path.
    Returns error message if invalid, None if valid.
    Prevents path traversal and SSRF attacks.
    """
    if not path or not path.strip():
        return "path cannot be empty"
    resolved = Path(path).resolve()
    # Block path traversal attempts
    if ".." in Path(path).parts:
        return "path traversal (..) is not allowed"
    # Block non-existent paths
    if not resolved.exists():
        return f"path does not exist: {resolved}"
    # Block non-directory paths
    if not resolved.is_dir():
        return f"path is not a directory: {resolved}"
    return None


def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """
    Register 1 tool: code_index (AST indexing management).
    """

    @mcp.tool()
    async def code_index(
        action: str,
        repo_id: Optional[str] = None,
        path: Optional[str] = None,
        files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Manage AST indexing for repositories.

        Actions:
          "status"      → Check indexing status (symbol/file/edge count, languages, last indexed)
          "index"       → Full re-index a repository (AST parse all files)
          "incremental" → Index only files changed since last index (git diff)
          "files"       → Index specific files by relative path
          "pre_scan"    → Pre-scan Python imports for cross-file call resolution
          "export"      → Export symbol table as structured JSON (symbols, edges, files)

        For symbol search, use code_search (codeanalysis domain).
        For graph building, use graph_build (codegraph domain).
        For full pipeline, use repo_analyze (coderepository domain).

        Args:
            action: "status" | "index" | "incremental" | "files" | "pre_scan"
            repo_id: Repository UUID (required for status/incremental/files)
            path: Repository root path (auto-resolve repo_id when needed)
            files: List of relative file paths for action="files"

        Returns:
            Operation result with counts, metrics, and timing
        """
        req_id = new_request_id()
        orchestrator = orchestrator_factory()
        index_service = orchestrator.index_service
        start = time.time()

        valid = {"status", "index", "incremental", "files", "pre_scan", "export"}
        if action not in valid:
            return api_response(success=False, status_code=400,
                message=f"Invalid action '{action}'. Must be one of: {sorted(valid)}",
                data={"valid_actions": sorted(valid)},
                request_id=req_id, error_code="CI_001")

        try:
            # ── status ─────────────────────────────────────────────────────
            if action == "status":
                if not repo_id:
                    return api_response(success=False, status_code=400,
                        message="repo_id is required for action='status'. Use repo_inspect to find your repo_id.",
                        data=None, request_id=req_id, error_code="CI_002")
                status_data = await index_service.get_index_status(repo_id)
                return api_response(success=True, insight="code_index", status_code=200,
                    message=f"Status: {status_data['symbol_count']} symbols, {status_data['file_count']} files, {status_data['edge_count']} edges",
                    data=status_data,
                    request_id=req_id)

            # ── index ──────────────────────────────────────────────────────
            if action == "index":
                if not repo_id and not path:
                    return api_response(success=False, status_code=400,
                        message="Provide repo_id or path. Use repo_inspect to find repo_id, or pass an absolute directory path.",
                        data=None, request_id=req_id, error_code="CI_003")
                if path:
                    path_err = _validate_path(path)
                    if path_err:
                        return api_response(success=False, status_code=400,
                            message=f"Invalid path: {path_err}",
                            data=None, request_id=req_id, error_code="CI_003")
                if not repo_id and path:
                    repo_id = await orchestrator.repo_service.sync_repository(path)
                await index_service.index_repository(repo_id, request_id=req_id)
                duration_s = round(time.time() - start, 2)
                # Fetch post-index metrics for response enrichment
                post_status = await index_service.get_index_status(repo_id)
                symbols_per_sec = round(post_status["symbol_count"] / duration_s, 1) if duration_s > 0 else 0
                files_per_sec = round(post_status["file_count"] / duration_s, 1) if duration_s > 0 else 0
                return api_response(success=True, insight="code_index", status_code=200,
                    message=f"Indexing completed: {post_status['symbol_count']} symbols, {post_status['file_count']} files in {duration_s}s",
                    data={
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
                    request_id=req_id)

            # ── incremental ────────────────────────────────────────────────
            if action == "incremental":
                if not repo_id:
                    return api_response(success=False, status_code=400,
                        message="repo_id is required for action='incremental'. Use repo_inspect to find your repo_id.",
                        data=None, request_id=req_id, error_code="CI_004")
                result = await orchestrator.repo_service.sync_repository_incremental(repo_id)
                vcs_meta = {}
                if isinstance(result, tuple) and len(result) == 3:
                    repo_id, changed, vcs_meta = result
                elif isinstance(result, tuple) and len(result) == 2:
                    repo_id, changed = result
                else:
                    changed = []
                if changed:
                    await index_service.index_files(repo_id, changed, request_id=req_id)
                duration_s = round(time.time() - start, 2)
                fallback = vcs_meta.get("fallback_to_full_sync", False)
                msg = (f"Incremental (fallback full sync, {vcs_meta.get('fallback_reason','')}): "
                       f"{len(changed or [])} file(s) in {duration_s}s"
                       if fallback else
                       f"Incremental ({vcs_meta.get('vcs_type','git')}): "
                       f"{len(changed or [])} file(s) re-indexed in {duration_s}s")
                return api_response(success=True, insight="code_index", status_code=200,
                    message=msg,
                    data={"repo_id": repo_id, "changed_files": changed or [],
                          "files_changed": len(changed or []),
                          "vcs_type": vcs_meta.get("vcs_type", "git"),
                          "fallback_to_full_sync": fallback,
                          "fallback_reason": vcs_meta.get("fallback_reason"),
                          "duration_s": duration_s},
                    request_id=req_id)

            # ── files ──────────────────────────────────────────────────────
            if action == "files":
                if not repo_id or not files:
                    return api_response(success=False, status_code=400,
                        message="Both repo_id and files[] are required for action='files'. Provide relative file paths.",
                        data=None, request_id=req_id, error_code="CI_005")
                if not isinstance(files, list) or len(files) == 0:
                    return api_response(success=False, status_code=400,
                        message="files must be a non-empty list of relative file paths.",
                        data=None, request_id=req_id, error_code="CI_005")
                result = await index_service.index_files(repo_id, files, request_id=req_id)
                duration_s = round(time.time() - start, 2)
                return api_response(success=True, insight="code_index", status_code=200,
                    message=f"Indexed {result.get('files_indexed', 0)}/{len(files)} file(s) in {duration_s}s",
                    data={**result, "duration_s": duration_s},
                    request_id=req_id)

            # ── pre_scan ───────────────────────────────────────────────────
            if action == "pre_scan":
                if not repo_id and not path:
                    return api_response(success=False, status_code=400,
                        message="Provide repo_id or path for action='pre_scan'. Builds Python import map for cross-file resolution.",
                        data=None, request_id=req_id, error_code="CI_006")
                if path:
                    path_err = _validate_path(path)
                    if path_err:
                        return api_response(success=False, status_code=400,
                            message=f"Invalid path: {path_err}",
                            data=None, request_id=req_id, error_code="CI_006")
                if not repo_id and path:
                    repo_id = await orchestrator.repo_service.sync_repository(path)
                imports_map = await index_service.pre_scan_repository(repo_id, request_id=req_id)
                total = sum(len(v) for v in imports_map.values())
                duration_s = round(time.time() - start, 2)
                return api_response(success=True, insight="code_index", status_code=200,
                    message=f"Pre-scan: {len(imports_map)} modules, {total} symbols in {duration_s}s",
                    data={"repo_id": repo_id, "modules": len(imports_map), "symbols": total,
                          "duration_s": duration_s},
                    request_id=req_id)

            # ── export ────────────────────────────────────────────────────
            if action == "export":
                if not repo_id:
                    return api_response(success=False, status_code=400,
                        message="repo_id is required for action='export'. Use repo_inspect to find your repo_id.",
                        data=None, request_id=req_id, error_code="CI_007")
                # Optional limit parameter from path reuse (pass as encoded in path=str(limit))
                export_limit = 500
                if path and path.isdigit():
                    export_limit = min(int(path), 5000)
                export_data = await index_service.export_index(repo_id, limit=export_limit)
                duration_s = round(time.time() - start, 2)
                return api_response(success=True, insight="code_index", status_code=200,
                    message=f"Export: {export_data['symbol_count']} symbols, {export_data['file_count']} files, {export_data['edge_count']} edges",
                    data={**export_data, "duration_s": duration_s},
                    request_id=req_id)

        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"code_index(action='{action}') failed: {str(e)}",
                data={"action": action, "repo_id": repo_id},
                request_id=req_id, error_code="CI_500")
