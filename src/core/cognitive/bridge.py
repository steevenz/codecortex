"""
Cognitive Bridge — auto-discovers and communicates with neocortex Server.

Two-tier communication:
  Tier 1 (Primary): POST /api/v1/llm/analyze — dedicated REST endpoint, no MCP overhead
  Tier 2 (Fallback): POST /cognitive-api/v1/sync — MCP JSON-RPC (Streamable HTTP)

Auto-discovery flow:
  1. On first use, try connecting to neocortex via known ports
  2. If neocortex found, save URL + test Tier 1 endpoint
  3. All insight generators auto-call neocortex's LLM when available
  4. Falls back to rule-based generators when neocortex unreachable

:project: CodeCortex
:package: Core.Cognitive
:author: Steeven Andrian
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
    """Simple circuit breaker implementation for fault isolation."""

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

# Discovery order: env-configured URL first, then common ports as fallback
def _build_discovery_paths() -> list[str]:
    configured = os.environ.get("CODECORTEX_BRIDGE_NEOCORTEX_URL", "").strip().rstrip("/")
    paths = []
    if configured:
        paths.append(f"{configured}/health")
    for port in [8010, 8000, 8001, 8002]:
        paths.append(f"http://127.0.0.1:{port}/health")
    return paths

# API key env vars to try (in order) — use the bridge-specific key, not self key
_API_KEY_ENV_VARS = [
    "CODECORTEX_BRIDGE_NEOCORTEX_API_KEY",
]

_neocortex_CONFIG_PATH = Path.home() / ".codecortex" / "neocortex.json"

# ---------------------------------------------------------------------------
# Domain-specific prompt builders — one per tool:action context
# ---------------------------------------------------------------------------

def _prompt_audit(data: Any, preview: str, ctx: Dict) -> str:
    return (
        "You are a senior software architect reviewing a codebase audit report.\n\n"
        "Analyze the following architecture findings and provide:\n"
        "1. ONE-LINE executive summary of the codebase health\n"
        "2. Top 3 architectural risks (god classes, circular deps, high coupling)\n"
        "3. Prioritized refactoring recommendations with estimated impact\n"
        "4. Suggested next diagnostic steps\n\n"
        f"Audit data:\n{preview}"
    )

def _prompt_graph(data: Any, preview: str, ctx: Dict) -> str:
    return (
        "You are a code intelligence assistant analyzing a call graph / dependency graph.\n\n"
        "Given the following graph data, explain:\n"
        "1. What this call chain or dependency relationship means\n"
        "2. Potential blast radius if the target symbol changes\n"
        "3. Whether the coupling looks healthy or problematic\n"
        "4. Specific refactoring suggestions to improve structure\n\n"
        f"Graph data:\n{preview}"
    )

def _prompt_search(data: Any, preview: str, ctx: Dict) -> str:
    query = ctx.get("query", "")
    return (
        f"You are a code search assistant. The developer searched for: \"{query}\"\n\n"
        "From the following search results, explain:\n"
        "1. Which results are most relevant and why\n"
        "2. How these code elements relate to each other\n"
        "3. What the developer likely needs to understand or change\n"
        "4. Any related symbols or files they should also check\n\n"
        f"Search results:\n{preview}"
    )

def _prompt_symbols(data: Any, preview: str, ctx: Dict) -> str:
    return (
        "You are a code intelligence assistant analyzing symbol definitions.\n\n"
        "Given the following symbol data, provide:\n"
        "1. Plain-language explanation of what this symbol does\n"
        "2. Who calls it and what depends on it\n"
        "3. Any code smell indicators (too many callers, complex signature)\n"
        "4. Safe refactoring approach if needed\n\n"
        f"Symbol data:\n{preview}"
    )

def _prompt_dependencies(data: Any, preview: str, ctx: Dict) -> str:
    return (
        "You are a software architect analyzing module dependencies.\n\n"
        "Given the following dependency data, identify:\n"
        "1. Circular or problematic dependencies\n"
        "2. Modules with too many inbound dependencies (high fan-in)\n"
        "3. Modules with too many outbound dependencies (high fan-out)\n"
        "4. Recommended decoupling strategies\n\n"
        f"Dependency data:\n{preview}"
    )

def _prompt_analyze(data: Any, preview: str, ctx: Dict) -> str:
    return (
        "You are a senior engineer assessing code change impact.\n\n"
        "Given the following analysis results, determine:\n"
        "1. What was found and its significance\n"
        "2. Risk level for any proposed changes (low/medium/high)\n"
        "3. Files or modules most likely to break on change\n"
        "4. Recommended testing strategy before making changes\n\n"
        f"Analysis data:\n{preview}"
    )

def _prompt_repository(data: Any, preview: str, ctx: Dict) -> str:
    return (
        "You are a DevOps and architecture expert reviewing a repository summary.\n\n"
        "Based on the following repository data, provide:\n"
        "1. Overall repository health assessment\n"
        "2. Key structural observations (entry points, tech stack, size)\n"
        "3. Potential onboarding friction points\n"
        "4. Suggested first areas of investigation\n\n"
        f"Repository data:\n{preview}"
    )

def _prompt_filesystem_tree(data: Any, preview: str, ctx: Dict) -> str:
    return (
        "You are a software engineer reviewing a project's directory structure.\n\n"
        "Given the following file tree, provide:\n"
        "1. High-level project layout summary (what each top-level folder does)\n"
        "2. Entry points and key configuration files to be aware of\n"
        "3. Any structural red flags (deeply nested logic, misplaced files, missing folders)\n"
        "4. Onboarding guidance: where to start reading this codebase\n\n"
        f"File tree:\n{preview}"
    )

def _prompt_filesystem_search(data: Any, preview: str, ctx: Dict) -> str:
    query = ctx.get("query", ctx.get("pattern", ""))
    return (
        f"You are a code navigator. The developer searched for: \"{query}\"\n\n"
        "From these file search results, explain:\n"
        "1. Which files are most relevant to the query and why\n"
        "2. What these files likely contain based on their names and paths\n"
        "3. The recommended reading order for understanding the feature\n\n"
        f"Search results:\n{preview}"
    )

def _prompt_filesystem_audit(data: Any, preview: str, ctx: Dict) -> str:
    return (
        "You are a code quality engineer reviewing filesystem health.\n\n"
        "Analyze the following filesystem audit and identify:\n"
        "1. Large or bloated files that may need splitting\n"
        "2. Orphaned or dead files not referenced anywhere\n"
        "3. Naming inconsistencies or misplaced files\n"
        "4. Cleanup recommendations with priority order\n\n"
        f"Audit data:\n{preview}"
    )

def _prompt_idegraph_search(data: Any, preview: str, ctx: Dict) -> str:
    query = ctx.get("query", "")
    return (
        f"You are reviewing past AI coding decisions related to: \"{query}\"\n\n"
        "From these historical IDE interactions, extract:\n"
        "1. Relevant decisions already made about this topic\n"
        "2. Approaches that were tried and their outcomes\n"
        "3. Any constraints or context the developer established\n"
        "4. How this historical context should inform the current request\n\n"
        f"Past decisions:\n{preview}"
    )

def _prompt_idegraph_workspace(data: Any, preview: str, ctx: Dict) -> str:
    return (
        "You are analyzing the current workspace state across multiple IDEs.\n\n"
        "Given this cross-IDE workspace snapshot, summarize:\n"
        "1. What the developer is currently working on (active files, branch)\n"
        "2. Any uncommitted changes that may affect the current task\n"
        "3. Which IDEs are active and what each is focused on\n"
        "4. Potential conflicts or coordination issues between IDEs\n\n"
        f"Workspace data:\n{preview}"
    )

def _prompt_knowledge_query(data: Any, preview: str, ctx: Dict) -> str:
    query = ctx.get("query", "")
    return (
        f"You are a technical knowledge assistant. The developer queried: \"{query}\"\n\n"
        "From the following documentation and specification results, provide:\n"
        "1. Direct answer to the query from the docs\n"
        "2. Key requirements or constraints from specs that apply\n"
        "3. API contracts or interfaces relevant to this topic\n"
        "4. Gaps in documentation the developer should be aware of\n\n"
        f"Knowledge results:\n{preview}"
    )

def _prompt_knowledge_relationships(data: Any, preview: str, ctx: Dict) -> str:
    concept = ctx.get("query", "concept")
    return (
        f"You are a knowledge graph analyst. Concept under analysis: \"{concept}\"\n\n"
        "From the following relationship data, explain:\n"
        "1. How this concept connects to other parts of the system\n"
        "2. Which code modules implement or use this concept\n"
        "3. Which docs or specs define it\n"
        "4. Potential impacts on related areas if this concept changes\n\n"
        f"Relationship data:\n{preview}"
    )

def _prompt_codebase_index(data: Any, preview: str, ctx: Dict) -> str:
    return (
        "You are reviewing codebase index status for a software project.\n\n"
        "Given the following index data, assess:\n"
        "1. Index freshness — is it up to date or stale?\n"
        "2. Coverage — any files or languages not indexed?\n"
        "3. Symbol extraction quality (total symbols vs file count ratio)\n"
        "4. Whether re-indexing is recommended before proceeding\n\n"
        f"Index data:\n{preview}"
    )

def _prompt_generic(tool_name: str, data: Any, preview: str) -> str:
    if isinstance(data, dict):
        keys = ", ".join(list(data.keys())[:8])
    elif isinstance(data, list):
        keys = f"{len(data)} items"
    else:
        keys = type(data).__name__
    return (
        f"Tool '{tool_name}' returned data with fields: {keys}.\n\n"
        "Analyze this data and produce a concise structured insight:\n"
        "- summary: one-line what was found\n"
        "- recommendations: actionable suggestions\n"
        "- critical_issues: urgent findings if any\n"
        "- risk_level: low/medium/high\n\n"
        f"Data:\n{preview}"
    )

_PROMPT_BUILDERS: Dict[str, Any] = {
    # codebase
    "codebase:audit":          _prompt_audit,
    "codebase:graph":          _prompt_graph,
    "codebase:search":         _prompt_search,
    "codebase:symbols":        _prompt_symbols,
    "codebase:dependencies":   _prompt_dependencies,
    "codebase:analyze":        _prompt_analyze,
    "codebase:metrics":        _prompt_analyze,
    "codebase:index":          _prompt_codebase_index,
    "codebase:status":         _prompt_codebase_index,
    # repository
    "repository":              _prompt_repository,
    "repository:inspect":      _prompt_repository,
    "repository:analyze":      _prompt_repository,
    "repository:audit":        _prompt_audit,
    # filesystem
    "filesystem:search":       _prompt_filesystem_search,
    "filesystem:audit":        _prompt_filesystem_audit,
    "filesystem:read":         _prompt_filesystem_tree,
    # idegraph
    "idegraph:search":         _prompt_idegraph_search,
    "idegraph:workspace":      _prompt_idegraph_workspace,
    "idegraph:harvest":        _prompt_idegraph_workspace,
    "idegraph:list":           _prompt_idegraph_search,
    # knowledge
    "knowledge:query":         _prompt_knowledge_query,
    "knowledge:relationships": _prompt_knowledge_relationships,
    "knowledge:extract":       _prompt_knowledge_query,
}


class CortexBridge:
    """
    Auto-discovers neocortex Server and provides AI enrichment for CodeCortex outputs.

    Enhanced with:
    - Circuit breaker pattern for fault isolation
    - Retry logic with exponential backoff
    - Configurable timeouts
    - Connection pooling
    - Structured logging

    Singleton — initialized once, cached.
    """

    _instance: Optional["CortexBridge"] = None

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
    def instance(cls) -> "CortexBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

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

        env_url = os.environ.get("CODECORTEX_BRIDGE_NEOCORTEX_URL", "") or os.environ.get("neocortex_SERVER_URL", "")
        if env_url:
            base = self._normalize_url(env_url)
            if self._ping(f"{base}/health"):
                self.neocortex_url = base
                self._available = True
                self._checked = True
                self._save_config(base)
                return True

        self._available = False
        self._checked = True
        self._log_event("BRIDGE_UNAVAILABLE")
        return False

    def _normalize_url(self, url: str) -> str:
        return url.replace("/health", "").replace("/cognitive-api/v1/sync", "").rstrip("/")

    def enrich(
        self,
        tool_name: str,
        data: Any,
        context: Optional[Dict[str, Any]] = None,
        project_id: str = "default",
    ) -> Optional[str]:
        if not self.available():
            return None

        ctx = {"tool": tool_name, "data_preview": str(data)[:2000], **(context or {})}

        if len(str(data)) > self.max_prompt_size:
            self._log_event("DATA_TRUNCATED", tool_name=tool_name, original_size=len(str(data)), max_size=self.max_prompt_size)
            data = str(data)[:self.max_prompt_size]

        prompt = self._build_prompt(tool_name, data, ctx)

        try:
            result = self._circuit_breaker.call(self._call_rest, prompt, ctx, project_id)
            if result:
                return result
        except Exception:
            pass

        return self._call_mcp(prompt, ctx, project_id)

    def register_project(self, project_id: str, display_name: str = "") -> bool:
        if not self.available():
            return False
        payload = {
            "jsonrpc": "2.0", "id": f"ccx_reg_{project_id}", "method": "tools/call",
            "params": {"name": "project_register", "arguments": {
                "project_id": project_id, "display_name": display_name or project_id,
            }},
        }
        try:
            self._call_mcp_raw(payload)
            logger.info(f"[Bridge] Auto-registered project: {project_id}")
            return True
        except Exception as e:
            logger.debug(f"[Bridge] project_register failed: {e}")
            return False

    def available(self) -> bool:
        if not self._checked:
            self.discover()
        return self._available

    # ── REST endpoint (Tier 1) ──

    def _get_client(self) -> Any:
        """Get or create pooled HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.Client(
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
                timeout=self.rest_timeout
            )
        return self._client

    def _log_event(self, event: str, **kwargs):
        logger.info(f"[{event}]", extra={"event": event, **kwargs})

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

    # ── MCP JSON-RPC (Tier 2 fallback) ──

    def _call_mcp(self, prompt: str, context: Dict, project_id: str) -> Optional[str]:
        import uuid as _uuid
        payload = {
            "jsonrpc": "2.0", "id": f"ccx_{_uuid.uuid4().hex[:8]}", "method": "tools/call",
            "params": {
                "name": "llm_analyze",
                "arguments": {
                    "prompt": prompt, "context": context,
                    "format": "insight", "project_id": project_id,
                },
            },
        }
        result = self._call_mcp_raw(payload)
        if result:
            return str(result)
        return None

    def _call_mcp_raw(self, payload: Dict) -> Optional[Any]:
        if not self.neocortex_url:
            return None
        url = f"{self.neocortex_url}/cognitive-api/v1/sync"
        try:
            import httpx
            resp = httpx.post(url, json=payload, headers=self._headers(), timeout=30.0)
            if resp.status_code == 200:
                rpc = resp.json()
                if "result" in rpc:
                    r = rpc["result"]
                    if isinstance(r, list) and r and isinstance(r[0], list):
                        cl = r[0]
                        if cl and isinstance(cl[0], dict) and cl[0].get("type") == "text":
                            try:
                                parsed = json.loads(cl[0]["text"])
                                return parsed.get("data", {}).get("content", cl[0]["text"])
                            except Exception:
                                return cl[0]
                    return r
                if "error" in rpc:
                    logger.debug(f"[Bridge] MCP error: {rpc['error']}")
            return None
        except Exception as e:
            logger.debug(f"[Bridge] MCP call failed: {e}")
            return None

    # ── Helpers ──

    def _headers(self) -> Dict[str, str]:
        h = {}
        if self._api_key:
            h["X-API-KEY"] = self._api_key
        return h

    def _resolve_api_key(self) -> str:
        for var in _API_KEY_ENV_VARS:
            val = os.environ.get(var, "")
            if val:
                return val
        return ""

    def _ping(self, url: str) -> bool:
        health = url.replace("/cognitive-api/v1/sync", "/health")
        try:
            import httpx
            resp = httpx.get(health, headers=self._headers(), timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def _build_prompt(self, tool_name: str, data: Any, context: Optional[Dict[str, Any]] = None) -> str:
        action = (context or {}).get("action", "")
        preview = str(data)[:3000]
        key = f"{tool_name}:{action}" if action else tool_name
        builder = _PROMPT_BUILDERS.get(key) or _PROMPT_BUILDERS.get(tool_name)
        if builder:
            return builder(data, preview, context or {})
        return _prompt_generic(tool_name, data, preview)

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
            _neocortex_CONFIG_PATH.write_text(json.dumps({
                "url": url, "discovered_at": str(__import__("datetime").datetime.now()),
            }, indent=2))
        except Exception:
            pass
