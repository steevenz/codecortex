"""
CodeCortex Bridge Client.
Main facade for communicating with CodeCortex from Neocortex.

:project: CodeCortex
:package: Core.Bridges
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
"""

import os
import logging
from typing import Optional, Dict, Any

from src.core.bridges.mcp_transport import McpClientFactory, McpTransportStrategy

logger = logging.getLogger(__name__)


class CodeCortexClient:
    """
    Client adapter to execute tasks on CodeCortex from Neocortex.
    Uses dynamic proxy and universal transport.
    """
    
    _instance: Optional["CodeCortexClient"] = None

    def __init__(self):
        self.transport_mode = os.environ.get("NEOCORTEX_BRIDGE_CODECORTEX_TRANSPORT", "sse").lower()
        _base_url = os.environ.get("NEOCORTEX_BRIDGE_CODECORTEX_URL", "http://127.0.0.1:8001").rstrip("/")
        self.codecortex_url = f"{_base_url}/codecortex-api/v1/sync"
        self.api_key = os.environ.get("NEOCORTEX_BRIDGE_CODECORTEX_API_KEY", "")

        self.transport: McpTransportStrategy = McpClientFactory.create(
            mode=self.transport_mode,
            url=self.codecortex_url,
            api_key=self.api_key,
            headers={"X-IDE-ORIGIN": "neocortex_bridge"}
        )

    @classmethod
    def instance(cls) -> "CodeCortexClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a single tool call and close connection."""
        try:
            async with self.transport.connect() as session:
                from src.core.bridges.dynamic_proxy import DynamicToolProxy
                proxy = DynamicToolProxy(session)
                return await proxy.execute_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"[CodeCortexClient] Execution failed for {tool_name}: {e}")
            return None

    async def get_code_context(self, query: str, repo_path: str) -> Optional[Dict[str, Any]]:
        """Search codebase context for Neocortex analysis."""
        return await self.execute("codecortex_codebase", {
            "action": "search",
            "repo_path": repo_path,
            "args": {"query": query, "limit": 20}
        })

    async def get_architecture(self, repo_path: str) -> Optional[Dict[str, Any]]:
        """Get architecture audit from CodeCortex."""
        return await self.execute("codecortex_codebase", {
            "action": "audit",
            "repo_path": repo_path
        })

    async def query_docs(self, query: str, repo_path: str) -> Optional[Dict[str, Any]]:
        """Query documentation and knowledge graph."""
        return await self.execute("knowledge_query", {
            "query": query,
            "repo_path": repo_path
        })