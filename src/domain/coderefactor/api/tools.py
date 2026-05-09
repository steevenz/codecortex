"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeRefactor
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 */
"""

from __future__ import annotations
from typing import Optional, Dict, Any, Callable
from dataclasses import asdict
from mcp.server.fastmcp import FastMCP
from src.core import api_response, new_request_id


def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """Register consolidated coderefactor tools. Tool count: 6 → 5."""

    @mcp.tool()
    async def search_code(repo_id: str, query: str, is_regex: bool = True, case_sensitive: bool = False) -> Dict[str, Any]:
        """
        Search across all indexed files in a repository for text or regex patterns.

        Faster than filesystem grep because it queries the DB cache, not disk.
        Use is_regex=False for plain text searches, True for patterns.

        @param repo_id: Repository UUID
        @param query: Text or regex pattern to search for
        @param is_regex: If True (default), treat query as a regular expression
        @param case_sensitive: If False (default), search is case-insensitive
        @return: List of matches with file path, line number, and matched content.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = orchestrator.refactor_service.search.search_code(repo_id, query, is_regex=is_regex, case_sensitive=case_sensitive)
            return api_response(success=True, status_code=200, message="Search completed", data=result, request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error searching code: {str(e)}", data=None, request_id=request_id, error_code="REF_001")
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def search_replace(repo_id: str, find_query: str, replace_text: str, is_regex: bool = True, dry_run: bool = True) -> Dict[str, Any]:
        """
        Global find and replace across all files in the repository.

        CAUTION: This modifies multiple files at once. Always run dry_run=True first.
        Supports regex patterns for advanced replacements (e.g. capture groups).

        @param repo_id: Repository UUID
        @param find_query: Text or regex pattern to find
        @param replace_text: Replacement text (supports regex capture groups like \\1)
        @param is_regex: If True (default), treat find_query as a regex
        @param dry_run: If True (default), show what WOULD change. Set False to execute.
        @return: List of affected files, change counts, and before/after previews.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = orchestrator.refactor_service.search.replace_code(repo_id, find_query, replace_text, is_regex=is_regex, dry_run=dry_run)
            return api_response(success=True, status_code=200, message="Replace operation completed", data=result, request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error replacing code: {str(e)}", data=None, request_id=request_id, error_code="REF_002")
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def refactor_symbol(
        action: str,
        path: str,
        dry_run: bool = True,
        old_name: Optional[str] = None,
        new_name: Optional[str] = None,
        element_name: Optional[str] = None,
        target_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Semantic refactoring: rename a symbol OR move a code element to another file.

        Automatically updates all references across the codebase. Always dry_run first.

        @param action: "rename" | "move"
        @param path: Absolute path to the source file containing the symbol
        @param dry_run: If True (default), preview changes only. Set False to execute.

        For action="rename":
        @param old_name: Current name of the symbol (function, class, or variable)
        @param new_name: New name for the symbol

        For action="move":
        @param element_name: Name of the class or function to move
        @param target_file: Absolute path to the destination file

        @return: Refactor summary with all affected files, changed lines, and commit hash (if applied).
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            if action == "rename":
                if not old_name or not new_name:
                    return api_response(success=False, status_code=400, message="old_name and new_name required for action='rename'", data=None, request_id=request_id, error_code="REF_003")
                result = await orchestrator.refactor_service.rename_symbol(path, old_name, new_name, dry_run=dry_run)
            elif action == "move":
                if not element_name or not target_file:
                    return api_response(success=False, status_code=400, message="element_name and target_file required for action='move'", data=None, request_id=request_id, error_code="REF_003")
                result = await orchestrator.refactor_service.move_code_element(path, element_name, target_file, dry_run=dry_run)
            else:
                return api_response(success=False, status_code=400, message=f"Unknown action '{action}'. Use: 'rename' or 'move'", data=None, request_id=request_id, error_code="REF_003")

            data = {
                "status": result.status,
                "message": result.message,
                "repository_id": result.repository_id,
                "changes": [asdict(c) for c in result.changes] if result.changes else [],
                "commit_hash": result.commit_hash,
                "error_code": result.error_code,
            }
            return api_response(success=True, status_code=200, message=f"Refactor '{action}' completed", data=data, request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error in refactor_symbol ({action}): {str(e)}", data=None, request_id=request_id, error_code="REF_003")
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def refactor_impact(path: str, symbol_name: str) -> Dict[str, Any]:
        """
        Predict the blast radius of renaming or modifying a symbol: all affected files and breaking changes.

        Run this BEFORE refactor_symbol to understand the full impact of a rename or move.
        Essential for large codebases where a single rename could touch dozens of files.

        @param path: Absolute path to the file where the symbol is defined
        @param symbol_name: Name of the symbol to analyze (function, class, or variable)
        @return: Impact analysis: list of affected files, call sites, import sites, and risk level.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = await orchestrator.refactor_service.analyze_refactor_impact(path, symbol_name)
            return api_response(success=True, status_code=200, message="Impact analysis completed", data=asdict(result), request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error analyzing impact: {str(e)}", data=None, request_id=request_id, error_code="REF_004")
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def refactor_apply(path: str, recipe: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Apply a predefined refactoring recipe to a file (e.g. add type hints, standardize docstrings).

        Recipes are repeatable, idempotent transformations that bring a file to a coding standard.
        Always dry_run first to preview what will change.

        @param path: Absolute path to the target file
        @param recipe: Recipe name to apply. Examples: "standardize_docstrings", "add_type_hints", "remove_unused_imports"
        @param dry_run: If True (default), preview only. Set False to apply the recipe.
        @return: Refactor result with changed lines, before/after diff, and commit hash (if applied).
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = await orchestrator.refactor_service.apply_refactor_recipe(path, recipe, dry_run=dry_run)
            data = {
                "status": result.status,
                "message": result.message,
                "repository_id": result.repository_id,
                "changes": [asdict(c) for c in result.changes] if result.changes else [],
                "commit_hash": result.commit_hash,
                "error_code": result.error_code,
            }
            return api_response(success=True, status_code=200, message="Recipe applied", data=data, request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Error applying recipe: {str(e)}", data=None, request_id=request_id, error_code="REF_005")
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def refactor_rename(path: str, old_name: str, new_name: str, dry_run: bool = True) -> dict:
        """
        Multi-file coordinated rename using the Knowledge Graph.

        Finds ALL references to a symbol across the codebase and renames them.
        Skips strings and comments to avoid false positives.
        Uses TreeSitter for safe semantic renaming.

        @param path: Absolute path to the file containing the symbol
        @param old_name: Current symbol name (function, class, or variable)
        @param new_name: New symbol name to use
        @param dry_run: If True (default), preview only. Set False to execute.
        @return: Rename plan with changes and affected files
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = await orchestrator.refactor_service.rename_symbol(path, old_name, new_name, dry_run=dry_run)
            from dataclasses import asdict
            data = {
                "status": result.status,
                "message": result.message,
                "repository_id": result.repository_id,
                "changes": [asdict(c) for c in result.changes] if result.changes else [],
                "commit_hash": result.commit_hash,
                "error_code": result.error_code,
            }
            return api_response(success=True, status_code=200, message="Rename analysis completed", data=data, request_id=request_id)
        except Exception as e:
            return api_response(success=False, status_code=500, message=f"Rename failed: {str(e)}", data=None, request_id=request_id, error_code="REF_006")
        finally:
            orchestrator.db.close()
