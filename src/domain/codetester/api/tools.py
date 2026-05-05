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

def register_tools(mcp: FastMCP, qa_service: QAService) -> None:
    """
    Register all QA related tools to the FastMCP instance.

    @param mcp: FastMCP server instance
    @param qa_service: QAService instance
    """

    @mcp.tool()
    async def run_qa_task(repo_id: str, tool: str, target_path: Optional[str] = None, 
                         extra_args: Optional[str] = None, webhook_url: Optional[str] = None,
                         background: bool = True) -> str:
        """
        Run a QA task (test or lint) on a codebase.
        Supported tools: 'pytest', 'flake8'.
        
        @param repo_id: Repository UUID
        @param tool: Tool name (pytest, flake8, etc.)
        @param target_path: Optional specific file or directory
        @param extra_args: Optional command line arguments
        @param webhook_url: Optional URL to notify on completion
        @param background: If True, runs as a background task
        @return: Task ID and initial status
        """
        try:
            result = qa_service.run_qa_task(repo_id, tool, target_path, extra_args, webhook_url, background)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error running QA task: {str(e)}"

    @mcp.tool()
    async def get_qa_task_status(task_id: str) -> str:
        """
        Get the status and result of a background QA task.
        
        @param task_id: Task UUID
        @return: Status, logs, and result summary
        """
        try:
            result = qa_service.get_task_status(task_id)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error retrieving task status: {str(e)}"
