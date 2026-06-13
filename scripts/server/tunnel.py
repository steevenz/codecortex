"""
Tunnel Client — exposes local HTTP server to a remote relay.

Used by: codecortex server start --expose <relay-url>

The tunnel connects to a relay WebSocket server, registers a tunnel,
and proxies incoming HTTP requests from the relay to the local FastAPI.

:project: CodeCortex
:package: Scripts.Server.Tunnel
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CrossStack-v1.0
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("CodeCortex.Tunnel")


class TunnelClient:
    """WebSocket tunnel client that proxies relay requests to local HTTP server.

    Protocol:
      1. Connect to relay at ws://<relay-url>/tunnel/register
      2. Receive tunnel_id
      3. Listen for proxy_request messages
      4. Execute request locally, send back proxy_response
    """

    def __init__(self, relay_url: str, local_base: str = "http://127.0.0.1:8001",
                 api_key: str = ""):
        self.relay_url = relay_url.rstrip("/")
        self.local_base = local_base.rstrip("/")
        self.api_key = api_key
        self.tunnel_id: Optional[str] = None
        self._running = False

    async def run(self) -> None:
        """Start the tunnel client using SSE-based polling (no WebSocket dep)."""
        self._running = True
        register_url = f"{self.relay_url}/tunnel/register"

        # 1. Register tunnel via POST
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.post(register_url, json={
                    "local_base": self.local_base,
                    "api_key": self.api_key,
                })
                data = resp.json()
                self.tunnel_id = data.get("tunnel_id", "")
                logger.info(f"Tunnel registered: {self.tunnel_id}")
                print(json.dumps({
                    "event": "tunnel_registered",
                    "tunnel_id": self.tunnel_id,
                    "relay": self.relay_url,
                }))
            except Exception as e:
                logger.error(f"Tunnel registration failed: {e}")
                raise

        # 2. Poll for proxy requests via SSE
        poll_url = f"{self.relay_url}/tunnel/{self.tunnel_id}/poll"
        while self._running:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(poll_url)
                    if resp.status_code == 200:
                        batch = resp.json()
                        requests = batch if isinstance(batch, list) else [batch]
                        for req_data in requests:
                            if not req_data:
                                continue
                            asyncio.create_task(self._handle_request(req_data))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Tunnel poll error (expected if idle): {e}")
                await asyncio.sleep(2)

    async def _handle_request(self, req_data: Dict[str, Any]) -> None:
        """Handle a single proxy request from relay."""
        req_id = req_data.get("id", str(uuid.uuid4()))
        method = req_data.get("method", "GET").upper()
        path = req_data.get("path", "/")
        headers = req_data.get("headers", {})
        body = req_data.get("body")

        url = f"{self.local_base}{path}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(
                    method, url, headers=headers,
                    content=json.dumps(body) if body and method in ("POST", "PUT", "PATCH") else None,
                )
                response_body = resp.text
                try:
                    response_body = resp.json()
                except Exception:
                    pass
                await self._send_response(req_id, resp.status_code, response_body)
        except Exception as e:
            await self._send_response(req_id, 502, {"error": str(e)})

    async def _send_response(self, req_id: str, status: int, body: Any) -> None:
        """Send proxy response back to relay."""
        respond_url = f"{self.relay_url}/tunnel/{self.tunnel_id}/respond"
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(respond_url, json={
                    "id": req_id, "status": status, "body": body,
                })
            except Exception:
                pass

    def stop(self) -> None:
        self._running = False
