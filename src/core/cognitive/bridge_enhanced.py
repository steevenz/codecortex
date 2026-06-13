"""
Enhanced Cognitive Bridge — auto-discovers and communicates with neocortex Server.

Enhanced version with:
- Circuit breaker pattern
- Retry logic with exponential backoff
- Configurable timeouts
- Connection pooling
- Structured logging

:project: CodeCortex
:package: Core.Cognitive
:author: Steeven Andrian (Enhanced)
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CrossStack-v1.0
"""

from __future__ import annotations

import json
import os
import logging
import uuid
import time
from typing import Any, Dict, Optional
from pathlib import Path
from functools import wraps
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_neocortex_CONFIG_PATH = Path.home() / ".coddy" / "codecortex" / "neocortex.json"
_MAX_PROMPT_ITEMS = 8
_MAX_STRING_LEN = 120
_LLM_ERROR_MARKERS = (
    "[ERROR]",
    "[No LLM available",
    "Autonomous reasoning unavailable",
    "Fallback to guided mode required",
)


def _new_request_id() -> str:
    return f"ccx_{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_str(value: Any, max_len: int = _MAX_STRING_LEN) -> str:
    return str(value)[:max_len] if value is not None else ""


def _safe_list(items: Any, max_items: int = _MAX_PROMPT_ITEMS) -> list:
    if not isinstance(items, list):
        return []
    result = []
    for item in items[:max_items]:
        if isinstance(item, dict):
            label = item.get("type") or item.get("name") or item.get("kind") or "unknown"
            result.append(_safe_str(label, 60))
        elif isinstance(item, str):
            result.append(_safe_str(item, 60))
    return result


class CircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"

    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


