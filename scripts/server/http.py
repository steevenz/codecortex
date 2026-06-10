import os
import time
import json
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends, status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse
import uvicorn
import threading
import secrets
import uuid

# pyrefly: ignore [missing-import]
from src.core import api_response, new_request_id, load_version
# pyrefly: ignore [missing-import]
from src.core.logging import get_logger
from src.main import CortexOrchestrator, mcp # Import mcp for tool lookup
from src.core.security.auth import AuthService

logger = get_logger(__name__)

START_TIME = time.time()
PRD_ID = "20260505-codecortex-mcp-hardened"
SENSITIVE_KEYWORDS = ("token", "secret", "password", "api_key", "apikey", "authorization")

_llm_registry: Dict[str, Dict[str, Any]] = {}
_llm_registry_lock = threading.Lock()

def _redact_sensitive(value: Any) -> Any:
    """Redacts sensitive fields from nested dictionaries/lists before API response."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
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
    if isinstance(value, tuple):
        return [_redact_sensitive(item) for item in value]
    try:
        from dataclasses import is_dataclass, asdict
        if is_dataclass(value):
            return _redact_sensitive(asdict(value))
    except Exception:
        pass
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        try:
            return _redact_sensitive(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "type") and hasattr(value, "text"):
        try:
            return {"type": str(getattr(value, "type")), "text": str(getattr(value, "text"))}
        except Exception:
            return str(value)
    if hasattr(value, "__dict__") and not isinstance(value, type):
        try:
            return _redact_sensitive({k: v for k, v in value.__dict__.items() if not k.startswith("_")})
        except Exception:
            pass
    return str(value)

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

    api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

    def _client_ip(request: Request) -> str:
        forwarded = (request.headers.get("X-Forwarded-For", "") or "").strip()
        if forwarded:
            return forwarded.split(",")[0].strip()
        return (request.client.host if request.client else "unknown") or "unknown"

    def _request_id(request: Request) -> str:
        return (request.headers.get("X-Request-ID", "") or "").strip() or f"req_{uuid.uuid4().hex[:8]}"

    def _detail_to_message(detail: Any) -> str:
        if isinstance(detail, str):
            return detail
        try:
            return json.dumps(detail, ensure_ascii=False)
        except Exception:
            return str(detail)

    def _is_mcp_jsonrpc_request(request: Request) -> bool:
        path = request.url.path or ""
        return path.startswith("/codecortex-api/v1/sync")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = _request_id(request)
        message = _detail_to_message(getattr(exc, "detail", "HTTP error"))

        if _is_mcp_jsonrpc_request(request):
            rpc_id = None
            try:
                payload = await request.json()
                if isinstance(payload, dict):
                    rpc_id = payload.get("id")
            except Exception:
                pass

            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "error": {
                        "code": -32000,
                        "message": message,
                        "data": {"request_id": request_id, "status_code": exc.status_code},
                    },
                },
            )

        return JSONResponse(
            status_code=exc.status_code,
            content=api_response(
                success=False,
                status_code=exc.status_code,
                message=message,
                data=None,
                request_id=request_id,
                error_code=f"HTTP_{exc.status_code}",
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = _request_id(request)
        message = "Validation error"
        details = {"errors": exc.errors()} if hasattr(exc, "errors") else None

        if _is_mcp_jsonrpc_request(request):
            rpc_id = None
            try:
                payload = await request.json()
                if isinstance(payload, dict):
                    rpc_id = payload.get("id")
            except Exception:
                pass

            return JSONResponse(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "error": {
                        "code": -32602,
                        "message": message,
                        "data": {"request_id": request_id, "details": details},
                    },
                },
            )

        return JSONResponse(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=api_response(
                success=False,
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=message,
                data=None,
                request_id=request_id,
                error_code="HTTP_422",
                details=details,
            ),
        )

    async def get_api_key(
        request: Request,
        x_api_key: Optional[str] = Depends(api_key_header),
        api_key: Optional[str] = None, # Query parameter
    ):
        orch = CortexOrchestrator()
        try:
            client_api_key = (os.getenv("CODECORTEX_CLIENT_API_KEY", "") or "").strip()
            if not client_api_key:
                raise HTTPException(status_code=503, detail="Server auth is not configured")

            auth_service = AuthService(conn=orch.db.conn, client_api_key=client_api_key)
            presented_key = (x_api_key or api_key or "").strip()
            result = auth_service.validate_api_key(
                presented_key,
                required_scope=None,
                request_id=_request_id(request),
                ip=_client_ip(request),
            )

            if not result.ok:
                raise HTTPException(status_code=403, detail="Could not validate credentials")

            principal = result.principal or {}
            if principal.get("llm_instance_id"):
                llm_id = principal["llm_instance_id"]
                with _llm_registry_lock:
                    _llm_registry[llm_id] = {
                        "auth_type": principal.get("auth_type"),
                        "scopes": principal.get("scopes", []),
                        "last_active": datetime.now().isoformat(),
                    }
            return principal
        finally:
            orch.db.close()

    def require_scope(scope: str):
        async def _check_scope(
            request: Request,
            principal: Dict[str, Any] = Depends(get_api_key),
        ) -> Dict[str, Any]:
            if scope not in principal.get("scopes", []):
                raise HTTPException(status_code=403, detail="Insufficient scope")
            return principal
        _check_scope.__name__ = f"require_scope_{scope.replace(':', '_')}"
        return _check_scope

    @app.post("/codecortex-api/v1/auth/handshake/init")
    async def handshake_init_api(request: Request, body: dict):
        orch = CortexOrchestrator()
        try:
            client_api_key = (os.getenv("CODECORTEX_CLIENT_API_KEY", "") or "").strip()
            if not client_api_key:
                raise HTTPException(status_code=503, detail="Server auth is not configured")
            auth_service = AuthService(conn=orch.db.conn, client_api_key=client_api_key)

            x_client_key = request.headers.get("X-CLIENT-KEY", "").strip()
            if not secrets.compare_digest(x_client_key, client_api_key):
                raise HTTPException(status_code=403, detail="Invalid bootstrap key")

            llm_instance_id = body.get("llm_instance_id", "remote-ide")
            client_nonce = body.get("client_nonce", "")

            result = auth_service.handshake_init(llm_instance_id, client_nonce)
            return {"success": True, "data": result}
        finally:
            orch.db.close()

    @app.post("/codecortex-api/v1/auth/handshake/complete")
    async def handshake_complete_api(request: Request, body: dict):
        orch = CortexOrchestrator()
        try:
            client_api_key = (os.getenv("CODECORTEX_CLIENT_API_KEY", "") or "").strip()
            if not client_api_key:
                raise HTTPException(status_code=503, detail="Server auth is not configured")
            auth_service = AuthService(conn=orch.db.conn, client_api_key=client_api_key)

            x_client_key = request.headers.get("X-CLIENT-KEY", "").strip()
            if not secrets.compare_digest(x_client_key, client_api_key):
                raise HTTPException(status_code=403, detail="Invalid bootstrap key")

            handshake_id = body.get("handshake_id", "")
            client_proof = body.get("client_proof", "")

            result = auth_service.handshake_complete(handshake_id, client_proof)
            if not result.ok:
                raise HTTPException(status_code=result.code, detail=result.message)
            return {"success": True, "data": result.principal}
        finally:
            orch.db.close()

    @app.get("/handshake", response_class=HTMLResponse)
    async def handshake_portal(request: Request):
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>CodeCortex Handshake Portal</title>
            <style>
                body { font-family: -apple-system, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 2rem; background: #f4f7f9; }
                .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                .form-group { margin-bottom: 1rem; }
                label { display: block; margin-bottom: 0.5rem; font-weight: bold; }
                input { width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
                button { background: #3498db; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 4px; cursor: pointer; font-weight: bold; }
                #result { margin-top: 2rem; display: none; }
                .config-block { background: #2c3e50; color: #ecf0f1; padding: 1rem; border-radius: 4px; font-family: monospace; }
                .success-badge { color: #27ae60; font-weight: bold; margin-bottom: 1rem; display: block; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>CodeCortex Server Handshake</h1>
                <div class="form-group">
                    <label>Client API Key (Root Secret)</label>
                    <input type="password" id="bootstrapKey">
                </div>
                <div class="form-group">
                    <label>IDE / Instance Name</label>
                    <input type="text" id="ideName" placeholder="e.g. cursor, vscode">
                </div>
                <button onclick="doHandshake()">Generate Credentials</button>
                <div id="result">
                    <span class="success-badge">✓ Credentials Generated Successfully</span>
                    <label>MCP Config (JSON Headers)</label>
                    <div class="config-block"><code id="jsonConfig"></code></div>
                </div>
            </div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js"></script>
            <script>
                async function doHandshake() {
                    const key = document.getElementById('bootstrapKey').value;
                    const ide = document.getElementById('ideName').value || 'remote-ide';
                    const nonce = Math.random().toString(36).substring(7);
                    if (!key) return alert('Key required');
                    try {
                        const initResp = await fetch('/codecortex-api/v1/auth/handshake/init', {
                            method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CLIENT-KEY': key },
                            body: JSON.stringify({ llm_instance_id: ide, client_nonce: nonce })
                        });
                        const initData = await initResp.json();
                        if (initResp.status !== 200) throw new Error(initData.detail);
                        const { handshake_id, challenge, server_nonce } = initData.data;

                        const message = `${handshake_id}:${ide}:${challenge}`;
                        const proof = CryptoJS.HmacSHA256(message, key).toString();

                        const completeResp = await fetch('/codecortex-api/v1/auth/handshake/complete', {
                            method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CLIENT-KEY': key },
                            body: JSON.stringify({ handshake_id: handshake_id, client_proof: proof })
                        });
                        const completeData = await completeResp.json();
                        if (completeResp.status !== 200) throw new Error(completeData.detail);

                        const apiKey = completeData.data.api_key;
                        const baseUrl = window.location.origin + '/codecortex-api/v1/sync';
                        document.getElementById('jsonConfig').innerText = JSON.stringify({
                            "mcpServers": {
                                "codecortex": {
                                    "command": "npx",
                                    "args": ["-y", "@modelcontextprotocol/server-sse", baseUrl],
                                    "env": {
                                        "X-API-KEY": apiKey,
                                        "X-IDE-ORIGIN": ide
                                    }
                                }
                            }
                        }, null, 2);
                        document.getElementById('result').style.display = 'block';
                    } catch (e) { alert('Handshake Error: ' + e.message); }
                }
            </script>
        </body>
        </html>
        """

    @app.get("/status")
    async def status() -> Dict[str, Any]:
        request_id = new_request_id()
        return api_response(
            success=True,
            status_code=200,
            message="OK",
            data={
                "server": {
                    "name": "codecortex",
                    "version": load_version(),
                    "identity": os.getenv("CODECORTEX_IDENTITY", "anonymous-node"),
                },
                "transport": "http-jsonrpc/sse",
                "uptime_seconds": int(time.time() - START_TIME),
                "status": "healthy",
                "features": ["code_analysis", "semantic_indexing", "architectural_mapping", "sse_streaming"],
            },
            request_id=request_id,
        )

    mcp_path = "/sync"
    mcp_secret = os.getenv("CODECORTEX_MCP_SECRET", "").strip()
    if mcp_secret:
        mcp_path = f"/sync/{mcp_secret}"
        logger.info(f"Custom MCP Secret Path activated: {mcp_path}")

    # --- MCP SSE Handler ---
    async def mcp_sse_handler(request: Request):
        async def event_generator():
            try:
                # CRITICAL: Send endpoint event first so the MCP client knows
                # where to POST JSON-RPC requests (MCP HTTP/SSE spec requirement)
                yield {
                    "event": "endpoint",
                    "data": f"/codecortex-api/v1{mcp_path}",
                }
                logger.info("SSE endpoint event sent: /codecortex-api/v1%s", mcp_path)
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

    @app.get(f"/codecortex-api/v1{mcp_path}/sse")
    async def mcp_sse_endpoint(request: Request, principal: Dict[str, Any] = Depends(require_scope("mcp:sse"))):
        return await mcp_sse_handler(request)

    @app.post(f"/codecortex-api/v1{mcp_path}")
    async def sync(request: Request, principal: Dict[str, Any] = Depends(require_scope("mcp:sync"))) -> Dict[str, Any]:
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
            # Strict JSON-RPC 2.0: only jsonrpc, id, result — no extra fields
            return {"jsonrpc": "2.0", "id": rpc_id, "result": result}

        def rpc_err(code: int, message: str, detail: Any = None) -> Dict[str, Any]:
            err: Dict[str, Any] = {"code": code, "message": message}
            if detail is not None:
                err["data"] = detail
            return {"jsonrpc": "2.0", "id": rpc_id, "error": err}

        def build_initialize_payload(requested_protocol_value: Any) -> Dict[str, Any]:
            protocol_version = (
                requested_protocol_value
                if isinstance(requested_protocol_value, str) and requested_protocol_value.strip()
                else "2025-03-26"
            )
            return {
                "protocolVersion": protocol_version,
                "serverInfo": {"name": "codecortex", "version": load_version()},
                "capabilities": {"tools": {"listChanged": False}},
            }

        # MCP Lifecycle overrides
        if not method and isinstance(payload.get("protocolVersion"), str):
            return rpc_ok(build_initialize_payload(payload.get("protocolVersion")))

        if method == "initialize":
            return rpc_ok(build_initialize_payload(params.get("protocolVersion")))

        if method == "ping":
            return rpc_ok({})

        if method == "tools/list":
            registered_tools = await mcp.list_tools()
            tools_payload = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema or {},
                }
                for t in registered_tools
            ]
            return rpc_ok({"tools": tools_payload})

        if method == "tools/call":
            tool_name = params.get("name") if isinstance(params, dict) else None
            tool_args = (params.get("arguments") or {}) if isinstance(params, dict) else {}
            if not tool_name:
                return rpc_err(-32602, "Missing 'name' in tools/call params")
            registered_tools = await mcp.list_tools()
            mcp_tools = {t.name: t for t in registered_tools}
            if tool_name not in mcp_tools:
                return rpc_err(-32601, f"Unknown tool: {tool_name}")
            try:
                call_result = await mcp.call_tool(tool_name, tool_args)
                if isinstance(call_result, tuple) and len(call_result) == 2:
                    left, right = call_result
                    if isinstance(left, list):
                        call_result = left
                    elif isinstance(right, dict) and "result" in right:
                        call_result = right.get("result")
                if hasattr(call_result, "content"):
                    content = [
                        {"type": getattr(c, "type", "text"), "text": getattr(c, "text", str(c))}
                        for c in (call_result.content or [])
                    ]
                elif isinstance(call_result, dict) and "success" in call_result:
                    text = json.dumps(_redact_sensitive(call_result), ensure_ascii=False)
                    content = [{"type": "text", "text": text}]
                elif isinstance(call_result, list):
                    content = [
                        {"type": getattr(c, "type", "text"), "text": getattr(c, "text", str(c))}
                        for c in call_result
                    ]
                else:
                    text = json.dumps(_redact_sensitive(call_result), ensure_ascii=False) if not isinstance(call_result, str) else call_result
                    content = [{"type": "text", "text": text}]
                structured = None
                if isinstance(content, list) and len(content) == 1 and isinstance(content[0], dict) and content[0].get("type") == "text":
                    raw_text = content[0].get("text")
                    if isinstance(raw_text, str) and raw_text.strip():
                        try:
                            first = json.loads(raw_text)
                            if isinstance(first, str):
                                content[0]["text"] = first
                                try:
                                    second = json.loads(first)
                                    if isinstance(second, (dict, list)):
                                        structured = second
                                except Exception:
                                    pass
                            elif isinstance(first, (dict, list)):
                                structured = first
                        except Exception:
                            pass
                payload: Dict[str, Any] = {"content": content}
                if structured is not None:
                    payload["structured"] = structured
                return rpc_ok(payload)
            except Exception as e:
                logger.exception("Tool execution failed: %s", tool_name)
                return rpc_err(-32603, f"Tool execution failed: {str(e)}")

        if not isinstance(method, str) or not method.strip():
            if rpc_id is not None:
                return rpc_err(-32602, "Missing method")
            return api_response(
                success=False,
                status_code=400,
                message="Missing method",
                data=None,
                request_id=request_id,
                error_code="RPC_002",
            )

        try:
            orchestrator = CortexOrchestrator()
            try:
                # Fallback to FastMCP tool registry
                registered_tools = await mcp.list_tools()
                mcp_tools = {t.name: t for t in registered_tools}
                if method in mcp_tools:
                    tool = mcp_tools[method]
                    # FastMCP tools are usually sync or wrapped async run()
                    if asyncio.iscoroutinefunction(tool.run):
                        result = await tool.run(**params)
                    else:
                        result = tool.run(**params)
                else:
                    msg = f"Unknown method: {method}"
                    if rpc_id is not None:
                        return rpc_err(-32601, msg)
                    return api_response(
                        success=False,
                        status_code=404,
                        message=msg,
                        data=None,
                        request_id=request_id,
                        error_code="RPC_404",
                    )

                # Standardized successful response with redaction
                redacted_data = _redact_sensitive(result)

                # If the request looks like a standard JSON-RPC, wrap it
                if rpc_id is not None:
                    # If the tool returned an api_response (dict with success=False),
                    # we should probably extract the error if it failed.
                    if isinstance(redacted_data, dict) and redacted_data.get("success") is False:
                        return rpc_err(
                            code=-32000,
                            message=redacted_data.get("message", "Tool execution failed"),
                            data=redacted_data.get("meta", {})
                        )
                    return rpc_ok(redacted_data)

                return api_response(
                    success=True,
                    status_code=200,
                    message="OK",
                    data=redacted_data,
                    request_id=request_id,
                )
            except Exception as e:
                logger.exception("Execution failed for method=%s", method)
                msg = f"Execution failed: {str(e)}"
                if rpc_id is not None:
                    return rpc_err(-32603, msg)
                return api_response(
                    success=False,
                    status_code=500,
                    message=msg,
                    data=None,
                    request_id=request_id,
                    error_code="RPC_500",
                )
            finally:
                try:
                    orchestrator.db.close()
                except Exception:
                    pass
        except Exception as e:
            logger.exception("Orchestrator initialization failed")
            msg = f"Internal Server Error: {str(e)}"
            if rpc_id is not None:
                return rpc_err(-32603, msg)
            return api_response(
                success=False,
                status_code=500,
                message=msg,
                data=None,
                request_id=request_id,
                error_code="SRV_500",
            )

    return app


def main() -> None:
    host = (os.getenv("CODECORTEX_HOST") or "127.0.0.1").strip()
    port_raw = (os.getenv("CODECORTEX_PORT") or "8001").strip()
    port = int(port_raw) if port_raw.isdigit() else 8001
    uvicorn.run("scripts.server.http:create_app", host=host, port=port, factory=True, log_level="info")


if __name__ == "__main__":
    main()

