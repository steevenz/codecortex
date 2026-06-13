"""
Shared helpers for CodeCortex CLI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform as _platform
import socket as _socket
import sys
import uuid as _uuid
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def output(data: Any, pretty: bool = True) -> None:
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    text = json.dumps(data, **kwargs, default=str)
    buf = sys.stdout.buffer
    buf.write(text.encode("utf-8", errors="replace"))
    buf.write(b"\n")
    buf.flush()


def ok(message: str, data: Any = None) -> Dict[str, Any]:
    return {"success": True, "status_code": 200, "message": message, "data": data}


def err(message: str, code: str = "CLI_ERROR", status: int = 400) -> Dict[str, Any]:
    return {"success": False, "status_code": status, "message": message, "data": {"explanation": f"No relevant data is available because an error occurred: {message}"}, "error_code": code}


def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


_LOCAL_DEVICE_ID: Optional[str] = None


def _register_device(cfg_file: Path) -> str:
    global _LOCAL_DEVICE_ID
    did = str(_uuid.uuid4())
    cfg_file.write_text(json.dumps({
        "device_id": did,
        "hostname": _socket.gethostname(),
        "os": f"{_platform.system()} {_platform.release()}",
        "user_home": str(Path.home()),
    }, indent=2), encoding="utf-8")
    _LOCAL_DEVICE_ID = did
    return did


def _get_device_id() -> str:
    global _LOCAL_DEVICE_ID
    if _LOCAL_DEVICE_ID:
        return _LOCAL_DEVICE_ID
    cfg_dir = Path.home() / ".coddy" / "codecortex"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / "device.json"
    if cfg_file.exists():
        try:
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            _LOCAL_DEVICE_ID = data.get("device_id", "")
            return _LOCAL_DEVICE_ID or _register_device(cfg_file)
        except Exception:
            pass
    return _register_device(cfg_file)


def _remote_url(args_ns: argparse.Namespace) -> Optional[str]:
    url = getattr(args_ns, "remote", None) or os.getenv("CODECORTEX_REMOTE", "")
    return url.strip() or None


def _remote_headers() -> Dict[str, str]:
    return {
        "X-Device-ID": _get_device_id(),
        "X-Device-Hostname": _socket.gethostname(),
        "X-Device-OS": f"{_platform.system()} {_platform.release()}",
        "X-Device-Home": str(Path.home()),
    }


def _get(ns, key, default=None):
    return getattr(ns, key, default)


def _send_remote(remote_url: str, domain: str, args_ns: argparse.Namespace, domain_registry: Dict) -> Dict:
    import httpx
    remote_routes = {
        "repository": {
            "method": "repository",
            "params": lambda ns: {
                "action": _get(ns, "repo_action"),
                "repo_path": _get(ns, "path") or _get(ns, "target"),
                "repo_id": _get(ns, "repo_id"),
            },
        },
        "filesystem": {
            "method": "filesystem",
            "params": lambda ns: {
                "action": _get(ns, "fs_action"),
                "path": _get(ns, "path") or _get(ns, "root") or _get(ns, "target") or _get(ns, "src"),
                "repo_id": _get(ns, "repo_id"),
            },
        },
        "codebase": {
            "method": "codebase",
            "params": lambda ns: {
                "action": _get(ns, "cb_action"),
                "repo_path": _get(ns, "target") or _get(ns, "path"),
                "repo_id": _get(ns, "repo_id"),
            },
        },
        "scaffolder": {
            "method": "scaffolder",
            "params": lambda ns: {
                "action": _get(ns, "sc_action"),
            },
        },
        "knowledge": {
            "method": "knowledge_graph",
            "params": lambda ns: {
                "action": _get(ns, "kg_action"),
                "repo_path": _get(ns, "repo_path"),
                "task": _get(ns, "task"),
                "knowledge_types": _get(ns, "types"),
                "min_importance": _get(ns, "min_importance", 0.0),
                "limit": _get(ns, "limit", 20),
            },
        },
        "idegraph": {
            "method": "idegraph",
            "params": lambda ns: {
                "action": _get(ns, "ig_action"),
                "query": _get(ns, "query"),
                "memory_id": _get(ns, "id"),
                "project_path": _get(ns, "project_path"),
                "project_name": _get(ns, "project"),
                "workspace_key": _get(ns, "workspace_key"),
                "ide_name": _get(ns, "ide"),
                "limit": _get(ns, "limit", 20),
                "offset": _get(ns, "offset", 0),
            },
        },
        "codegraph": {
            "method": "codegraph",
            "params": lambda ns: {
                "action": _get(ns, "cg_action"),
                "repo_path": _get(ns, "repo_path"),
                "repo_id": _get(ns, "repo_id"),
                "query_type": _get(ns, "query_type"),
                "target": _get(ns, "target"),
                "refactor_action": _get(ns, "refactor_action"),
                "refactor_type": _get(ns, "refactor_type"),
                "target_node": _get(ns, "target_node"),
                "limit": _get(ns, "limit", 20),
            },
        },
    }
    domain_map = {
        "repo": "repository", "repository": "repository",
        "fs": "filesystem", "filesystem": "filesystem",
        "cb": "codebase", "codebase": "codebase",
        "sc": "scaffolder", "scaffolder": "scaffolder",
        "kg": "knowledge", "knowledge": "knowledge",
        "ig": "idegraph", "idegraph": "idegraph",
        "cg": "codegraph", "codegraph": "codegraph",
    }
    canonical = domain_map.get(domain, domain)
    route = remote_routes.get(canonical)
    if not route:
        return err(f"Domain '{domain}' not supported for remote execution", "REMOTE_UNSUPPORTED")
    method = route["method"]
    params = route["params"](args_ns)
    if not params.get("action"):
        return err(f"No action specified for {domain}", "REMOTE_NO_ACTION")
    params = {k: v for k, v in params.items() if v is not None}
    headers = _remote_headers()
    api_key = os.getenv("CODECORTEX_CLIENT_API_KEY")
    if api_key:
        headers["X-API-KEY"] = api_key
    try:
        resp = httpx.post(
            f"{remote_url}/codecortex-api/v1/sync",
            json={"method": method, "params": params, "id": 1},
            headers=headers,
            timeout=120,
        )
        rpc = resp.json()
        if "result" in rpc:
            result_data = rpc["result"]
            if isinstance(result_data, list):
                if len(result_data) >= 1 and isinstance(result_data[0], list):
                    content_list = result_data[0]
                    if content_list and isinstance(content_list[0], dict) and content_list[0].get("type") == "text":
                        try:
                            result_data = json.loads(content_list[0]["text"])
                        except Exception:
                            result_data = content_list[0]
            return result_data
        if "error" in rpc:
            return err(rpc["error"].get("message", str(rpc["error"])), "REMOTE_RPC_ERROR", 500)
        return ok("Remote execution complete", rpc)
    except httpx.ConnectError:
        return err(f"Cannot connect to server at {remote_url}", "REMOTE_CONNECT_ERROR", 503)
    except Exception as e:
        return err(f"Remote execution failed: {e}", "REMOTE_ERROR", 500)


def cmd_version(args_ns: argparse.Namespace) -> Dict:
    from src.core import load_version
    data = {
        "version": load_version(),
        "cli_version": "2.0.0",
        "tools": {
            "repository": 15,
            "filesystem": 12,
            "codebase": 8,
            "scaffolder": 7,
            "knowledge": 4,
            "idegraph": 10,
            "codegraph": 7,
            "remote": 4,
            "cloud": 5,
            "server": 3,
        },
    }
    remote_url_val = _remote_url(args_ns)
    if remote_url_val:
        data["server_url"] = remote_url_val
    return ok("CodeCortex CLI", data)
