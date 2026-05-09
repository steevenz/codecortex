"""
/**
 * @project   CodeCortex
 * @package   Domain/Repository
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Module tools – Single Responsibility: Register and handle MCP tools for repository domain.
 */
"""

from __future__ import annotations
import json
import os
from typing import Optional, List
from mcp.server.fastmcp import FastMCP
from src.domain.coderepository.application.service import CodeRepositoryService
from src.domain.coderepository.application.git_service import GitService

from src.core import api_response, new_request_id
from src.domain.coderepository.application.registry import RegistryManager


def register_tools(mcp: FastMCP, orchestrator_factory) -> None:
    """
    Register consolidated repository tools to the FastMCP instance.
    Tool count: 6 → 5 (removed read_repo_file, use fs_read instead).

    @param mcp: FastMCP server instance
    @param orchestrator_factory: Factory function to create CortexOrchestrator instances
    """

    # -------------------------------------------------------------------------
    # 1. repo_init — Replaces: initialize_repository
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def repo_init(path: str, max_depth: Optional[int] = None) -> dict:
        """
        Initialize a local repository for CodeCortex analysis by syncing its files to the index.

        Run this FIRST before using any graph, index, or refactor tools on a new codebase.
        Respects .gitignore and .codecortexignore to exclude unwanted files.
        Hardening: Deep recursive discovery is supported, but use max_depth for massive repos.

        @param path: Absolute path to the repository root directory (e.g. "/projects/my-app")
        @param max_depth: Optional maximum directory depth to scan. (Default: full recursive)
        @return: Repository ID and initialization status. Use the returned ID for subsequent tool calls.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            res = await orchestrator.repo_service.initialize(path, max_depth=max_depth)
            return api_response(
                success=True,
                status_code=200,
                message="Repository initialized successfully",
                data={"repository_id": res},
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Error initializing repository: {str(e)}",
                data=None,
                error_code="REP_001",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 2. repo_inspect — Replaces: repo_info + repo_structure
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def repo_inspect(
        list_all: bool = False,
        include_structure: bool = False,
        sub_path: Optional[str] = None,
        depth: int = 3
    ) -> dict:
        """
        Inspect repository metadata or structure. Use this to discover available repos or explore a specific one.

        @param list_all: If True, returns a list of all repositories currently indexed.
        @param include_structure: If True, includes a file/directory tree in the response.
        @param sub_path: Optional subdirectory path to scope the structure (e.g. "src/domain").
        @param depth: Maximum structure traversal depth (default 3). Use higher values for deep exploration.
        @return: Repository metadata and optionally the filtered directory structure.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            if list_all:
                results = await orchestrator.graph_service.list_indexed_repositories(limit=100)
                return api_response(success=True, status_code=200, message="Indexed repositories listed", data=results, request_id=request_id)

            # Metadata info
            info = orchestrator.repo_service.get_info()
            metadata = json.loads(info) if isinstance(info, str) else info

            # Optional structure tree
            structure = None
            if include_structure:
                structure_raw = orchestrator.repo_service.get_structure(sub_path, depth)
                structure = json.loads(structure_raw) if isinstance(structure_raw, str) else structure_raw

            return api_response(
                success=True,
                status_code=200,
                message="Repository inspection completed",
                data={
                    "metadata": metadata,
                    "structure": structure
                },
                request_id=request_id
            )
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error inspecting repository: {str(e)}", data=None, error_code="REP_002", request_id=request_id)
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 4. git_status — Unchanged, kept as-is
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def git_status(path: str) -> dict:
        """
        Get the current Git working tree status for a repository.

        Shows modified, staged, untracked, and deleted files relative to the last commit.

        @param path: Absolute path to the repository root
        @return: Git status summary with file lists by change type (modified, staged, untracked, etc.)
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            res = orchestrator.git_service.get_repo_status(path)
            return api_response(
                success=True,
                status_code=200,
                message="Git status retrieved",
                data=res,
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Error getting git status: {str(e)}",
                data=None,
                error_code="GIT_001",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 5. git_commit — Unchanged, kept as-is
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def git_commit(path: str, message: str, files: Optional[List[str]] = None) -> dict:
        """
        Stage and commit changes to the repository.

        Stages specified files (or all changes if `files` is omitted) and creates a Git commit.
        Always use a descriptive commit message following your project's convention.

        @param path: Absolute path to the repository root
        @param message: Commit message (e.g. "feat: add payment retry logic")
        @param files: Optional list of file paths to stage. If omitted, stages all changes (".").
        @return: Commit result with hash, author, and timestamp.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            res = orchestrator.git_service.stage_and_commit(path, files or ["."], message)
            return api_response(
                success=True,
                status_code=200,
                message="Git commit successful",
                data=res,
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Error committing changes: {str(e)}",
                data=None,
                error_code="GIT_002",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()
    # -------------------------------------------------------------------------
    # 6. repo_analyze — Replaces: analyze_codebase (from main.py)
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def repo_analyze(
        path: str, 
        dry_run: bool = True, 
        max_depth: Optional[int] = None,
        include_codemap: bool = False
    ) -> dict:
        """
        Execute a full, multi-dimensional intelligence pipeline on a codebase.

        This is a 'one-shot' tool that performs:
        1. Repository Discovery & Sync (repo_init)
        2. Semantic AST Indexing (index_repo)
        3. Architectural Analysis (arch_analyze)

        @param path: Absolute path to the repository root directory
        @param dry_run: If True (default), skip database updates and analyze using existing index data. 
                        Set False to perform a fresh scan and index update before analysis.
        @param max_depth: Optional maximum directory depth for discovery (used when dry_run=False).
        @param include_codemap: If True, includes a structured map of files and symbols in the response.
        @return: Unified analysis report including architectural health and complexity metrics.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = await orchestrator.analyze(
                path, 
                request_id=request_id, 
                dry_run=dry_run, 
                max_depth=max_depth,
                include_codemap=include_codemap
            )
            return api_response(
                success=True,
                status_code=200,
                message="Codebase analysis completed",
                data=result,
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Full analysis failed: {str(e)}",
                data=None,
                error_code="REP_004",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 7. repo_codemap — Replaces: get_structured_codemap (from main.py)
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def repo_codemap(path: str) -> dict:
        """
        Generate a high-density structured map of the codebase layout and symbols.

        Shows a nested tree of folders and files, including the key classes and functions 
        defined in each file. Excellent for getting a bird's eye view of the system's logic.

        @param path: Absolute path to the repository root directory
        @return: High-density map of directories, files, and their internal symbols.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            repo_id = orchestrator.get_repo_id(path)
            if not repo_id:
                return api_response(
                    success=False,
                    status_code=404,
                    message="Repository not indexed. Run repo_init first.",
                    data=None,
                    error_code="REP_005",
                    request_id=request_id,
                )

            def _build_map():
                # Build a nested structure
                # 1. Get all directories
                dirs = orchestrator.db.conn.execute(
                    "SELECT id, name, relative_path FROM directories WHERE repository_id = ? ORDER BY relative_path",
                    (repo_id,)
                ).fetchall()

                # 2. Get all files
                files = orchestrator.db.conn.execute(
                    "SELECT id, name, directory_id FROM files WHERE repository_id = ?",
                    (repo_id,)
                ).fetchall()

                # 3. Get all key symbols
                symbols = orchestrator.db.conn.execute(
                    "SELECT id, name, symbol_type, file_id FROM symbols WHERE repository_id = ? AND symbol_type IN ('class', 'function')",
                    (repo_id,)
                ).fetchall()

                # Map construction
                tree = {}
                file_symbols = {}
                for s in symbols:
                    f_id = s['file_id']
                    if f_id not in file_symbols: file_symbols[f_id] = []
                    file_symbols[f_id].append({"id": s['id'], "name": s['name'], "type": s['symbol_type']})

                dir_files = {}
                for f in files:
                    d_id = f['directory_id']
                    if d_id not in dir_files: dir_files[d_id] = []
                    dir_files[d_id].append({
                        "id": f['id'],
                        "name": f['name'],
                        "symbols": file_symbols.get(f['id'], [])
                    })

                for d in dirs:
                    tree[d['relative_path'] or "."] = dir_files.get(d['id'], [])
                return tree

            tree = await orchestrator.graph_service.run_in_thread(_build_map)
            return api_response(
                success=True,
                status_code=200,
                message="Structured codemap generated",
                data={"codemap": tree},
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Codemap generation failed: {str(e)}",
                data=None,
                error_code="REP_006",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 8. multi_repo_sync — Sync multiple repos in one call
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def multi_repo_sync(paths: List[str], max_depth: Optional[int] = None) -> dict:
        """
        Sync multiple repositories in a single call.

        Useful for teams or monorepos with multiple projects.
        Respects CODECORTEX_MAX_REPOS env var (default: 50) to prevent overload.

        @param paths: List of absolute paths to repository root directories
        @param max_depth: Optional maximum directory depth to scan
        @return: Summary of synced and failed repositories
        """
        if not paths:
            return api_response(success=False, status_code=400, message="paths must be a non-empty list", data=None, error_code="REP_007", request_id=new_request_id())

        max_repos = int(os.getenv("CODECORTEX_MAX_REPOS", "50"))
        if len(paths) > max_repos:
            return api_response(success=False, status_code=429, message=f"max_repos exceeded: {len(paths)} > {max_repos}", data=None, error_code="REP_QUOTA", request_id=new_request_id())

        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = await orchestrator.repo_service.multi_repo_sync(
                paths, request_id=request_id, max_depth=max_depth, max_repos=max_repos
            )
            return api_response(
                success=True,
                status_code=200,
                message="Multi-repo sync completed",
                data=result,
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Multi-repo sync failed: {str(e)}",
                data=None,
                error_code="REP_008",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 9. git_audit — Scan git history for secrets
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def git_audit(path: str, limit: int = 100) -> dict:
        """
        Scan git commit history for hardcoded secrets (API keys, tokens, passwords).

        Detects patterns like API keys, private keys, AWS access keys, and GitHub tokens
        in commit diffs. Risk levels: high, medium, low.

        @param path: Absolute path to the repository root
        @param limit: Maximum number of recent commits to scan (default: 100)
        @return: Security audit results with findings and risk level
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = orchestrator.git_service.git_audit(path, repo_id=orchestrator.get_repo_id(path) or "", limit=limit)
            return api_response(
                success=True,
                status_code=200,
                message="Git audit completed",
                data=result,
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Git audit failed: {str(e)}",
                data=None,
                error_code="GIT_AUDIT_001",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 10. check_staleness — Check if indexed repo is stale
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def check_staleness(path: str) -> dict:
        """
        Check how many commits the indexed repository is behind HEAD.

        Useful for determining if re-indexing is needed.

        @param path: Absolute path to the repository root
        @return: Staleness info with commits_behind and is_stale flag
        """
        request_id = new_request_id()
        try:
            result = RegistryManager.check_staleness(path)
            return api_response(
                success=True,
                status_code=200,
                message="Staleness check completed",
                data=result,
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Staleness check failed: {str(e)}",
                data=None,
                error_code="REG_001",
                request_id=request_id,
            )

    # -------------------------------------------------------------------------
    # 11. list_repos — List all indexed repos from global registry
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def list_repos() -> dict:
        """
        List all repositories currently registered in the global registry.

        @return: List of registered repositories with path, repo_id, and stats
        """
        request_id = new_request_id()
        try:
            repos = RegistryManager.list_all()
            return api_response(
                success=True,
                status_code=200,
                message=f"Found {len(repos)} registered repositories",
                data={"repositories": repos, "count": len(repos)},
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Failed to list repos: {str(e)}",
                data=None,
                error_code="REG_002",
                request_id=request_id,
            )

    # -------------------------------------------------------------------------
    # 12. repo_sync_incremental — Git diff-based fast sync
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def repo_sync_incremental(path: str) -> dict:
        """
        Incrementally sync a repository using git diff (much faster than full sync).

        Uses `git diff --name-only HEAD` to only re-index files changed since the
        last commit. Falls back to full sync if git diff fails.

        @param path: Absolute path to the repository root
        @return: Summary of re-indexed files
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            repo_id, changed = await orchestrator.repo_service.sync_repository_incremental(
                path, request_id=request_id
            )
            return api_response(
                success=True,
                status_code=200,
                message=f"Incremental sync completed: {len(changed)} files updated",
                data={"repository_id": repo_id, "changed_files": changed, "count": len(changed)},
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Incremental sync failed: {str(e)}",
                data=None,
                error_code="REG_003",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 13. db_compact — VACUUM database to reclaim space
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def db_compact() -> dict:
        """
        Compact the CodeCortex database to reclaim disk space.

        Runs VACUUM, REINDEX, and ANALYZE on the SQLite database.
        Safe to run at any time — no data loss.
        Shows space reclaimed before/after.

        @return: Space reclaimed stats
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            from src.core.database_cleanup import compact_database

            def _compact():
                return compact_database(orchestrator.db.conn)

            result = await asyncio.to_thread(_compact)
            return api_response(
                success=True,
                status_code=200,
                message="Database compacted successfully",
                data=result,
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Database compact failed: {str(e)}",
                data=None,
                error_code="REG_004",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 14. repo_cleanup — Delete all data for a project
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def repo_cleanup(repo_id: str) -> dict:
        """
        Permanently delete ALL data for a repository/project.

        Removes: files, symbols, edges, insights, commits, and the repository record.
        Also removes from global registry (~/.codecortex/registry.json).
        IRREVERSIBLE — use with caution. Re-run repo_init to re-index.

        @param repo_id: Repository UUID to clean up
        @return: Summary of deleted data
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            from src.core.database_cleanup import cleanup_project

            def _cleanup():
                return cleanup_project(orchestrator.db.conn, repo_id)

            result = await asyncio.to_thread(_cleanup)
            deleted = result.get("total_entries", 0)
            return api_response(
                success=True,
                status_code=200,
                message=f"Cleaned up project: {deleted} entries removed",
                data=result,
                request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Cleanup failed: {str(e)}",
                data=None,
                error_code="REG_005",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()
