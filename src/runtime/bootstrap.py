"""Lightweight runtime bootstrap for CLI and other non-server adapters.

This module intentionally avoids importing src.main so adapters do not trigger
server construction, lockfile safeguards, or full MCP registration as import side effects.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from src.main import CortexOrchestrator, create_orchestrator
from src.api.tools import register_tools as register_api_tools
from src.modules.knowledgegraph.api.tools import register_tools as register_knowledge_tools
from src.modules.idegraph.api.tools import register_tools as register_idegraph_tools

logger = logging.getLogger(__name__)

def bootstrap_runtime(*, include_mcp: bool = False, cli_mode: bool = False) -> Dict[str, Any]:
    """Initialize codebase deps without server/app side effects."""
    logger.info("Bootstrapping CodeCortex runtime infrastructure")

    # Load orchestrator without triggering any single-instance / lockfile checks
    orchestrator = create_orchestrator()

    components: Dict[str, Any] = {
        "orchestrator": orchestrator,
    }

    if include_mcp:
        mcp_instance = FastMCP("codecortex")
        # Register all the required tools to this lightweight FastMCP instance
        register_api_tools(mcp_instance, lambda: orchestrator)
        register_knowledge_tools(mcp_instance, lambda: orchestrator)
        register_idegraph_tools(mcp_instance, lambda: orchestrator)
        components["mcp_instance"] = mcp_instance

    return components
