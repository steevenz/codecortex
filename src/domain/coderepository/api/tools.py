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
from typing import Optional, List
from mcp.server.fastmcp import FastMCP
from src.domain.coderepository.application.service import CodeRepositoryService
from src.domain.coderepository.application.git_service import GitService

def register_tools(mcp: FastMCP, service: CodeRepositoryService, git_service: GitService) -> None:
    """
    Register all repository-related tools to the FastMCP instance.
    
    @param mcp: FastMCP server instance
    @param service: CodeRepositoryService instance
    @param git_service: GitService instance
    """

    @mcp.tool()
    async def initialize_repository(path: str) -> str:
        """Initialize the repository path for future code analysis operations."""
        try:
            return await service.initialize(path)
        except Exception as e:
            return f"Error initializing repository: {str(e)}"

    @mcp.tool()
    async def get_repo_info() -> str:
        """Get information about the currently initialized code repository."""
        return service.get_info()

    @mcp.tool()
    async def get_repo_structure(sub_path: Optional[str] = None, depth: Optional[int] = None) -> str:
        """Get the structure of files and directories in the repository."""
        return service.get_structure(sub_path, depth)

    @mcp.tool()
    async def read_file(file_path: str) -> str:
        """Read and display the contents of a file from the repository."""
        return service.read_file(file_path)

    @mcp.tool()
    async def git_status(path: str) -> str:
        """Get the git status of a repository."""
        try:
            # Service needs root path. RepositoryService can resolve it.
            # But main.py was doing it via orchestrator.
            # We can just use git_service directly if path is correct.
            res = git_service.get_repo_status(path)
            return json.dumps(res, indent=2)
        except Exception as e:
            return f"Error getting git status: {str(e)}"

    @mcp.tool()
    async def git_commit(path: str, message: str, files: Optional[List[str]] = None) -> str:
        """Stage and commit changes to the repository."""
        try:
            res = git_service.stage_and_commit(path, files or ["."], message)
            return json.dumps(res, indent=2)
        except Exception as e:
            return f"Error committing changes: {str(e)}"
