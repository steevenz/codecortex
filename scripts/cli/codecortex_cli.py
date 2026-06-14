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


async def _dispatch(tool: str, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    # Redirect accidental stdout during import/tool execution; JSON contract owns stdout.
    stdout_guard = io.StringIO()
    with contextlib.redirect_stdout(stdout_guard):
        from src.runtime.bootstrap import bootstrap_runtime

        runtime = bootstrap_runtime(include_mcp=True, cli_mode=True)
        mcp_instance = runtime["mcp_instance"]

        # Find tool handler in the FastMCP instance
        handler = None
        target_names = {tool, f"codecortex_{tool}", f"codecortex:{tool}"}
        for t in mcp_instance._tools:
            if t.name in target_names:
                handler = t
                break

        if not handler:
            return _fail("UNKNOWN_TOOL", f"Unknown tool: {tool}", tool=tool)

        # Call tool with action/args matching MCP signature
        try:
            # CodeCortex tools usually expect (ctx, action, repo_path, repo_id, args)
            # but FastMCP .run() handles mapping arguments.
            result = await handler.run(action=action, args=args)
        except Exception as e:
            return _fail("EXECUTION_ERROR", str(e), tool=tool, action=action)

    return _ok(tool, action, result)


def main() -> None:
    parser = argparse.ArgumentParser(prog="codecortex", add_help=False)
    parser.add_argument("tool", nargs="?")
    parser.add_argument("--action", "-a", required=False)
    parser.add_argument("--args", "-A", default="{}")
    parser.add_argument("--json", action="store_true")
    ns, rest = parser.parse_known_args()

    if not ns.tool or ns.tool in {"--help", "-h", "help"}:
        print(f"CodeCortex CLI v{VERSION}")
        print("Usage: python codecortex_cli.py <tool> --action <action> --args '<json>' --json")
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
