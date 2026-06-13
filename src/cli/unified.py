"""
Unified CLI Parser - MCP Tools Compatible Interface.

All CLI commands now use structured action arguments to match MCP tools pattern.

Usage:
    codecortex repository --action init --args '{"repo_path":"..."}'
    codecortex filesystem --action read --args '{"path":"..."}'
    codecortex codebase --action search --args '{"query":"..."}'

:project: CodeCortex
:package: CLI.Unified
:author: Steeven Andrian (MCP Conversion)
:copyright: (c) 2026 CODDY Codework
:standard: MCP-CLI-v1.0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from src.cli.common import PROJECT_ROOT, run_async
from src.api.orchestration import ActionRouter


def _new_request_id() -> str:
    import uuid
    return str(uuid.uuid4())


def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def ok(message: str, data: Any) -> Dict:
    return {
        "success": True,
        "status_code": 200,
        "message": message,
        "data": data,
        "request_id": _new_request_id(),
        "meta": {"timestamp": _utcnow()}
    }


def err(message: str, code: str) -> Dict:
    return {
        "success": False,
        "status_code": 400,
        "message": message,
        "data": None,
        "error_code": code,
        "request_id": _new_request_id(),
        "meta": {"timestamp": _utcnow()}
    }


_UNIFIED_TOOLS = [
    "codecortex_repository",
    "codecortex_filesystem",
    "codecortex_codebase",
    "codecortex_scaffolder",
    "codecortex_neocortex",
    "codecortex_ai",
    "knowledge",
    "server",
    "cloud",
    "remote",
]


def _build_unified_parser() -> argparse.ArgumentParser:
    """Build unified CLI parser with action-based commands."""
    parser = argparse.ArgumentParser(
        prog="codecortex",
        description="CodeCortex MCP Server - Unified CLI Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s repository --action init --args '{"repo_path":"/path/to/repo"}'
  %(prog)s filesystem --action read --args '{"path":"/path/to/file.py"}'
  %(prog)s codebase --action search --args '{"query":"authentication"}'
        """
    )

    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version"
    )

    subparsers = parser.add_subparsers(dest="tool", help="Available tools")

    for tool in _UNIFIED_TOOLS:
        p = subparsers.add_parser(tool, help=f"{tool} MCP tool")
        p.add_argument(
            "--action", "-a",
            required=True,
            help="Action to perform (use 'list' to see available actions)"
        )
        p.add_argument(
            "--args", "-A",
            type=str,
            default="{}",
            help="JSON arguments for the action"
        )
        p.add_argument(
            "--repo-path",
            type=str,
            default=None,
            help="Repository path (alternative to repo_id)"
        )
        p.add_argument(
            "--repo-id",
            type=str,
            default=None,
            help="Repository ID"
        )
        p.add_argument(
            "--path",
            type=str,
            default=None,
            help="File/directory path"
        )
        p.add_argument(
            "--project-id",
            type=str,
            default="default",
            help="Project ID for context"
        )

    return parser


