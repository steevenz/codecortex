"""
/**
 * @project   CodeCortex
 * @package   Domain/Filesystem
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Module tools – Single Responsibility: Register and handle MCP tools for filesystem domain.
 */
"""

from __future__ import annotations
import json
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

from src.domain.filesystem.application.service import FilesystemService

def register_tools(mcp: FastMCP, service: FilesystemService) -> None:
    """
    Register all filesystem-related tools to the FastMCP instance.

    @param mcp: FastMCP server instance
    @param service: FilesystemService instance to delegate work to
    """

    @mcp.tool()
    async def get_codebase_tree(repo_id: str) -> str:
        """
        Get the directory and file tree for a repository from the index.
        
        @param repo_id: Repository UUID
        @return: JSON tree structure
        """
        try:
            tree = service.get_codebase_tree(repo_id)
            return json.dumps(tree, indent=2)
        except Exception as e:
            return f"Error retrieving tree: {str(e)}"

    @mcp.tool()
    async def read_code_file(path: str, repo_id: str) -> str:
        """
        Read the content of a specific code file from the repository.
        
        @param path: Relative path to the file
        @param repo_id: Repository UUID
        @return: File content and metadata
        """
        try:
            result = service.read_file(path, repo_id)
            if "error" in result:
                return f"Error: {result['error']}"
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @mcp.tool()
    async def write_code_file(path: str, content: str, repo_id: str, dry_run: bool = True) -> str:
        """
        Write or update a code file. Supports dry-run for safety.
        
        @param path: Relative path to the file
        @param content: New content for the file
        @param repo_id: Repository UUID
        @param dry_run: If True, only returns what would happen
        @return: Status and change summary
        """
        try:
            result = service.write_file(path, content, repo_id, dry_run=dry_run)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error writing file: {str(e)}"

    @mcp.tool()
    async def delete_code_file(path: str, repo_id: str, dry_run: bool = True) -> str:
        """
        Delete a code file from the codebase and index.
        
        @param path: Relative path to the file
        @param repo_id: Repository UUID
        @param dry_run: If True, only returns what would happen
        @return: Status
        """
        try:
            result = service.delete_file(path, repo_id, dry_run=dry_run)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error deleting file: {str(e)}"

    @mcp.tool()
    async def move_code_file(source_path: str, dest_path: str, repo_id: str, dry_run: bool = True) -> str:
        """
        Move or rename a code file or directory.
        
        @param source_path: Current relative path
        @param dest_path: Target relative path
        @param repo_id: Repository UUID
        @param dry_run: If True, only returns what would happen
        @return: Status
        """
        try:
            result = service.move_file(source_path, dest_path, repo_id, dry_run=dry_run)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error moving file: {str(e)}"

    @mcp.tool()
    async def list_files_glob(pattern: str, repo_id: str) -> str:
        """
        List files matching a glob pattern.
        
        @param pattern: Glob pattern (e.g. '**/*.py')
        @param repo_id: Repository UUID
        @return: List of matching paths
        """
        try:
            result = service.list_files_glob(pattern, repo_id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing files: {str(e)}"
