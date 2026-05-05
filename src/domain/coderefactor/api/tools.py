"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeRefactor
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Module tools – Single Responsibility: Register and handle MCP tools for coderefactor domain.
 */
"""

from __future__ import annotations
import json
from typing import Optional, List, Dict, Any
from dataclasses import asdict
from mcp.server.fastmcp import FastMCP

from src.domain.coderefactor.application.service import CodeRefactorService

def register_tools(mcp: FastMCP, service: CodeRefactorService) -> None:
    """
    Register all refactor-related tools to the FastMCP instance.

    @param mcp: FastMCP server instance
    @param service: RefactorService instance to delegate work to
    """

    @mcp.tool()
    async def search_code(repo_id: str, query: str, is_regex: bool = True, case_sensitive: bool = False) -> str:
        """
        Search across all files in a repository using DB-cached content.
        
        @param repo_id: Repository UUID
        @param query: Text or regex to search for
        @param is_regex: Whether the query is a regular expression
        @param case_sensitive: Whether the search should be case sensitive
        @return: List of matches with line numbers
        """
        try:
            result = service.search.search_code(repo_id, query, is_regex=is_regex, case_sensitive=case_sensitive)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error searching code: {str(e)}"

    @mcp.tool()
    async def replace_code(repo_id: str, find_query: str, replace_text: str, is_regex: bool = True, dry_run: bool = True) -> str:
        """
        Global find and replace across the repository.
        
        @param repo_id: Repository UUID
        @param find_query: Text or regex pattern to find
        @param replace_text: Text to replace with
        @param is_regex: Whether the find_query is a regular expression
        @param dry_run: If True, only returns what would happen
        @return: Status and affected files
        """
        try:
            result = service.search.replace_code(repo_id, find_query, replace_text, is_regex=is_regex, dry_run=dry_run)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error replacing code: {str(e)}"

    @mcp.tool()
    async def rename_symbol(path: str, old_name: str, new_name: str, dry_run: bool = True) -> str:
        """
        Rename a symbol (class, function, variable) semantically and update all references.
        
        @param path: Absolute path to the file where symbol is defined
        @param old_name: Current name of the symbol
        @param new_name: New name for the symbol
        @param dry_run: If True, only returns the planned changes
        @return: Refactor result summary
        """
        try:
            result = await service.rename_symbol(path, old_name, new_name, dry_run=dry_run)
            return json.dumps({
                "status": result.status,
                "message": result.message,
                "repository_id": result.repository_id,
                "changes": [asdict(c) for c in result.changes] if result.changes else [],
                "commit_hash": result.commit_hash,
                "error_code": result.error_code
            }, indent=2)
        except Exception as e:
            return f"Error executing rename: {str(e)}"

    @mcp.tool()
    async def move_code_element(path: str, element_name: str, target_file: str, dry_run: bool = True) -> str:
        """
        Move a class or function from source file to target file.
        Automatically updates imports in all calling files.
        
        @param path: Absolute path to the source file
        @param element_name: Name of the class or function to move
        @param target_file: Absolute path to the destination file
        @param dry_run: If True, only returns the planned changes
        @return: Refactor result summary
        """
        try:
            result = await service.move_code_element(path, element_name, target_file, dry_run=dry_run)
            return json.dumps({
                "status": result.status,
                "message": result.message,
                "repository_id": result.repository_id,
                "changes": [asdict(c) for c in result.changes] if result.changes else [],
                "commit_hash": result.commit_hash,
                "error_code": result.error_code
            }, indent=2)
        except Exception as e:
            return f"Error executing move element: {str(e)}"

    @mcp.tool()
    async def analyze_refactor_impact(path: str, symbol_name: str) -> str:
        """
        Predict breaking changes and affected files for a symbol modification.
        
        @param path: Absolute path to the file where symbol is defined
        @param symbol_name: Name of the symbol to analyze
        @return: Impact analysis summary
        """
        try:
            result = await service.analyze_refactor_impact(path, symbol_name)
            return json.dumps(asdict(result), indent=2)
        except Exception as e:
            return f"Error analyzing impact: {str(e)}"

    @mcp.tool()
    async def apply_refactor_recipe(path: str, recipe: str, dry_run: bool = True) -> str:
        """
        Apply a predefined refactor pattern (e.g. 'standardize_docstrings', 'add_type_hints').
        
        @param path: Absolute path to the file
        @param recipe: Recipe name to apply
        @param dry_run: If True, only returns the planned changes
        @return: Refactor result summary
        """
        try:
            result = await service.apply_refactor_recipe(path, recipe, dry_run=dry_run)
            return json.dumps({
                "status": result.status,
                "message": result.message,
                "repository_id": result.repository_id,
                "changes": [asdict(c) for c in result.changes] if result.changes else [],
                "commit_hash": result.commit_hash,
                "error_code": result.error_code
            }, indent=2)
        except Exception as e:
            return f"Error applying recipe: {str(e)}"
