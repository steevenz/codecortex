import os
import time
import json
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends, status as http_status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sse_starlette.sse import EventSourceResponse
import uvicorn

from src.core import api_response, new_request_id, load_version
from src.core.logging_config import get_logger
from src.main import CortexOrchestrator, mcp # Import mcp for tool lookup

logger = get_logger(__name__)

START_TIME = time.time()
PRD_ID = "20260505-codecortex-mcp-hardened"
SENSITIVE_KEYWORDS = ("token", "secret", "password", "api_key", "apikey", "authorization")

def _require_api_key() -> str:
    api_key = (os.getenv("CODECORTEX_DASHBOARD_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("CODECORTEX_DASHBOARD_API_KEY is required")
    return api_key

def _redact_sensitive(value: Any) -> Any:
    """Redacts sensitive fields from nested dictionaries/lists before API response."""
    if isinstance(value, dict):
        redacted: Dict[str, Any] = {}
        for key, item in value.items():
            lowered = key.lower()
            if any(marker in lowered for marker in SENSITIVE_KEYWORDS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value

def create_app() -> FastAPI:
    app = FastAPI(
        title="CodeCortex MCP HTTP API",
        version=load_version(),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    raw_origins = os.getenv("CODECORTEX_CORS_ORIGINS", "http://localhost,http://127.0.0.1").strip()
    allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-KEY"],
    )

    api_key = _require_api_key()
    api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

    def _validate_key(key: Optional[str]) -> None:
        if not key or key.strip() != api_key:
            raise HTTPException(status_code=403, detail="Forbidden")

    @app.get("/status")
    async def status() -> Dict[str, Any]:
        return {
            "server": {
                "name": "codecortex", 
                "version": load_version(),
                "identity": os.getenv("CODECORTEX_IDENTITY", "anonymous-node")
            },
            "transport": "http-jsonrpc/sse",
            "uptime_seconds": int(time.time() - START_TIME),
            "status": "healthy",
            "features": ["code_analysis", "semantic_indexing", "architectural_mapping", "sse_streaming"]
        }

    mcp_path = "/sync"
    mcp_secret = os.getenv("CODECORTEX_MCP_SECRET", "").strip()
    if mcp_secret:
        mcp_path = f"/sync/{mcp_secret}"
        logger.info(f"Custom MCP Secret Path activated: {mcp_path}")

    # --- MCP SSE Handler ---
    async def mcp_sse_handler(request: Request):
        async def event_generator():
            try:
                while True:
                    if await request.is_disconnected():
                        logger.info("MCP SSE connection closed by client")
                        return
                    await asyncio.sleep(15)
                    yield {"comment": "keepalive"}
            except asyncio.CancelledError:
                logger.info("MCP SSE connection closed by client")
            except Exception as e:
                logger.error(f"Error in MCP SSE handler: {e}")
        return EventSourceResponse(event_generator(), ping=15)

    @app.get(f"/codecortex-api/v1{mcp_path}")
    async def mcp_sse_endpoint(request: Request, x_api_key: Optional[str] = None):
        _validate_key(x_api_key or api_key_header(request))
        return await mcp_sse_handler(request)

    @app.post(f"/codecortex-api/v1{mcp_path}")
    async def sync(request: Request, x_api_key: Optional[str] = None) -> Dict[str, Any]:
        _validate_key(x_api_key or api_key_header(request))
        request_id = new_request_id()
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        if not isinstance(payload, dict):
            return api_response(
                success=False,
                status_code=400,
                message="Invalid JSON-RPC payload",
                data=None,
                request_id=request_id,
                error_code="RPC_001",
            )

        method = payload.get("method")
        params = payload.get("params") or {}
        rpc_id = payload.get("id")

        def rpc_ok(result: Any) -> Dict[str, Any]:
            return {"jsonrpc": "2.0", "id": rpc_id, "result": result}

        def build_initialize_payload(requested_protocol_value: Any) -> Dict[str, Any]:
            protocol_version = (
                requested_protocol_value
                if isinstance(requested_protocol_value, str) and requested_protocol_value.strip()
                else "2024-11-05"
            )
            return {
                "protocolVersion": protocol_version,
                "serverInfo": {"name": "codecortex", "version": load_version()},
                "capabilities": {"tools": {"listChanged": False}},
            }

        # MCP Lifecycle overrides
        if not method and isinstance(payload.get("protocolVersion"), str):
            return build_initialize_payload(payload.get("protocolVersion"))

        if method == "initialize":
            return rpc_ok(build_initialize_payload(params.get("protocolVersion")))

        if method == "ping":
            return rpc_ok({})

        if not isinstance(method, str) or not method.strip():
            return api_response(
                success=False,
                status_code=400,
                message="Missing method",
                data=None,
                request_id=request_id,
                error_code="RPC_002",
            )

        orchestrator = CortexOrchestrator()
        try:
            # Fallback to FastMCP tool registry
            mcp_tools = {t.name: t for t in mcp._tools}
            if method in mcp_tools:
                tool = mcp_tools[method]
                # FastMCP tools are usually sync or wrapped async run()
                if asyncio.iscoroutinefunction(tool.run):
                    result = await tool.run(**params)
                else:
                    result = tool.run(**params)
            else:
                return api_response(
                    success=False,
                    status_code=404,
                    message=f"Unknown method: {method}",
                    data=None,
                    request_id=request_id,
                    error_code="RPC_404",
                )

            # Standardized successful response with redaction
            redacted_data = _redact_sensitive(result)
            
            # If the request looks like a standard JSON-RPC, wrap it
            if rpc_id is not None:
                return rpc_ok(redacted_data)

            return api_response(
                success=True,
                status_code=200,
                message="OK",
                data=redacted_data,
                request_id=request_id,
            )
        except Exception as e:
            logger.exception("sync handler failed for method=%s", method)
            return api_response(
                success=False,
                status_code=500,
                message=f"Request failed: {str(e)}",
                data=None,
                request_id=request_id,
                error_code="RPC_500",
            )
        finally:
            try:
                orchestrator.db.close()
            except Exception:
                pass

    return app


def main() -> None:
    host = (os.getenv("CODECORTEX_HOST") or "127.0.0.1").strip()
    port_raw = (os.getenv("CODECORTEX_PORT") or "8001").strip()
    port = int(port_raw) if port_raw.isdigit() else 8001
    uvicorn.run("src.http_server:create_app", host=host, port=port, factory=True, log_level="info")


if __name__ == "__main__":
    main()

