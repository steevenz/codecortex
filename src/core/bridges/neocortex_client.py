"""
Neocortex Bridge Client.
Main facade for communicating with Neocortex from CodeCortex.

:project: CodeCortex
:package: Core.Bridges
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
"""

import os
import logging
from typing import Optional, Dict, Any

from src.core.bridges.mcp_transport import McpClientFactory, McpTransportStrategy
from src.core.bridges.dynamic_proxy import DynamicToolProxy

logger = logging.getLogger(__name__)

class NeocortexClient:
    """
    Client adapter to execute tasks on Neocortex Cognitive Engine.
    Uses dynamic proxy and universal transport.
    """
    
    _instance: Optional["NeocortexClient"] = None

    def __init__(self):
        self.transport_mode = os.environ.get("CODECORTEX_BRIDGE_NEOCORTEX_TRANSPORT", "sse").lower()
        _base_url = os.environ.get("CODECORTEX_BRIDGE_NEOCORTEX_URL", "http://127.0.0.1:8010").rstrip("/")
        self.neocortex_url = f"{_base_url}/cognitive-api/v1/sync"
        self.api_key = os.environ.get("CODECORTEX_BRIDGE_NEOCORTEX_API_KEY", "")

        self.transport: McpTransportStrategy = McpClientFactory.create(
            mode=self.transport_mode,
            url=self.neocortex_url,
            api_key=self.api_key,
            headers={"X-IDE-ORIGIN": "codecortex_bridge"}
        )

    @classmethod
    def instance(cls) -> "NeocortexClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a single tool call and close connection."""
        try:
            async with self.transport.connect() as session:
                proxy = DynamicToolProxy(session)
                return await proxy.execute_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"[NeocortexClient] Execution failed for {tool_name}: {e}")
            return None

    async def request_executive_summary(self, problem_statement: str, context: str) -> Optional[Dict[str, Any]]:
        """Request Neocortex to think and summarize an architecture audit."""
        return await self.execute("neocortex:think", {
            "action": "analyze",
            "content": problem_statement,
            "context": context
        })
