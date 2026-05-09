"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeTester
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Module tools – Single Responsibility: Register and handle MCP tools for codetester domain.
 */
"""

from __future__ import annotations
import json
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

from src.domain.codetester.application.qa_service import QAService

from src.core import api_response, new_request_id

def register_tools(mcp: FastMCP, orchestrator_factory) -> None:
    """
    Register all QA related tools to the FastMCP instance.

    @param mcp: FastMCP server instance
    @param orchestrator_factory: Factory function to create CortexOrchestrator instances
    """

    @mcp.tool()
    async def qa_run(repo_id: str, tool: str, target_path: Optional[str] = None,
                     extra_args: Optional[str] = None, webhook_url: Optional[str] = None,
                     background: bool = True) -> dict:
        """
        Run a QA task (tests or linting) on the codebase. Supported tools: 'pytest', 'flake8'.

        Runs asynchronously in the background by default. Use qa_status to poll for results.
        Scope to a specific path for faster targeted runs.

        @param repo_id: Repository UUID
        @param tool: QA tool to run — 'pytest' (tests) | 'flake8' (linting)
        @param target_path: Optional file or directory to scope the run (e.g. 'tests/unit/')
        @param extra_args: Optional extra CLI arguments (e.g. '-v --tb=short' for pytest)
        @param webhook_url: Optional URL to POST results to on completion
        @param background: If True (default), runs async. Set False for synchronous blocking execution.
        @return: Task ID (for background) or full results (for synchronous). Use qa_status to poll.
        """
        request_id = new_request_id()
        
        # Input validation
        if not repo_id or not isinstance(repo_id, str):
            return api_response(
                success=False,
                status_code=400,
                message="Repository ID must be a non-empty string",
                data=None,
                error_code="QA_VAL_001",
                request_id=request_id
            )
        
        # Validate tool parameter
        allowed_tools = ["pytest", "flake8", "unittest", "jest", "phpunit", "npm", "pnpm", "vitest", "yarn", "go_test", "cargo_test", "swift_test", "kotlin_test", "sbt_test", "maven_test", "ruby_test", "flutter_test", "dart_test", "haskell_test", "elixir_test", "dotnet_test", "perl_test", "stylelint", "ctest"]
        if not tool or not isinstance(tool, str) or tool not in allowed_tools:
            return api_response(
                success=False,
                status_code=400,
                message=f"Tool must be one of {allowed_tools}",
                data=None,
                error_code="QA_VAL_002",
                request_id=request_id
            )
        
        # Validate target_path for path traversal
        if target_path and isinstance(target_path, str):
            # Normalize and check for path traversal
            normalized_path = target_path.replace("\\", "/")
            if ".." in normalized_path or normalized_path.startswith("/"):
                return api_response(
                    success=False,
                    status_code=400,
                    message="Target path cannot contain path traversal sequences",
                    data=None,
                    error_code="QA_VAL_003",
                    request_id=request_id
                )
        
        # Validate webhook_url format if provided
        if webhook_url and isinstance(webhook_url, str):
            if not webhook_url.startswith(("http://", "https://")):
                return api_response(
                    success=False,
                    status_code=400,
                    message="Webhook URL must start with http:// or https://",
                    data=None,
                    error_code="QA_VAL_004",
                    request_id=request_id
                )
        
        orchestrator = orchestrator_factory()
        try:
            result = orchestrator.qa_service.run_qa_task(repo_id, tool, target_path, extra_args, webhook_url, background)
            # Check if the service returned an error
            if isinstance(result, dict) and "error" in result:
                return api_response(
                    success=False,
                    status_code=400,
                    message=result["error"],
                    data=None,
                    error_code="QA_SRV_001",
                    request_id=request_id
                )
            return api_response(
                success=True,
                status_code=202 if background else 200,
                message=f"QA task {tool} started" if background else f"QA task {tool} completed",
                data=result,
                request_id=request_id
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Error running QA task: {str(e)}",
                data=None,
                error_code="QA_001",
                request_id=request_id
            )
        finally:
            orchestrator.db.close()

    @mcp.tool()
    async def qa_status(task_id: str) -> dict:
        """
        Poll the status and result of a background QA task started by qa_run.

        Call this after qa_run (background=True) to check if the task is done and get results.
        Status values: 'pending', 'running', 'completed', 'failed'.

        @param task_id: Task UUID returned by qa_run
        @return: Task status and full output (stdout, exit code, error messages) when completed.
        """
        request_id = new_request_id()
        
        # Input validation
        if not task_id or not isinstance(task_id, str):
            return api_response(
                success=False,
                status_code=400,
                message="Task ID must be a non-empty string",
                data=None,
                error_code="QA_VAL_005",
                request_id=request_id
            )
        
        # Optional: Validate UUID format
        try:
            import uuid
            uuid.UUID(task_id)
        except ValueError:
            return api_response(
                success=False,
                status_code=400,
                message="Task ID must be a valid UUID",
                data=None,
                error_code="QA_VAL_006",
                request_id=request_id
            )
        
        orchestrator = orchestrator_factory()
        try:
            result = orchestrator.qa_service.get_task_status(task_id)
            # Check if the service returned an error
            if isinstance(result, dict) and "error" in result:
                return api_response(
                    success=False,
                    status_code=404 if result["error"] == "task_not_found" else 400,
                    message=result["error"],
                    data=None,
                    error_code="QA_SRV_002",
                    request_id=request_id
                )
            return api_response(
                success=True,
                status_code=200,
                message="QA task status retrieved",
                data=result,
                request_id=request_id
            )
        except Exception as e:
            return api_response(
                success=False,
                status_code=500,
                message=f"Error retrieving task status: {str(e)}",
                data=None,
                error_code="QA_002",
                request_id=request_id
            )
        finally:
            orchestrator.db.close()
