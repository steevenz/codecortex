"""AI analysis CLI commands."""

from __future__ import annotations

import argparse
from typing import Any, Dict

from src.cli.common import ok, err


def cmd_ai_analyze(args_ns: argparse.Namespace) -> Dict:
    from src.core.cognitive.bridge import CortexBridge
    bridge = CortexBridge.instance()
    if not bridge.discover():
        return err("neocortex Server not available. Start neocortex Server or set neocortex_SERVER_URL.", "AI_NO_neocortex", 503)

    data = {"query": args_ns.query}
    if getattr(args_ns, "code", None):
        data["code"] = args_ns.code
    if getattr(args_ns, "repo", None):
        data["repo"] = args_ns.repo

    prompt = args_ns.prompt or f"Analyze this code query: {args_ns.query}"
    result = bridge.enrich(
        tool_name="ai_analyze",
        data=data,
        context={"format": args_ns.format},
        project_id=getattr(args_ns, "project_id", "default"),
    )
    if result:
        return ok("AI analysis complete", {"insight": result, "format": args_ns.format})
    return err("AI analysis failed — neocortex LLM may not be configured", "AI_FAILED", 502)


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("ai", help="Direct AI analysis via neocortex Server")
    p.add_argument("query", help="Query or code question to analyze")
    p.add_argument("--prompt", help="Custom prompt (default: auto-generated from query)")
    p.add_argument("--code", help="Optional code snippet to include")
    p.add_argument("--repo", help="Repository path for context")
    p.add_argument("--format", default="insight", help="insight|summary|remediation|explain|free")
    p.add_argument("--project-id", default="default", help="Project ID")
    p.add_argument("--neocortex-url", help="neocortex server URL override")
