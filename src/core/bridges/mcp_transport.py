"""
MCP Transport Strategies.
Handles dynamic switching between SSE and Stdio MCP Client protocols.

:project: Cognitive Server
:package: Core.Bridges
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
"""

import os
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters

class McpTransportStrategy:
    """Base strategy for MCP Client Transport."""
    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[ClientSession, None]:
        raise NotImplementedError

class SSETransportStrategy(McpTransportStrategy):
    """Connects to a remote or local MCP server via HTTP/SSE."""
    def __init__(self, url: str, api_key: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {}
        if api_key:
            self.headers["X-API-KEY"] = api_key

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[ClientSession, None]:
        async with sse_client(self.url, headers=self.headers) as streams:
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session

class StdioTransportStrategy(McpTransportStrategy):
    """Connects to a local MCP server via CLI (subprocess)."""
    def __init__(self, command: str, args: list[str], env: Optional[Dict[str, str]] = None):
        self.params = StdioServerParameters(
            command=command,
            args=args,
            env=env or os.environ.copy()
        )

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[ClientSession, None]:
        async with stdio_client(self.params) as streams:
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session

class McpClientFactory:
    """Creates the appropriate transport strategy based on config."""
    @staticmethod
    def create(mode: str, **kwargs) -> McpTransportStrategy:
        mode = mode.lower()
        if mode == "sse":
            return SSETransportStrategy(
                url=kwargs.get("url"),
                api_key=kwargs.get("api_key"),
                headers=kwargs.get("headers")
            )
        elif mode == "stdio":
            return StdioTransportStrategy(
                command=kwargs.get("command"),
                args=kwargs.get("args", []),
                env=kwargs.get("env")
            )
        else:
            raise ValueError(f"Unsupported MCP transport mode: {mode}")
