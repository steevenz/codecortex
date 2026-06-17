#!/usr/bin/env python3
"""CodeCortex CLI adapter.

The CLI is a transport adapter over the same MCP tools. It exists so
host agents can call CodeCortex as deterministic subprocess tools without
speaking MCP.

JSON mode contract:
- stdout: exactly one JSON object
- stderr: logs/diagnostics only
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import os
import sys
from pathlib import Path

# Bypass safeguard for CLI mode — no stale instance scanning needed
os.environ.setdefault("CODECORTEX_SKIP_SAFEGUARD", "1")
from typing import Dict, Any, Optional

# Fix sys.path for internal imports
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


VERSION = "0.1.0"


def _write_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False))


def _ok(tool: str, action: str, result: Any) -> Dict[str, Any]:
    return {
        "success": True,
        "status_code": 200,
        "tool": tool,
        "action": action,
        "data": result,
        "meta": {"adapter": "cli", "schema_version": 1}
    }


def _fail(code: str, message: str, **details) -> Dict[str, Any]:
    return {
        "success": False,
        "status_code": 400,
        "error_code": code,
        "message": message,
        "data": details,
        "meta": {"adapter": "cli", "schema_version": 1}
    }


def _read_stdin_request() -> tuple[str, str, Dict[str, Any]]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("stdin JSON is empty")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("stdin JSON must be an object")
    tool = str(payload.get("tool", "")).strip()
    action = str(payload.get("action", "")).strip()
    args = payload.get("arguments", {})
    if not args and "args" in payload:
        args = payload.get("args", {})
    if not tool:
        raise ValueError("stdin JSON requires 'tool'")
    if not isinstance(args, dict):
        raise ValueError("stdin JSON 'arguments' or 'args' must be an object")
    return tool, action, args


async def _dispatch(tool: str, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    # Redirect accidental stdout during import/tool execution; JSON contract owns stdout.
    stdout_guard = io.StringIO()
    with contextlib.redirect_stdout(stdout_guard):
        from src.runtime.bootstrap import bootstrap_runtime
        from mcp.server.fastmcp.server import Context

        runtime = bootstrap_runtime(include_mcp=True, cli_mode=True)
        orch = runtime["orchestrator"]

        # Create a dummy context if tool expects it
        class DummyContext(Context):
            def __init__(self):
                pass
            async def info(self, message: str): pass
            async def error(self, message: str): pass
            async def warning(self, message: str): pass
            async def report_progress(self, progress: float, total: float, message: Optional[str] = None): pass

        ctx = DummyContext()

        # Direct dispatch to orchestration layer to avoid FastMCP context issues
        from src.api.orchestration import ActionRouter
        router = ActionRouter(lambda: orch)

        try:
            if tool == "repository":
                result = await router.dispatch_repository(
                    action, args.get("repo_path"), args.get("repo_id"), args
                )
            elif tool == "filesystem":
                result = await router.dispatch_filesystem(
                    action, args.get("path"), args.get("repo_id"), args
                )
            elif tool == "codebase":
                result = await router.dispatch_codebase(
                    action, args.get("repo_id"), args.get("repo_path"), args
                )
            elif tool == "scaffolder":
                result = await router.dispatch_scaffolder(action, args)
            elif tool == "knowledge":
                # Knowledge tool uses repo_path as primary
                from src.modules.knowledgegraph.api.tools import _build_tools as register_k
                from mcp.server.fastmcp import FastMCP
                mcp = FastMCP("k")
                register_k(mcp, lambda: orch)
                # Hacky: extract tool function
                tools = await mcp.list_tools()
                k_tool = next(t for t in tools if t.name == "knowledge_graph")
                result = await k_tool.run(ctx=ctx, action=action, **args)
            elif tool == "idegraph":
                from src.modules.idegraph.api.tools import _build_tools as register_i
                from mcp.server.fastmcp import FastMCP
                mcp = FastMCP("i")
                register_i(mcp, lambda: orch)
                tools = await mcp.list_tools()
                i_tool = next(t for t in tools if t.name == "idegraph")
                result = await i_tool.run(ctx=ctx, action=action, **args)
            else:
                return _fail("UNKNOWN_TOOL", f"Unknown tool: {tool}", tool=tool)
        except Exception as e:
            return _fail("EXECUTION_ERROR", str(e), tool=tool, action=action)

    return result # ActionRouter already returns the _ok/_err shaped dict


def main() -> None:
    parser = argparse.ArgumentParser(prog="codecortex", add_help=False)
    parser.add_argument("tool", nargs="?")
    parser.add_argument("--action", "-a", required=False)
    parser.add_argument("--args", "-A", default="{}")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--stdin", action="store_true")
    ns, rest = parser.parse_known_args()

    if ns.stdin:
        try:
            tool, action, args_dict = _read_stdin_request()
            response = asyncio.run(_dispatch(tool, action, args_dict))
            _write_json(response)
            if not response.get("success"):
                sys.exit(1)
        except Exception as exc:
            _write_json(_fail("CLI_ERROR", str(exc)))
            sys.exit(1)
        return

    if not ns.tool or ns.tool in {"--help", "-h", "help"}:
        print(f"CodeCortex CLI v{VERSION}")
        print("Usage: python codecortex_cli.py <tool> --action <action> --args '<json>' --json")
        print("       python codecortex_cli.py --stdin --json")
        return

    try:
        args_dict = json.loads(ns.args)
        response = asyncio.run(_dispatch(ns.tool, ns.action, args_dict))
        _write_json(response)
        if not response.get("success"):
            sys.exit(1)
    except Exception as exc:
        _write_json(_fail("CLI_ERROR", str(exc)))
        sys.exit(1)


if __name__ == "__main__":
    main()