def _get_available_actions(tool: str) -> Dict[str, str]:
    """Return available actions for each tool."""
    actions = {
        "codecortex_repository": {
            "init": "Clone or initialize a repository",
            "inspect": "Fast health check",
            "analyze": "Deep AST analysis",
            "sync": "Incremental sync",
            "audit": "Security audit",
            "staleness": "Check staleness",
            "list": "List repositories",
            "compact": "Compact database",
            "cleanup": "Cleanup repository",
            "dump": "Export data",
            "restore": "Import data",
            "git": "Execute git commands",
            "svn": "Execute SVN commands",
            "server_start": "Start HTTP server",
            "server_stop": "Stop HTTP server",
            "server_status": "Check server status",
            "cloud_deploy": "Deploy to cloud",
            "cloud_logs": "View cloud logs",
            "cloud_status": "Check cloud status",
        },
        "codecortex_filesystem": {
            "read": "Read a file",
            "write": "Write a file",
            "delete": "Delete a file/directory",
            "copy": "Copy a file/directory",
            "move": "Move a file/directory",
            "mkdir": "Create directory",
            "list": "List directory contents",
            "search": "Search filesystem",
            "watch": "Watch for changes",
            "usage": "Disk usage analysis",
            "audit": "Security audit",
            "read_lines": "Read specific lines",
            "write_lines": "Write specific lines",
        },
        "codecortex_codebase": {
            "analyze": "Deep AST analysis",
            "search": "Multi-layer search",
            "audit": "Code standards audit",
            "graph_build": "Build code graph",
            "graph_query": "Query code graph",
            "graph_audit": "Graph audit",
            "graph_refactor": "Graph refactoring",
            "status": "Codebase metrics",
            "index": "Manage AST index",
            "test": "Run tests",
            "refactor": "Refactor code",
        },
        "codecortex_scaffolder": {
            "list_stacks": "List available stacks",
            "get_stack": "Get stack details",
            "validate_name": "Validate project name",
            "list_licenses": "List available licenses",
            "generate_content": "Generate file content",
            "generate_class": "Generate class file",
            "create_project": "Create new project",
        },
        "codecortex_neocortex": {
            "think_start": "Start thinking session",
            "analyze": "LLM analyze",
            "projects": "List projects",
            "project_add": "Add project",
            "project_status": "Project status",
            "code_analyze": "Code analysis",
            "code_search": "Code search",
        },
        "codecortex_ai": {
            "analyze": "AI code analysis",
        },
        "knowledge": {
            "query": "Query knowledge graph",
            "relationships": "Get relationships",
            "extract": "Extract knowledge",
            "list": "List knowledge items",
            "stats": "Knowledge statistics",
            "compact": "Compact knowledge graph",
        },
        "server": {
            "start": "Start server",
            "stop": "Stop server",
            "status": "Check server status",
        },
        "cloud": {
            "deploy": "Deploy to cloud",
            "logs": "View logs",
            "status": "Check cloud status",
        },
        "remote": {
            "path_map": "Register path mapping",
            "list": "List mappings",
            "unmap": "Remove mapping",
            "resolve": "Resolve path",
        },
    }
    return actions.get(tool, {})


def _execute_action(tool: str, action: str, args: Dict, **kwargs) -> Dict:
    """Execute an action through the shared ActionRouter or specific tool functions."""
    import asyncio

    if tool == "codecortex_neocortex":
        return _execute_neocortex_action(action, args)
    elif tool == "codecortex_ai":
        return _execute_ai_action(action, args)
    elif tool == "knowledge":
        return _execute_knowledge_action(action, args)
    elif tool == "server":
        return _execute_server_action(action, args)
    elif tool == "cloud":
        return _execute_cloud_action(action, args)
    elif tool == "remote":
        return _execute_remote_action(action, args)

    from src.api.orchestration import ActionRouter

    # Lazy import to avoid circular dependency
    from src.main import CortexOrchestrator
    def _factory():
        return CortexOrchestrator()

    router = ActionRouter(_factory)

    # Merge kwargs into args to match ActionRouter expectations
    merged_args = {**args}
    for k, v in kwargs.items():
        if v is not None and k not in merged_args:
            merged_args[k] = v

    # dispatch is async, so we use asyncio.run
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
    except RuntimeError:
        pass

    result = asyncio.run(router.dispatch(tool, action, merged_args))
    return result


def run_cli(tool, action, args):
    """Legacy runner, wrapping _execute_action."""
    return _execute_action(tool, action, args)


def _execute_neocortex_action(action: str, args: Dict) -> Dict:
    """Execute neocortex actions."""
    import httpx
    neocortex_url = os.getenv("neocortex_URL", "http://127.0.0.1:8001")

    neocortex_calls = {
        "think_start": "thinking_start",
        "analyze": "llm_analyze",
        "projects": "project_list",
        "project_add": "project_register",
        "project_status": "project_status",
        "code_analyze": "codecortex_analyze",
        "code_search": "codecortex_search",
    }

    method = neocortex_calls.get(action)
    if not method:
        return err(f"Unknown neocortex action: {action}", "UNKNOWN_ACTION")

    try:
        resp = httpx.post(
            f"{neocortex_url}/cognitive-api/v1/sync",
            json={"jsonrpc": "2.0", "id": "cli", "method": method, "params": args},
            timeout=120
        )
        return ok("neocortex call completed", resp.json())
    except Exception as e:
        return err(f"neocortex call failed: {e}", "neocortex_ERROR")


