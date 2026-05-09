"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeIndex
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Module tools – Single Responsibility: Register and handle MCP tools for codeindex domain.
 */
"""

from __future__ import annotations
import asyncio
from typing import Optional
from mcp.server.fastmcp import FastMCP
from src.domain.codeindex.application.service import CodeIndexService
from src.core.database import DatabaseManager

from src.core import api_response, new_request_id

def register_tools(mcp: FastMCP, orchestrator_factory) -> None:
    """
    Register all codeindex-related tools to the FastMCP instance.

    :param mcp: FastMCP server instance
    :param orchestrator_factory: Factory function to create CortexOrchestrator instances
    """

    @mcp.tool()
    async def index_repo(repo_id: str, include_codemap: bool = False) -> dict:
        """
        Index all code files in a repository using Tree-Sitter to extract symbols (functions, classes, variables).

        Run this AFTER repo_init to populate the symbol index for graph_find_symbols and graph_query.
        Required before any graph_build or graph_query operations will return results.
        Hardening: Files larger than 5MB are automatically skipped to ensure parser stability.

        @param repo_id: Repository UUID (from repo_init or repo_info)
        @param include_codemap: If True, returns a structured map of the codebase after indexing.
        @return: Indexing result with file count and extracted symbol count.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            await asyncio.to_thread(orchestrator.index_service.index_repository, repo_id, request_id=request_id)
            
            data = {"repository_id": repo_id}
            if include_codemap:
                data["codemap"] = await orchestrator._build_codemap(repo_id)

            return api_response(
                success=True,
                status_code=200,
                message=f"Successfully indexed repository: {repo_id}",
                data=data,
                request_id=request_id
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Error indexing repository: {str(e)}",
                data=None,
                error_code="IDX_001",
                request_id=request_id
            )
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def index_file(repo_id: str, file_id: str) -> dict:
        """
        Re-index a single file to update its symbols after a code change.

        Use this for incremental updates instead of running the full index_repo after every edit.
        The file must already exist in the repository index (use fs_tree or fs_glob to get file IDs).

        @param repo_id: Repository UUID
        @param file_id: File UUID (from the repository index — use fs_tree to discover)
        @return: Symbol extraction result with extracted function and class count.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        service = orchestrator.index_service
        try:
            # Get file path from database
            def _get_file_info():
                cursor = service.db.conn.execute("""
                    SELECT d.relative_path, f.name 
                    FROM files f
                    JOIN directories d ON f.directory_id = d.id
                    WHERE f.id = ?
                """, (file_id,))
                return cursor.fetchone()
                
            file_info = await asyncio.to_thread(_get_file_info)
            if not file_info:
                return api_response(
                    success=False,
                    status_code=404,
                    message=f"File not found: {file_id}",
                    data=None,
                    error_code="IDX_002",
                    request_id=request_id
                )
            
            # Read file content
            from pathlib import Path
            def _get_repo_root():
                return service.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,)).fetchone()['root_path']
            
            repo_root = await asyncio.to_thread(_get_repo_root)
            dir_path = file_info['relative_path'] if file_info['relative_path'] else ''
            file_rel_path = f"{dir_path}/{file_info['name']}" if dir_path else file_info['name']
            file_path = Path(repo_root) / file_rel_path
            
            if not file_path.exists():
                return api_response(
                    success=False,
                    status_code=404,
                    message=f"File not found on disk: {file_rel_path}",
                    data=None,
                    error_code="IDX_003",
                    request_id=request_id
                )
            
            # TreeSitterParser primary path
            parsed = await asyncio.to_thread(service.index_file_with_tree_sitter, repo_id, file_id, file_path)
            symbol_count = 0
            if "error" not in parsed:
                symbol_count = len(parsed.get("functions", [])) + len(parsed.get("classes", []))
            else:
                # Fallback to legacy BaseStrategy path
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                symbol_count = await asyncio.to_thread(service.index_file, repo_id, file_id, file_rel_path, content)
                
            return api_response(
                success=True,
                status_code=200,
                message=f"Successfully indexed file: {file_rel_path}",
                data={
                    "file_id": file_id,
                    "symbol_count": symbol_count
                },
                request_id=request_id
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Error indexing file: {str(e)}",
                data=None,
                error_code="IDX_004",
                request_id=request_id
            )
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def semantic_search(repo_id: str, query: str, top_k: int = 10) -> dict:
        """
        Search code using natural language understanding (semantic search).

        Uses sentence-transformers (all-MiniLM-L6-v2) to find semantically similar code.
        No exact keyword matching — understands concepts like "user login" or "database query".
        Works with ANY MCP-compatible AI coder: Claude, Cursor, Windsurf, Cline, etc.

        Run index_repo FIRST to generate embeddings.

        @param repo_id: Repository UUID (from repo_init)
        @param query: Natural language query (e.g. "authentication logic", "API routes")
        @param top_k: Maximum number of results (default: 10, max: 50)
        @return: List of semantically matched code chunks with similarity scores
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            from src.domain.codeindex.infrastructure.embeddings import semantic_search as _semantic_search

            def _get_db_path():
                return orchestrator.db.db_path

            db_path = await asyncio.to_thread(_get_db_path)
            results = await asyncio.to_thread(_semantic_search, query, str(db_path), min(top_k, 50))

            return api_response(
                success=True,
                status_code=200,
                message=f"Semantic search completed: {len(results)} results",
                data={
                    "query": query,
                    "results": results,
                    "count": len(results)
                },
                request_id=request_id
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Semantic search failed: {str(e)}",
                data=None,
                error_code="IDX_005",
                request_id=request_id
            )
        finally:
            orchestrator.db.close()
