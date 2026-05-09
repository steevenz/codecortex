"""
/**
 * @project   CodeCortex
 * @package   Domain/Filesystem
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 */
"""

from __future__ import annotations
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import asyncio
from mcp.server.fastmcp import FastMCP
from src.core import api_response, new_request_id


def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """Register consolidated filesystem tools. Tool count: 6 → 5."""

    @mcp.tool()
    async def fs_tree(repo_id: str) -> Dict[str, Any]:
        """
        Get the full directory and file tree for a repository from the index.
        Use this to explore repo layout before reading or writing files.

        @param repo_id: Repository UUID (from repo_init or repo_info)
        @return: Nested JSON tree with directories and files.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            tree = orchestrator.fs_service.get_codebase_tree(repo_id)
            return api_response(success=True, status_code=200, message="File tree retrieved", data=tree, request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error retrieving tree: {str(e)}", data=None, request_id=request_id, error_code="FS_001")
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def fs_read(path: str, repo_id: str) -> Dict[str, Any]:
        """
        Read the content of a code file from the repository index.

        @param path: Relative path from repo root (e.g. "src/domain/service.py")
        @param repo_id: Repository UUID (from repo_init or repo_info)
        @return: File content string plus language and size metadata.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = orchestrator.fs_service.read_file(path, repo_id)
            if "error" in result:
                return api_response(success=False, status_code=400, message=result["error"], data=None, request_id=request_id, error_code="FS_002")
            return api_response(success=True, status_code=200, message="File read successfully", data=result, request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error reading file: {str(e)}", data=None, request_id=request_id, error_code="FS_003")
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def fs_write(path: str, content: str, repo_id: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Write or overwrite a code file. CAUTION: replaces entire file. Run dry_run=True first.

        @param path: Relative path from repo root
        @param content: Full new content to write
        @param repo_id: Repository UUID
        @param dry_run: If True (default), preview only. Set False to write.
        @return: Change summary with diff and affected line count.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = orchestrator.fs_service.write_file(path, content, repo_id, dry_run=dry_run)
            return api_response(success=True, status_code=200, message="Write operation completed", data=result, request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error writing file: {str(e)}", data=None, request_id=request_id, error_code="FS_004")
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def fs_manage(action: str, path: str, repo_id: str, dest_path: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
        """
        File lifecycle management: delete or move/rename files in the repository.

        @param action: "delete" | "move"
        @param path: Relative source path from repo root
        @param repo_id: Repository UUID
        @param dest_path: Target relative path (required for action="move")
        @param dry_run: If True (default), preview only. Set False to execute.
        @return: Operation result with status and affected index entries.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            if action == "delete":
                result = orchestrator.fs_service.delete_file(path, repo_id, dry_run=dry_run)
                msg = "Delete operation completed"
            elif action == "move":
                if not dest_path:
                    return api_response(success=False, status_code=400, message="dest_path is required for action='move'", data=None, request_id=request_id, error_code="FS_005")
                result = orchestrator.fs_service.move_file(path, dest_path, repo_id, dry_run=dry_run)
                msg = "Move operation completed"
            else:
                return api_response(success=False, status_code=400, message=f"Unknown action '{action}'. Use: 'delete' or 'move'", data=None, request_id=request_id, error_code="FS_005")
            return api_response(success=True, status_code=200, message=msg, data=result, request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error in fs_manage ({action}): {str(e)}", data=None, request_id=request_id, error_code="FS_005")
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def fs_glob(pattern: str, repo_id: str) -> Dict[str, Any]:
        """
        List files matching a glob pattern within the repository index.
        Common patterns: "**/*.py", "src/**/*.ts", "tests/**".

        @param pattern: Glob pattern to match against indexed file paths
        @param repo_id: Repository UUID
        @return: List of matching relative file paths.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = orchestrator.fs_service.list_files_glob(pattern, repo_id)
            return api_response(success=True, status_code=200, message="Files listed", data=result, request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error listing files: {str(e)}", data=None, request_id=request_id, error_code="FS_006")
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def fs_batch(operations: list, repo_id: str, dry_run: bool = True) -> dict:
        """
        Execute multiple file operations (create, write, delete, move, copy) in one call.

        Each operation: {"action": "create"|"write"|"delete"|"move"|"copy",
                         "path": "relative/path", "content": "...", "dest": "target/path"}

        @param operations: List of file operations to execute
        @param repo_id: Repository UUID
        @param dry_run: If True (default), preview only. Set False to execute.
        @return: Results for each operation with success/error status
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            from src.domain.filesystem.infrastructure.watcher import batch_file_operations
            import asyncio

            def _get_root():
                return orchestrator.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,)).fetchone()

            row = await asyncio.to_thread(_get_root)
            if not row:
                return api_response(success=False, status_code=404, message="Repository not found", data=None, request_id=request_id, error_code="FS_007")

            repo_root = Path(row["root_path"])

            if dry_run:
                results = []
                for op in operations:
                    results.append({
                        "action": op.get("action"),
                        "path": op.get("path"),
                        "dest": op.get("dest"),
                        "status": "dry_run",
                        "message": f"Would {op.get('action')} {op.get('path')}"
                    })
                return api_response(success=True, status_code=200, message=f"Batch dry-run: {len(operations)} operations",
                                     data={"results": results, "count": len(operations)}, request_id=request_id)

            results = batch_file_operations(operations, repo_root)
            success_count = sum(1 for r in results if r["success"])
            return api_response(success=True, status_code=200,
                                 message=f"Batch completed: {success_count}/{len(operations)} succeeded",
                                 data={"results": results, "count": len(operations), "success_count": success_count},
                                 request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Batch operation failed: {str(e)}",
                                 data=None, request_id=request_id, error_code="FS_008")
        finally:
            orchestrator.db.close()