def _execute_ai_action(action: str, args: Dict) -> Dict:
    """Execute AI actions."""
    if action == "analyze":
        from src.core.cognitive.neo_enricher import audit_narrative
        result = audit_narrative(args, project_id=args.get("project_id", "default"))
        return ok("AI analysis completed", result) if result else err("AI unavailable", "AI_UNAVAILABLE")
    return err(f"Unknown AI action: {action}", "UNKNOWN_ACTION")


def _execute_knowledge_action(action: str, args: Dict) -> Dict:
    """Execute knowledge graph actions."""
    from src.main import CortexOrchestrator
    from src.modules.knowledgegraph.adapters.storage import KnowledgeStore

    orch = CortexOrchestrator()
    store = KnowledgeStore(orch.db)

    try:
        if action == "query":
            result = store.query(
                task=args.get("task"), knowledge_types=args.get("knowledge_types"),
                source_file=args.get("source_file"), min_importance=args.get("min_importance", 0.0),
                max_importance=args.get("max_importance"), min_confidence=args.get("min_confidence", 0.0),
                max_confidence=args.get("max_confidence"), repo_id=args.get("repo_id"),
                semantic=args.get("semantic", False), fts_query=args.get("fts_query"),
                regex=args.get("regex"), glob=args.get("glob"), pattern=args.get("pattern"),
                structured_query=args.get("structured_query"), search_fields=args.get("search_fields"),
                vector_search=args.get("vector_search"), limit=args.get("limit", 20)
            )
            return ok(f"Found {result['total']} relevant knowledge items", result)
        elif action == "relationships":
            rels_path = store.get_relationships()
            if args.get("focus"):
                from src.modules.knowledgegraph.core.graph import KnowledgeGraphBuilder
                all_chunks = []
                rows = orch.db.conn.execute("SELECT * FROM knowledge_chunks ORDER BY importance_score DESC LIMIT 200").fetchall()
                for r in rows:
                    all_chunks.append(KnowledgeStore._row_to_chunk(r))
                builder = KnowledgeGraphBuilder()
                result = builder.build_for_query(all_chunks, args.get("focus"))
                result["statistics"] = rels_path.get("statistics", {})
                return ok("Knowledge graph relationships", result)
            return ok("Knowledge graph relationships", rels_path)
        elif action == "status":
            return ok("Knowledge status", store.status(repo_id=args.get("repo_id")))
        return err(f"Unknown knowledge action: {action}", "UNKNOWN_ACTION")
    finally:
        orch.db.close()


def _execute_server_action(action: str, args: Dict) -> Dict:
    """Execute server actions."""
    import argparse
    from src.cli.server import cmd_server_start, cmd_server_stop, cmd_server_status

    # Mock Namespace from dict args
    ns = argparse.Namespace(**args)
    if action == "start":
        return cmd_server_start(ns)
    elif action == "stop":
        return cmd_server_stop(ns)
    elif action == "status":
        return cmd_server_status(ns)
    return err(f"Unknown server action: {action}", "UNKNOWN_ACTION")


def _execute_cloud_action(action: str, args: Dict) -> Dict:
    """Execute cloud actions."""
    return ok(f"Cloud action '{action}' not yet implemented", {})


def _execute_remote_action(action: str, args: Dict) -> Dict:
    """Execute remote actions."""
    return ok(f"Remote action '{action}' not yet implemented", {})


def main():
    """Main entry point for unified CLI."""
    parser = _build_unified_parser()
    args = parser.parse_args()

    if args.version:
        output = {"success": True, "data": {"version": Path(PROJECT_ROOT / '.version').read_text().strip() if (PROJECT_ROOT / '.version').exists() else '0.1.0'}}
        print(json.dumps(output))
        sys.exit(0)

    if not args.tool:
        parser.print_help()
        sys.exit(1)

    tool = args.tool
    action = args.action

    if action == "list-actions":
        actions = _get_available_actions(tool)
        output = {"success": True, "data": {"actions": actions}}
        print(json.dumps(output))
        sys.exit(0)

    try:
        parsed_args = json.loads(args.args)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in --args: {args.args}", file=sys.stderr)
        sys.exit(1)

    result = _execute_action(
        tool=tool,
        action=action,
        args=parsed_args,
        repo_path=args.repo_path,
        repo_id=args.repo_id,
        path=args.path,
        project_id=args.project_id,
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
