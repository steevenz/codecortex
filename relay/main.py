"""
Relay Server — Main FastAPI application.

Provides tunnel proxy, cloud sync relay, and API key management
for CodeCortex cross-device communication.

Endpoints:
  POST /tunnel/register         — Register a new tunnel (24h TTL)
  GET  /tunnel/{id}/poll        — Poll for queued proxy requests
  POST /tunnel/{id}/respond     — Submit proxy response
  POST /tunnel/{id}/send        — Send proxy request to tunneled device
  DELETE /tunnel/{id}           — Deregister tunnel
  POST /codecortex-api/v1/cloud/push  — Push encrypted cloud data
  POST /codecortex-api/v1/cloud/pull  — Pull encrypted cloud data
  POST /admin/register-key      — Register API key (paid tier)
  GET  /health                  — Health check
  GET  /                        — Server info

:project: CodeCortex Relay
:package: Relay.Main
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CrossStack-v1.0
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import (
    CloudPullRequest, CloudPushRequest, ProxyRequest, ProxyResponse,
    TunnelRegistration, default_expiry, generate_id, utcnow,
)
from .storage import RelayStore

logger = logging.getLogger("codecortex.relay")

store = RelayStore()

VERSION = "2026.01"
START_TIME = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Relay Server v{VERSION} starting...")
    yield
    logger.info("Relay Server stopping...")


app = FastAPI(
    title="CodeCortex Relay",
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ──

def _ok(data: Any = None, message: str = "OK") -> Dict:
    return {"success": True, "status_code": 200, "message": message, "data": data}


def _err(message: str, code: str = "ERROR", status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"success": False, "status_code": status, "message": message, "data": None, "error_code": code},
    )


def _get_api_key(request: Request) -> str:
    return request.headers.get("X-API-KEY", "")


def _validate_api_key(key: str) -> bool:
    if not key:
        return True  # Open tier: no key required
    result = store.validate_api_key(key)
    return result is not None


# ── Tunnel Endpoints ──

@app.post("/tunnel/register")
async def tunnel_register(reg: TunnelRegistration, request: Request):
    api_key = reg.api_key or _get_api_key(request)
    if api_key and not _validate_api_key(api_key):
        return _err("Invalid or expired API key", "AUTH_001", 401)

    tunnel = store.register_tunnel(
        local_base=reg.local_base,
        api_key=api_key,
        device_id=reg.device_id,
        public_key=reg.public_key,
    )
    logger.info(f"Tunnel registered: {tunnel.tunnel_id} ({reg.local_base})")
    return _ok(data={
        "tunnel_id": tunnel.tunnel_id,
        "expires_at": tunnel.expires_at,
        "device_id": tunnel.device_id,
    }, message="Tunnel registered")


@app.get("/tunnel/{tunnel_id}/poll")
async def tunnel_poll(tunnel_id: str, limit: int = 10):
    tunnel = store.get_tunnel(tunnel_id)
    if not tunnel:
        return _err("Tunnel not found or expired", "TUNNEL_001", 404)

    requests = store.poll_requests(tunnel_id, limit=limit)
    return [r.model_dump() for r in requests]


@app.post("/tunnel/{tunnel_id}/respond")
async def tunnel_respond(tunnel_id: str, response: ProxyResponse):
    tunnel = store.get_tunnel(tunnel_id)
    if not tunnel:
        return _err("Tunnel not found or expired", "TUNNEL_001", 404)

    store.save_response(
        request_id=response.id,
        status=response.status,
        body=response.body,
    )
    return _ok(message="Response accepted")


@app.post("/tunnel/{tunnel_id}/send")
async def tunnel_send(tunnel_id: str, request_data: ProxyRequest, request: Request):
    tunnel = store.get_tunnel(tunnel_id)
    if not tunnel:
        return _err("Tunnel not found or expired", "TUNNEL_001", 404)

    req_id = store.enqueue_request(
        tunnel_id=tunnel_id,
        method=request_data.method,
        path=request_data.path,
        headers=request_data.headers,
        body=request_data.body,
    )
    logger.info(f"Request queued: {req_id} -> {tunnel_id} ({request_data.method} {request_data.path})")
    return _ok(data={"request_id": req_id}, message="Request queued")


@app.delete("/tunnel/{tunnel_id}")
async def tunnel_delete(tunnel_id: str):
    store.delete_tunnel(tunnel_id)
    return _ok(message="Tunnel deleted")


# ── Cloud Sync Endpoints ──

@app.post("/codecortex-api/v1/cloud/push")
async def cloud_push(push: CloudPushRequest, request: Request):
    api_key = _get_api_key(request)
    if api_key and not _validate_api_key(api_key):
        return _err("Invalid API key", "AUTH_001", 401)

    data = store.push_cloud_data(
        device_id=push.device_id,
        data_key=push.data_key,
        encrypted_payload=push.encrypted_payload,
        version=push.version,
    )
    return _ok(data={
        "device_id": data.device_id,
        "data_key": data.data_key,
        "version": data.version,
        "updated_at": data.updated_at,
    }, message="Data pushed")


@app.post("/codecortex-api/v1/cloud/pull")
async def cloud_pull(pull: CloudPullRequest, request: Request):
    api_key = _get_api_key(request)
    if api_key and not _validate_api_key(api_key):
        return _err("Invalid API key", "AUTH_001", 401)

    results = store.pull_cloud_data(
        device_id=pull.device_id,
        data_keys=pull.data_keys,
    )
    return _ok(data={
        "device_id": pull.device_id,
        "records": [r.model_dump() for r in results],
        "count": len(results),
    }, message="Data pulled")


# ── Admin Endpoints ──

@app.post("/admin/register-key")
async def register_api_key(key_data: Dict):
    key = key_data.get("key", generate_id("key_"))
    plan = key_data.get("plan", "free")
    rate_limit = key_data.get("rate_limit", 60)
    expires_at = key_data.get("expires_at", "")

    ok = store.register_api_key(key, plan, rate_limit, expires_at)
    if not ok:
        return _err("API key already exists", "AUTH_002", 409)
    logger.info(f"API key registered: {key[:12]}... ({plan})")
    return _ok(data={"key": key, "plan": plan}, message="API key registered")


# ── Health & Info ──

@app.get("/health")
async def health():
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    tunnels = store._conn().execute(
        "SELECT COUNT(*) as c FROM tunnels WHERE deleted_at IS NULL AND expires_at > ?",
        (utcnow(),),
    ).fetchone()["c"]
    return _ok(data={
        "status": "healthy",
        "version": VERSION,
        "uptime_seconds": int(uptime),
        "active_tunnels": tunnels,
        "server_time": utcnow(),
    })


@app.get("/")
async def root():
    return _ok(data={
        "server": "CodeCortex Relay",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "tunnel": "/tunnel/*",
            "cloud": "/codecortex-api/v1/cloud/*",
            "admin": "/admin/*",
        },
    })


# ── Cleanup task ──

@app.on_event("startup")
async def start_cleanup_task():
    asyncio.create_task(_cleanup_loop())


async def _cleanup_loop():
    while True:
        await asyncio.sleep(3600)  # Every hour
        try:
            deleted = store.cleanup_expired()
            if deleted:
                logger.info(f"Cleaned up {deleted} expired tunnels")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")


def start_server(host: str = "0.0.0.0", port: int = 8002, reload: bool = False):
    """Entry point for running the relay server."""
    logger.info(f"Starting relay server on {host}:{port}")
    uvicorn.run(
        "relay.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    start_server()