def retry_with_backoff(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.debug(f"Retry attempt {attempt + 1}/{max_attempts} after {delay}s")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


class EnhancedCortexBridge:
    """
    Enhanced auto-discovery and AI enrichment with resilience patterns.

    Features:
    - Circuit breaker for fault isolation
    - Retry with exponential backoff
    - Connection pooling
    - Configurable timeouts
    - Structured logging
    """

    _instance: Optional["EnhancedCortexBridge"] = None

    def __init__(self):
        self.neocortex_url: Optional[str] = None
        self._available: bool = False
        self._checked: bool = False
        self._api_key: str = ""
        self.rest_timeout = float(os.environ.get("CODECORTEX_BRIDGE_REST_TIMEOUT", "60.0"))
        self.mcp_timeout = float(os.environ.get("CODECORTEX_BRIDGE_MCP_TIMEOUT", "30.0"))
        self.max_prompt_size = int(os.environ.get("CODECORTEX_BRIDGE_MAX_PROMPT_SIZE", "10000"))
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        self._client: Optional[Any] = None

    @classmethod
    def instance(cls) -> "EnhancedCortexBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_client(self) -> Any:
        """Get or create pooled HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.Client(
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
                timeout=self.rest_timeout
            )
        return self._client

    def discover(self, force: bool = False) -> bool:
        if self._checked and not force:
            return self._available

        if os.environ.get("CODECORTEX_BRIDGE_ENABLED", "true").lower() in ("0", "false", "no"):
            self._available = False
            self._checked = True
            return False

        self._api_key = self._resolve_api_key()

        saved_url = self._load_config()
        if saved_url and self._ping(saved_url):
            self.neocortex_url = saved_url
            self._available = True
            self._checked = True
            self._log_event("BRIDGE_DISCOVERED", method="config")
            return True

        for url in self._build_discovery_paths():
            if self._ping(url):
                base = self._normalize_url(url)
                self.neocortex_url = base
                self._available = True
                self._checked = True
                self._save_config(base)
                self._log_event("BRIDGE_DISCOVERED", method="probe")
                return True

        self._available = False
        self._checked = True
        self._log_event("BRIDGE_UNAVAILABLE")
        return False

    def available(self) -> bool:
        if not self._checked:
            self.discover()
        return self._available

    @retry_with_backoff(max_attempts=3)
    def _call_rest(self, prompt: str, context: Dict, project_id: str) -> Optional[str]:
        if not self.neocortex_url:
            return None

        url = f"{self.neocortex_url}/api/v1/llm/analyze"
        request_id = _new_request_id()
        t0 = time.time()

        try:
            client = self._get_client()
            resp = client.post(
                url,
                json={"prompt": prompt, "context": context, "format": "insight", "project_id": project_id},
                headers=self._headers(),
            )

            latency_ms = (time.time() - t0) * 1000
            self._log_event("BRIDGE_CALL", request_id=request_id, latency_ms=latency_ms, status="success")

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    return data["data"]["content"]
            return None
        except Exception as e:
            latency_ms = (time.time() - t0) * 1000
            self._log_event("BRIDGE_CALL_FAILED", request_id=request_id, latency_ms=latency_ms, error=str(e))
            raise

    def enrich(self, tool_name: str, data: Any, context: Optional[Dict] = None, project_id: str = "default") -> Optional[str]:
        if not self.available():
            return None

        ctx = {"tool": tool_name, "data_preview": str(data)[:2000], **(context or {})}

        if len(str(data)) > self.max_prompt_size:
            logger.warning("Data truncated due to size limit", extra={"original_size": len(str(data)), "max_size": self.max_prompt_size})
            data = str(data)[:self.max_prompt_size]

        prompt = self._build_prompt(tool_name, data, ctx)

        try:
            result = self._circuit_breaker.call(self._call_rest, prompt, ctx, project_id)
            if result:
                return result
        except Exception:
            pass

        return self._call_mcp(prompt, ctx, project_id)

    def _call_mcp(self, prompt: str, context: Dict, project_id: str) -> Optional[str]:
        import httpx
        payload = {
            "jsonrpc": "2.0",
            "id": _new_request_id(),
            "method": "tools/call",
            "params": {"name": "llm_analyze", "arguments": {"prompt": prompt, "context": context, "format": "insight", "project_id": project_id}},
        }

        try:
            client = self._get_client()
            resp = client.post(f"{self.neocortex_url}/cognitive-api/v1/sync", json=payload, headers=self._headers())
            if resp.status_code == 200:
                rpc = resp.json()
                if "result" in rpc:
                    return str(rpc["result"])
        except Exception:
            pass
        return None

    def _headers(self) -> Dict[str, str]:
        h = {}
        if self._api_key:
            h["X-API-KEY"] = self._api_key
        return h

    def _resolve_api_key(self) -> str:
        for var in ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY", "NEOCORTEX_CLIENT_API_KEY", "neocortex_SERVER_API_KEY"]:
            val = os.environ.get(var, "")
            if val:
                return val
        return ""

    def _ping(self, url: str) -> bool:
        try:
            client = self._get_client()
            resp = client.get(f"{self._normalize_url(url)}/health", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def _normalize_url(self, url: str) -> str:
        return url.replace("/health", "").replace("/cognitive-api/v1/sync", "").rstrip("/")

    def _build_discovery_paths(self) -> list[str]:
        configured = os.environ.get("CODECORTEX_BRIDGE_NEOCORTEX_URL", "").strip().rstrip("/")
        paths = []
        if configured:
            paths.append(f"{configured}/health")
        for port in [8010, 8000, 8001, 8002]:
            paths.append(f"http://127.0.0.1:{port}/health")
        return paths

    def _log_event(self, event: str, **kwargs):
        logger.info(f"[{event}]", extra={"event": event, **kwargs})

    def _build_prompt(self, tool_name: str, data: Any, context: Dict) -> str:
        preview = str(data)[:3000]
        return f"Tool '{tool_name}' returned data: {preview}. Analyze and provide insight."

    def _load_config(self) -> Optional[str]:
        try:
            if _neocortex_CONFIG_PATH.exists():
                return json.loads(_neocortex_CONFIG_PATH.read_text()).get("url")
        except Exception:
            pass
        return None

    def _save_config(self, url: str) -> None:
        try:
            _neocortex_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            _neocortex_CONFIG_PATH.write_text(json.dumps({"url": url, "discovered_at": _utcnow()}, indent=2))
        except Exception:
            pass

    def close(self):
        if self._client:
            self._client.close()
            self._client = None


CortexBridge = EnhancedCortexBridge
