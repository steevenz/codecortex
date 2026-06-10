"""
Tools.

:project: CodeCortex
:package: Modules.Filesystem.Api.Tools
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""
from __future__ import annotations
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path
import asyncio
from mcp.server.fastmcp import FastMCP
from src.core import api_response, new_request_id, ApiError

def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """
    Register consolidated filesystem tools.
    5 tools: fs_manage, fs_search, fs_watch, fs_df, fs_audit
    """

    @mcp.tool()
    async def fs_manage(
        operation: str,
        paths: Optional[List[str]] = None,
        path: Optional[str] = None,
        content: Optional[str] = None,
        encoding: Optional[str] = None,
        operations: Optional[List[Dict[str, str]]] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        modes: Optional[List[str]] = None,
        mode: Optional[str] = None,
        owner: Optional[str] = None,
        group: Optional[str] = None,
        target: Optional[str] = None,
        link_path: Optional[str] = None,
        is_directory: bool = False,
        dry_run: bool = False,
        overwrite: bool = False,
        recursive: bool = False,
        create_parents: bool = True,
        create_dest_parents: bool = True,
        backup_existing: bool = False,
        atomic_write: bool = True,
        permissions: Optional[int] = None,
        force: bool = False,
        create_if_not_exists: bool = True,
        set_timestamps: Optional[Dict[str, str]] = None,
        action: Optional[str] = None,
        archive_path: Optional[str] = None,
        compression_level: int = 6,
        files_to_add: Optional[List[str]] = None,
        xattr_name: Optional[str] = None,
        xattr_value: Optional[str] = None,
        repo_id: Optional[str] = None,
        convert_type: Optional[str] = None,
        source_content: Optional[str] = None,
        source_format: Optional[str] = None,
        target_format: Optional[str] = None,
        convert_options: Optional[Dict[str, Any]] = None,
        max_depth: Optional[int] = None,
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """
        Unified filesystem management tool — pure file operations, no VCS.

        For Git/SVN operations, use repo_git / repo_svn in the CodeRepository domain.

        @param operation: "tree" | "tree_sync" | "read" | "write" | "append" | "delete" | "move" | "rename" | "write_batch" | "chmod" | "chown" | "symlink" | "touch" | "archive" | "xattr" | "convert"
        @param paths: For delete: list of paths; For chmod/chown: list of paths
        @param path: For write/append: source path; For archive: path to archive; For convert: source path
        @param content: For write/append: file content
        @param encoding: "utf8" (default) or "base64"
        @param operations: For move: array of {source, destination} pairs
        @param items: For write_batch: array of {path, content, encoding, overwrite, create_parents, permissions}
        @param modes: For chmod: list of octal permissions
        @param mode: For chmod: single octal permission
        @param owner: For chown: owner username or UID
        @param group: For chown: group name or GID
        @param target: For symlink: target path; For archive extract: destination; For convert: target path
        @param link_path: For symlink: where to create the link
        @param is_directory: For symlink: hint target is a directory
        @param dry_run: Simulate without changes (default false)
        @param overwrite: For write/move/archive/convert: overwrite if exists
        @param recursive: For delete: recursive delete; For chown: recursive apply
        @param create_parents: For write: create parent directories
        @param create_dest_parents: For move: create destination parents
        @param backup_existing: For write: backup before overwrite
        @param atomic_write: For write: use temp file + rename
        @param permissions: Unix permissions (e.g., 644)
        @param force: For delete: treat missing as deleted
        @param create_if_not_exists: For touch: create file if missing
        @param set_timestamps: For touch: {"access_time": "ISO8601", "modify_time": "ISO8601"}
        @param action: For archive: "list" | "extract" | "create"
        @param archive_path: For archive: path to archive file
        @param compression_level: For archive: 0-9 compression
        @param files_to_add: For archive: specific files to include
        @param xattr_name: For xattr: attribute name
        @param xattr_value: For xattr set: attribute value
        @param repo_id: Repository UUID for path resolution.
        @param convert_type: For convert: "data" | "image" | "encoding"
        @param source_content: For convert: inline content
        @param source_format: For convert: source format hint
        @param target_format: For convert: target format hint
        @param convert_options: For convert: type-specific options
        @return: Operation result with status and details.
        """
        from src.modules.filesystem.adapters.manager import DiskManager
        manager = DiskManager()
        orchestrator = orchestrator_factory()
        params: Dict[str, Any] = {"operation": operation, "dry_run": dry_run}
        if operation in ("write", "append"):
            if not path:
                return api_response(success=False, status_code=400, message="path is required for write/append", data=None, request_id=new_request_id(), error_code="FS_001")
            resolved = orchestrator.fs_service.resolve_repo_path(repo_id, path)
            params["path"] = resolved
            params["content"] = content or ""
            params["encoding"] = encoding or "utf8"
            params["overwrite"] = overwrite
            params["create_parents"] = create_parents
            params["backup_existing"] = backup_existing
            params["atomic_write"] = atomic_write
            params["permissions"] = permissions

        elif operation == "write_batch":
            if not items:
                return api_response(success=False, status_code=400, message="items is required for write_batch", data=None, request_id=new_request_id(), error_code="FS_001B")
            resolved_items = []
            for item in items:
                resolved_path = orchestrator.fs_service.resolve_repo_path(repo_id, item.get("path", ""))
                resolved_items.append({
                    "path": resolved_path,
                    "content": item.get("content", ""),
                    "encoding": item.get("encoding", "utf8"),
                    "overwrite": item.get("overwrite", overwrite),
                    "create_parents": item.get("create_parents", create_parents),
                    "permissions": item.get("permissions", permissions),
                    "backup_existing": item.get("backup_existing", False),
                    "atomic_write": item.get("atomic_write", True),
                })
            params["items"] = resolved_items
            params["overwrite"] = overwrite
            params["create_parents"] = create_parents
        elif operation == "delete":
            if not paths:
                return api_response(success=False, status_code=400, message="paths is required for delete", data=None, request_id=new_request_id(), error_code="FS_002")
            resolved_paths = []
            for p in paths:
                resolved = orchestrator.fs_service.resolve_repo_path(repo_id, p)
                resolved_paths.append(resolved)
            params["paths"] = resolved_paths
            params["recursive"] = recursive

            params["force"] = force
        elif operation in ("move", "rename"):
            if not operations:
                return api_response(success=False, status_code=400, message="operations is required for move/rename", data=None, request_id=new_request_id(), error_code="FS_003")
            resolved_ops = []
            for op in operations:
                src = op.get("source")
                dst = op.get("destination")
                if src and dst:
                    resolved_ops.append({
                        "source": orchestrator.fs_service.resolve_repo_path(repo_id, src),
                        "destination": orchestrator.fs_service.resolve_repo_path(repo_id, dst)
                    })
            params["operations"] = resolved_ops

            params["create_dest_parents"] = create_dest_parents
            params["overwrite"] = overwrite
        elif operation == "chmod":
            if not paths:
                return api_response(success=False, status_code=400, message="paths is required for chmod", data=None, request_id=new_request_id(), error_code="FS_005")
            resolved_paths = []
            for p in paths:
                resolved = orchestrator.fs_service.resolve_repo_path(repo_id, p)
                resolved_paths.append(resolved)
            params["paths"] = resolved_paths
            params["mode"] = mode or "755"
            params["modes"] = modes
            params["recursive"] = recursive

        elif operation == "chown":
            if not paths:
                return api_response(success=False, status_code=400, message="paths is required for chown", data=None, request_id=new_request_id(), error_code="FS_006")
            resolved_paths = []
            for p in paths:
                resolved = orchestrator.fs_service.resolve_repo_path(repo_id, p)
                resolved_paths.append(resolved)
            params["paths"] = resolved_paths
            params["owner"] = owner
            params["group"] = group
            params["recursive"] = recursive

        elif operation == "symlink":
            if not target or not link_path:
                return api_response(success=False, status_code=400, message="target and link_path are required for symlink", data=None, request_id=new_request_id(), error_code="FS_007")
            resolved_target = orchestrator.fs_service.resolve_repo_path(repo_id, target)
            resolved_link = orchestrator.fs_service.resolve_repo_path(repo_id, link_path)
            params["target"] = resolved_target
            params["link_path"] = resolved_link
            params["overwrite"] = overwrite
            params["is_directory"] = is_directory

        elif operation == "touch":
            resolved = orchestrator.fs_service.resolve_repo_path(repo_id, path) if path else None
            if not resolved:
                return api_response(success=False, status_code=400, message="path is required for touch", data=None, request_id=new_request_id(), error_code="FS_008")
            params["path"] = resolved
            params["create_if_not_exists"] = create_if_not_exists
            params["set_timestamps"] = set_timestamps

        elif operation == "archive":
            resolved_archive = orchestrator.fs_service.resolve_repo_path(repo_id, archive_path or path or "")
            if not resolved_archive:
                return api_response(success=False, status_code=400, message="archive_path or path is required for archive", data=None, request_id=new_request_id(), error_code="FS_009")
            params["archive_path"] = resolved_archive
            params["action"] = action or "list"
            if target:
                params["target_dir"] = orchestrator.fs_service.resolve_repo_path(repo_id, target)
            params["overwrite"] = overwrite
            params["compression_level"] = compression_level
            if files_to_add:
                params["files_to_add"] = [orchestrator.fs_service.resolve_repo_path(repo_id, f) for f in files_to_add]
        elif operation == "xattr":
            resolved = orchestrator.fs_service.resolve_repo_path(repo_id, path or "")
            if not resolved:
                return api_response(success=False, status_code=400, message="path is required for xattr", data=None, request_id=new_request_id(), error_code="FS_010")
            params["path"] = resolved
            params["action"] = action or "list"
            params["name"] = xattr_name or ""
            params["value"] = xattr_value or ""
            params["encoding"] = encoding or "utf8"
            params["recursive"] = recursive
        elif operation == "convert":
            if not target:
                return api_response(success=False, status_code=400, message="target (target_path) is required for convert", data=None, request_id=new_request_id(), error_code="FS_011")
            params["source_path"] = orchestrator.fs_service.resolve_repo_path(repo_id, path or "") if path else None
            params["target_path"] = orchestrator.fs_service.resolve_repo_path(repo_id, target)
            params["convert_type"] = convert_type or "data"
            params["source_content"] = source_content
            params["source_format"] = source_format
            params["target_format"] = target_format
            params["options"] = convert_options or {}
        elif operation == "tree":
            resolved = orchestrator.fs_service.resolve_repo_path(repo_id, path) if path else None
            params["path"] = resolved
            params["max_depth"] = max_depth
            params["include_hidden"] = include_hidden
            params["repo_id"] = repo_id
        elif operation == "tree_sync":
            from src.core.database.integrity import FileIntegrity
            resolved = orchestrator.fs_service.resolve_repo_path(repo_id, path) if path else None
            if not resolved:
                return api_response(success=False, status_code=400, message="path is required for tree_sync", data=None, request_id=new_request_id(), error_code="FS_002")
            repo_id_resolved = repo_id or orchestrator.get_repo_id(resolved)
            if not repo_id_resolved:
                return api_response(success=False, status_code=400, message="repo_id required or path must be indexed", data=None, request_id=new_request_id(), error_code="FS_002")
            fi = FileIntegrity(orchestrator.db)
            stats = fi.update_bulk(repo_id_resolved, Path(resolved), max_depth=max_depth or 10)
            disk = fi.cache_disk_usage(repo_id_resolved, resolved)
            state = fi.get_sync_state(repo_id_resolved)
            return api_response(success=True, insight="fs_manage", status_code=200,
                                message=f"Tree synced: {stats['total']} entries in {stats['duration_seconds']}s",
                                data={**stats, "disk": disk, "synced_at": state.get("sync_at")},
                                request_id=new_request_id())
        elif operation == "read":
            resolved = orchestrator.fs_service.resolve_repo_path(repo_id, path) if path else None
            if not resolved:
                return api_response(success=False, status_code=400, message="path is required for read", data=None, request_id=new_request_id(), error_code="FS_012")
            params["path"] = resolved
            params["repo_id"] = repo_id
        else:
            return api_response(success=False, status_code=400, message=f"Unknown operation: {operation}", data=None, request_id=new_request_id(), error_code="FS_004")
        request_id = new_request_id()
        try:
            raw = manager.execute(params, db=orchestrator.db, repo_id=repo_id)
            status_code = int(raw.get("status_code", 200)) if isinstance(raw, dict) else 200
            payload = raw.get("data", raw) if isinstance(raw, dict) else raw
            return api_response(
                success=bool(raw.get("success", status_code < 400)) if isinstance(raw, dict) else True,
                status_code=status_code,
                message=str(raw.get("message", f"fs_manage '{operation}' completed")) if isinstance(raw, dict) else f"fs_manage '{operation}' completed",
                data=payload,
                request_id=request_id,
                error_code=raw.get("meta", {}).get("error_code") if isinstance(raw, dict) and status_code >= 400 else None,
                details=raw.get("meta", {}).get("details") if isinstance(raw, dict) and status_code >= 400 else None,
                repo_id=repo_id,
            )
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details, repo_id=repo_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"fs_manage error: {str(e)}", data=None, request_id=request_id, error_code="FS_500", repo_id=repo_id)

    @mcp.tool()
    async def fs_search(
        root_path: Optional[str] = None,
        repo_id: Optional[str] = None,
        file_pattern: str = "*",
        file_regex: Optional[str] = None,
        content_regex: Optional[str] = None,
        content_regex_flags: str = "",
        recursive: bool = True,
        max_depth: Optional[int] = None,
        include_hidden: bool = False,
        follow_symlinks: bool = False,
        max_results: int = 100,
        include_content_snippet: bool = True,
        exclude_patterns: Optional[List[str]] = None,
        replace_text: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Search filesystem for files and directories matching patterns.

        Scans filesystem for files/directories by name patterns and/or content.
        Can search by glob pattern, regex on filenames, and/or regex in file contents.
        When replace_text is provided, performs search-and-replace on file contents.

        @param root_path: Absolute path to search from (default: current working directory).
        @param repo_id: Optional. Repository UUID for path resolution.
        @param file_pattern: Glob pattern for filenames (default: "*", all files).
        @param file_regex: Regex pattern to match against filenames.
        @param content_regex: Regex pattern to search within file contents.
        @param content_regex_flags: Regex flags (e.g., "i" for case-insensitive).
        @param recursive: Scan subdirectories recursively (default true).
        @param max_depth: Maximum directory depth to scan (default: unlimited).
        @param include_hidden: Include hidden files/dirs starting with '.' (default false).
        @param follow_symlinks: Follow symbolic links (default false).
        @param max_results: Maximum number of results to return (default: 100).
        @param include_content_snippet: Include matching lines from file contents (default true).
        @param exclude_patterns: Glob patterns to exclude from search.
        @param replace_text: If set, replace matched patterns with this text (supports \\1 groups).
        @param dry_run: When True (default), preview changes without applying.
        @return: List of matching files with paths, sizes, and content snippets.
        """
        from src.modules.filesystem.adapters.search import DiskSearch
        params: Dict[str, Any] = {
            "root_path": root_path,
            "repo_id": repo_id,
            "file_pattern": file_pattern,
            "file_regex": file_regex,
            "content_regex": content_regex,
            "content_regex_flags": content_regex_flags,
            "recursive": recursive,
            "max_depth": max_depth,
            "include_hidden": include_hidden,
            "follow_symlinks": follow_symlinks,
            "max_results": max_results,
            "include_content_snippet": include_content_snippet,
            "exclude_patterns": exclude_patterns,
            "replace_text": replace_text,
            "dry_run": dry_run,
        }
        request_id = new_request_id()
        try:
            raw = DiskSearch().search(params)
            status_code = int(raw.get("status_code", 200)) if isinstance(raw, dict) else 200
            payload = raw.get("data", raw) if isinstance(raw, dict) else raw
            pagination = None
            if isinstance(payload, dict):
                next_cursor = payload.get("next_cursor")
                has_more = payload.get("has_more")
                total = payload.get("total")
                if next_cursor is not None or has_more is not None or total is not None:
                    pagination = {
                        "next_cursor": next_cursor,
                        "has_more": bool(has_more) if has_more is not None else None,
                        "total": total,
                        "limit": max_results,
                    }
                    payload = {k: v for k, v in payload.items() if k not in ("next_cursor", "has_more", "total")}
            return api_response(
                success=bool(raw.get("success", status_code < 400)) if isinstance(raw, dict) else True,
                status_code=status_code,
                message=str(raw.get("message", "fs_search completed")) if isinstance(raw, dict) else "fs_search completed",
                data=payload,
                request_id=request_id,
                error_code=raw.get("meta", {}).get("error_code") if isinstance(raw, dict) and status_code >= 400 else None,
                repo_id=repo_id,
                pagination=pagination,
            )
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details, repo_id=repo_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"fs_search error: {str(e)}", data=None, request_id=request_id, error_code="FS_005", repo_id=repo_id)

    @mcp.tool()
    async def fs_watch(
        target: str,
        recursive: bool = True,
        events: Optional[List[str]] = None,
        since: Optional[str] = None,
        include_ignored: bool = False,
        format: str = "simple",
        max_changes: int = 500,
        timeout_seconds: int = 60,
    ) -> Dict[str, Any]:
        """
        Watch filesystem for changes using polling-based detection.

        Supports timestamp-based, git-based, and svn-based change detection.

        @param target: Absolute path to directory or file to watch.
        @param recursive: Watch subdirectories (default true).
        @param events: Event types to report: ["create","modify","delete","rename","attribute"]. Default all.
        @param since: ISO 8601 timestamp, "git:<revision>", or "svn:<revision>". If omitted, reports current file state.
        @param include_ignored: Include files ignored by Git/SVN in results (default false).
        @param format: "simple" (default) or "detailed" (includes content previews and diffs).
        @param max_changes: Maximum changes to report, up to 5000 (default 500).
        @param timeout_seconds: Scan timeout in seconds (default 60).
        @return: Change list with metadata and VCS status per file.
        """
        from src.modules.filesystem.adapters.watch import DiskWatcher
        params: Dict[str, Any] = {
            "target": target,
            "recursive": recursive,
            "events": events or ["create", "modify", "delete", "rename", "attribute"],
            "since": since,
            "include_ignored": include_ignored,
            "format": format,
            "max_changes": max_changes,
            "timeout_seconds": timeout_seconds,
        }
        request_id = new_request_id()
        try:
            raw = DiskWatcher.watch(params)
            status_code = int(raw.get("status_code", 200)) if isinstance(raw, dict) else 200
            payload = raw.get("data", raw) if isinstance(raw, dict) else raw
            return api_response(
                success=bool(raw.get("success", status_code < 400)) if isinstance(raw, dict) else True,
                status_code=status_code,
                message=str(raw.get("message", "fs_watch completed")) if isinstance(raw, dict) else "fs_watch completed",
                data=payload,
                request_id=request_id,
                error_code=raw.get("meta", {}).get("error_code") if isinstance(raw, dict) and status_code >= 400 else None,
            )
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"fs_watch error: {str(e)}", data=None, request_id=request_id, error_code="FS_006")

    @mcp.tool()
    async def fs_df(
        target: str,
        recursive: bool = True,
        depth: int = 10,
        unit: str = "auto",
        include_hidden: bool = False,
        exclude_patterns: Optional[List[str]] = None,
        vcs_integration: str = "none",
        aggregate_by: str = "file",
        max_items: int = 100,
    ) -> Dict[str, Any]:
        """
        Analyze disk usage with optional VCS integration.

        Calculates file/directory sizes with support for Git and SVN analysis.

        @param target: Absolute path to directory or file to analyze.
        @param recursive: Calculate recursively (default true).
        @param depth: Maximum subdirectory depth (default: unlimited).
        @param unit: "bytes", "kb", "mb", "gb", or "auto" (default: "auto").
        @param include_hidden: Include hidden files/dirs starting with '.' (default false).
        @param exclude_patterns: Glob patterns to exclude (e.g. ["*.log", "temp/"]).
        @param vcs_integration: "none" (default), "git", or "svn" — enables VCS-aware breakdown.
        @param aggregate_by: "file" (default), "extension", or "vcs_status".
        @param max_items: Maximum items to report (default: 100).
        @return: Disk usage breakdown with optional VCS analysis.
        """
        from src.modules.filesystem.adapters.df import DiskUsage
        params: Dict[str, Any] = {
            "target": target,
            "recursive": recursive,
            "depth": depth,
            "unit": unit,
            "include_hidden": include_hidden,
            "exclude_patterns": exclude_patterns,
            "vcs_integration": vcs_integration,
            "aggregate_by": aggregate_by,
            "max_items": max_items,
        }
        request_id = new_request_id()
        try:
            raw = DiskUsage.analyze(params)
            status_code = int(raw.get("status_code", 200)) if isinstance(raw, dict) else 200
            payload = raw.get("data", raw) if isinstance(raw, dict) else raw
            pagination = None
            if isinstance(payload, dict):
                next_cursor = payload.get("next_cursor")
                has_more = payload.get("has_more")
                total = payload.get("total")
                if next_cursor is not None or has_more is not None or total is not None:
                    pagination = {
                        "next_cursor": next_cursor,
                        "has_more": bool(has_more) if has_more is not None else None,
                        "total": total,
                        "limit": max_items,
                    }
                    payload = {k: v for k, v in payload.items() if k not in ("next_cursor", "has_more", "total")}
            return api_response(
                success=bool(raw.get("success", status_code < 400)) if isinstance(raw, dict) else True,
                status_code=status_code,
                message=str(raw.get("message", "fs_df completed")) if isinstance(raw, dict) else "fs_df completed",
                data=payload,
                request_id=request_id,
                error_code=raw.get("meta", {}).get("error_code") if isinstance(raw, dict) and status_code >= 400 else None,
                pagination=pagination,
            )
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"fs_df error: {str(e)}", data=None, request_id=request_id, error_code="FS_007")

    @mcp.tool()
    async def fs_audit(
        target: str,
        recursive: bool = True,
        severity: Optional[List[str]] = None,
        check_permissions: bool = True,
        check_hidden: bool = True,
        max_file_size_mb: int = 100,
        exclude_patterns: Optional[List[str]] = None,
        limit: int = 200,
    ) -> Dict[str, Any]:
        """
        Audit filesystem security — detects sensitive files, permission issues, hidden VCS.

        Scans file NAMES and METADATA only (does NOT read file contents).
        Detects: credentials, config files, backups, world-writable permissions,
        hidden VCS directories, build artifacts, large logs, and more.

        @param target: Absolute path to directory to audit.
        @param recursive: Scan subdirectories recursively (default true).
        @param severity: Filter by severity levels (default all).
        @param check_permissions: Check file permissions (default true).
        @param check_hidden: Include hidden files/dirs starting with '.' (default true).
        @param max_file_size_mb: Max file size to inspect (default 100MB).
        @param exclude_patterns: Glob patterns to exclude (default [".git",".svn","node_modules"]).
        @param limit: Maximum findings to report (default 200).
        @return: Audit findings with severity, category, path, and recommendations.
        """
        from src.modules.filesystem.adapters.audit import DiskAudit
        params: Dict[str, Any] = {
            "target": target,
            "recursive": recursive,
            "severity": severity or ["critical", "high", "medium", "low"],
            "check_permissions": check_permissions,
            "check_hidden": check_hidden,
            "max_file_size_mb": max_file_size_mb,
            "exclude_patterns": exclude_patterns or [".git", ".svn", "node_modules"],
            "limit": limit,
        }
        request_id = new_request_id()
        try:
            raw = DiskAudit.audit(params)
            status_code = int(raw.get("status_code", 200)) if isinstance(raw, dict) else 200
            payload = raw.get("data", raw) if isinstance(raw, dict) else raw
            return api_response(
                success=bool(raw.get("success", status_code < 400)) if isinstance(raw, dict) else True,
                status_code=status_code,
                message=str(raw.get("message", "fs_audit completed")) if isinstance(raw, dict) else "fs_audit completed",
                data=payload,
                request_id=request_id,
                error_code=raw.get("meta", {}).get("error_code") if isinstance(raw, dict) and status_code >= 400 else None,
            )
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"fs_audit error: {str(e)}", data=None, request_id=request_id, error_code="FS_008")
