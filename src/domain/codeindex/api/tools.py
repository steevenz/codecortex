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
from typing import Optional
from mcp.server.fastmcp import FastMCP
from src.domain.codeindex.application.service import CodeIndexService
from src.core.database import DatabaseManager

def register_tools(mcp: FastMCP, service: CodeIndexService, codegraph_service=None) -> None:
    """
    Register all codeindex-related tools to the FastMCP instance.

    :param mcp: FastMCP server instance
    :param service: CodeIndexService instance to delegate work to
    :param codegraph_service: Optional CodeGraphService for unified graph sync
    """
    if codegraph_service and not service.codegraph_service:
        service.codegraph_service = codegraph_service

    @mcp.tool()
    async def index_repository(repo_id: str) -> str:
        """
        Index all code files in the repository using Tree-Sitter.
        
        :param repo_id: Repository UUID
        :return: Status message with indexing statistics
        """
        try:
            service.index_repository(repo_id)
            return f"Successfully indexed repository: {repo_id}"
        except Exception as e:
            return f"Error indexing repository: {str(e)}"

    @mcp.tool()
    async def index_file(repo_id: str, file_id: str) -> str:
        """
        Index a specific file for symbol extraction.
        
        :param repo_id: Repository UUID
        :param file_id: File UUID
        :return: Status message with symbol count
        """
        try:
            # Get file path from database
            cursor = service.db.conn.execute("""
                SELECT d.relative_path, f.name 
                FROM files f
                JOIN directories d ON f.directory_id = d.id
                WHERE f.id = ?
            """, (file_id,))
            file_info = cursor.fetchone()
            if not file_info:
                return f"File not found: {file_id}"
            
            # Read file content
            from pathlib import Path
            repo_root = service.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,)).fetchone()['root_path']
            dir_path = file_info['relative_path'] if file_info['relative_path'] else ''
            file_rel_path = f"{dir_path}/{file_info['name']}" if dir_path else file_info['name']
            file_path = Path(repo_root) / file_rel_path
            
            if not file_path.exists():
                return f"File not found on disk: {file_rel_path}"
            
            # TreeSitterParser primary path
            parsed = service.index_file_with_tree_sitter(repo_id, file_id, file_path)
            if "error" not in parsed:
                symbol_count = len(parsed.get("functions", [])) + len(parsed.get("classes", []))
                return f"Successfully indexed file: {file_rel_path} ({symbol_count} symbols)"

            # Fallback to legacy BaseStrategy path
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            symbol_count = service.index_file(repo_id, file_id, file_rel_path, content)
            return f"Successfully indexed file: {file_rel_path} ({symbol_count} symbols)"
        except Exception as e:
            return f"Error indexing file: {str(e)}"
