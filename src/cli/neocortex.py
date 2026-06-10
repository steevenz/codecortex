"""neocortex (Creative Critical Thinking) proxy CLI commands."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from src.cli.common import ok, err

_neocortex_CACHE_PATH = Path.home() / ".codecortex" / "neocortex_endpoint.json"


def _neocortex_url(args_ns: argparse.Namespace) -> str:
    explicit = getattr(args_ns, "neocortex_url", None) or os.getenv("neocortex_URL", "")
    if explicit:
        return explicit
    try:
        if _neocortex_CACHE_PATH.exists():
            data = json.loads(_neocortex_CACHE_PATH.read_text())
            return data.get("url", "")
    except Exception:
        pass
    return "http://127.0.0.1:8001"


def _neocortex_call(method: str, params: Dict, neocortex_url: str) -> Dict:
    import httpx
    sync_url = neocortex_url.rstrip("/")
    if not sync_url.endswith("/v1/sync"):
        if sync_url.endswith("/health"):
            sync_url = sync_url.replace("/health", "/cognitive-api/v1/sync")
        elif sync_url.endswith("/cognitive-api"):
            sync_url = sync_url + "/v1/sync"
        else:
            sync_url = sync_url + "/cognitive-api/v1/sync"
    payload = {
        "jsonrpc": "2.0", "id": f"cli_{method}", "method": "tools/call",
        "params": {"name": method, "arguments": params},
    }
    try:
        resp = httpx.post(sync_url, json=payload, timeout=120)
        if resp.status_code == 200:
            rpc = resp.json()
            if "result" in rpc:
                result_data = rpc["result"]
                if isinstance(result_data, list) and result_data and isinstance(result_data[0], list):
                    content_list = result_data[0]
                    if content_list and isinstance(content_list[0], dict) and content_list[0].get("type") == "text":
                        try:
                            result_data = json.loads(content_list[0]["text"])
                        except Exception:
                            result_data = content_list[0]
                return result_data
            if "error" in rpc:
                return err(rpc["error"].get("message", str(rpc["error"])), "neocortex_RPC_ERROR", 500)
            return ok("neocortex call complete", rpc)
        return err(f"neocortex server returned {resp.status_code}", "neocortex_CONNECT_ERROR", 503)
    except httpx.ConnectError:
        return err(f"Cannot connect to neocortex at {sync_url}", "neocortex_CONNECT_ERROR", 503)
    except Exception as e:
        return err(f"neocortex call failed: {e}", "neocortex_ERROR", 500)


def _neocortex_register_endpoint(endpoint: str) -> Dict:
    try:
        _neocortex_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _neocortex_CACHE_PATH.write_text(json.dumps({"url": endpoint, "saved_at": str(__import__("datetime").datetime.now())}))
        saved = _neocortex_CACHE_PATH.exists()
        return ok("neocortex endpoint registered", {"url": endpoint, "saved": saved})
    except Exception as e:
        return err(f"Failed to save endpoint: {e}", "neocortex_SAVE_ERROR")


def cmd_neocortex_think_start(args_ns: argparse.Namespace) -> Dict:
    url = _neocortex_url(args_ns)
    params = {
        "problem_statement": args_ns.problem,
        "profile": getattr(args_ns, "profile", "balanced"),
        "project_id": getattr(args_ns, "project_id", "default"),
        "model_id": getattr(args_ns, "model", ""),
    }
    if getattr(args_ns, "code_context", None):
        params["code_snippet"] = args_ns.code_context
    return _neocortex_call("thinking_start", params, url)


def cmd_neocortex_analyze(args_ns: argparse.Namespace) -> Dict:
    url = _neocortex_url(args_ns)
    context = {}
    if getattr(args_ns, "code_context", None):
        context["code"] = args_ns.code_context
    if getattr(args_ns, "repo_path", None):
        context["repo_path"] = args_ns.repo_path
    return _neocortex_call("llm_analyze", {
        "prompt": args_ns.prompt,
        "context": context or None,
        "format": getattr(args_ns, "format", "insight"),
        "project_id": getattr(args_ns, "project_id", "default"),
    }, url)


def cmd_neocortex_projects(args_ns: argparse.Namespace) -> Dict:
    return _neocortex_call("project_list", {}, _neocortex_url(args_ns))


def cmd_neocortex_project_add(args_ns: argparse.Namespace) -> Dict:
    return _neocortex_call("project_register", {
        "project_id": args_ns.project_id,
        "display_name": getattr(args_ns, "display_name", ""),
    }, _neocortex_url(args_ns))


def cmd_neocortex_project_status(args_ns: argparse.Namespace) -> Dict:
    return _neocortex_call("project_status", {
        "project_id": args_ns.project_id,
    }, _neocortex_url(args_ns))


def cmd_neocortex_code_analyze(args_ns: argparse.Namespace) -> Dict:
    return _neocortex_call("codecortex_analyze", {
        "query": args_ns.query,
        "repo_path": getattr(args_ns, "repo_path", ""),
        "project_id": getattr(args_ns, "project_id", "default"),
    }, _neocortex_url(args_ns))


def cmd_neocortex_code_search(args_ns: argparse.Namespace) -> Dict:
    return _neocortex_call("codecortex_search", {
        "query": args_ns.query,
        "repo_path": getattr(args_ns, "repo_path", ""),
        "search_type": getattr(args_ns, "search_type", "code"),
        "limit": getattr(args_ns, "limit", 10),
        "project_id": getattr(args_ns, "project_id", "default"),
    }, _neocortex_url(args_ns))


COMMANDS = {
    "think-start": cmd_neocortex_think_start,
    "analyze": cmd_neocortex_analyze,
    "projects": cmd_neocortex_projects,
    "project-add": cmd_neocortex_project_add,
    "project-status": cmd_neocortex_project_status,
    "code-analyze": cmd_neocortex_code_analyze,
    "code-search": cmd_neocortex_code_search,
}


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("neocortex", help="Proxy commands to neocortex Server")
    sp = p.add_subparsers(dest="neocortex_action", required=True)

    sp.add_parser("projects", help="List all neocortex projects")

    pa = sp.add_parser("project-add", help="Register a new neocortex project")
    pa.add_argument("project_id", help="Project ID")
    pa.add_argument("--display-name", help="Display name")

    ps = sp.add_parser("project-status", help="Get project health")
    ps.add_argument("project_id", help="Project ID")

    ts = sp.add_parser("think-start", help="Start a neocortex thinking session")
    ts.add_argument("problem", help="Problem statement")
    ts.add_argument("--profile", default="balanced", help="Profile: balanced, creative, critical, mimic_user")
    ts.add_argument("--project-id", default="default", help="Project ID")
    ts.add_argument("--model", default="", help="LLM model ID")
    ts.add_argument("--code-context", help="Optional code snippet for context")
    ts.add_argument("--neocortex-url", help="neocortex server URL override")

    an = sp.add_parser("analyze", help="LLM analyze via neocortex (lightweight)")
    an.add_argument("prompt", help="Analysis prompt")
    an.add_argument("--format", default="insight", help="insight|summary|remediation|explain|free")
    an.add_argument("--project-id", default="default", help="Project ID")
    an.add_argument("--code-context", help="Optional code context")
    an.add_argument("--repo-path", help="Repository path for context")
    an.add_argument("--neocortex-url", help="neocortex server URL override")

    ca = sp.add_parser("code-analyze", help="Analyze code via CodeCortex thru neocortex")
    ca.add_argument("query", help="Code question / symbol")
    ca.add_argument("--repo-path", default="", help="Repository path")
    ca.add_argument("--project-id", default="default", help="Project ID")
    ca.add_argument("--neocortex-url", help="neocortex server URL override")

    cs = sp.add_parser("code-search", help="Search code via CodeCortex thru neocortex")
    cs.add_argument("query", help="Search query")
    cs.add_argument("--repo-path", default="", help="Repository path")
    cs.add_argument("--search-type", default="code", help="code|symbols")
    cs.add_argument("--limit", type=int, default=10, help="Max results")
    cs.add_argument("--project-id", default="default", help="Project ID")
    cs.add_argument("--neocortex-url", help="neocortex server URL override")

    p.add_argument("--neocortex-url", help="neocortex server URL (default: http://127.0.0.1:8001)")
