"""
Legacy CLI Compatibility Layer.

Maps old CLI subcommands to new unified tool/action format.
This allows existing scripts and workflows to continue working.

:project: CodeCortex
:package: CLI.Compatibility
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: MCP-CLI-v1.0
"""

import argparse
import sys
from typing import Dict, Any

LEGACY_COMMANDS = {
    # repository subcommands
    "repository init": {"tool": "codecortex_repository", "action": "init"},
    "repository inspect": {"tool": "codecortex_repository", "action": "inspect"},
    "repository analyze": {"tool": "codecortex_repository", "action": "analyze"},
    "repository sync": {"tool": "codecortex_repository", "action": "sync"},
    "repository audit": {"tool": "codecortex_repository", "action": "audit"},
    "repository staleness": {"tool": "codecortex_repository", "action": "staleness"},
    "repository list": {"tool": "codecortex_repository", "action": "list"},
    "repository compact": {"tool": "codecortex_repository", "action": "compact"},
    "repository cleanup": {"tool": "codecortex_repository", "action": "cleanup"},
    "repository dump": {"tool": "codecortex_repository", "action": "dump"},
    "repository restore": {"tool": "codecortex_repository", "action": "restore"},
    "repository git": {"tool": "codecortex_repository", "action": "git"},
    "repository svn": {"tool": "codecortex_repository", "action": "svn"},

    # filesystem subcommands
    "filesystem read": {"tool": "codecortex_filesystem", "action": "read"},
    "filesystem write": {"tool": "codecortex_filesystem", "action": "write"},
    "filesystem delete": {"tool": "codecortex_filesystem", "action": "delete"},
    "filesystem copy": {"tool": "codecortex_filesystem", "action": "copy"},
    "filesystem move": {"tool": "codecortex_filesystem", "action": "move"},
    "filesystem mkdir": {"tool": "codecortex_filesystem", "action": "mkdir"},
    "filesystem list": {"tool": "codecortex_filesystem", "action": "list"},
    "filesystem search": {"tool": "codecortex_filesystem", "action": "search"},
    "filesystem watch": {"tool": "codecortex_filesystem", "action": "watch"},
    "filesystem usage": {"tool": "codecortex_filesystem", "action": "usage"},
    "filesystem audit": {"tool": "codecortex_filesystem", "action": "audit"},
    "filesystem read_lines": {"tool": "codecortex_filesystem", "action": "read_lines"},
    "filesystem write_lines": {"tool": "codecortex_filesystem", "action": "write_lines"},

    # codebase subcommands
    "codebase analyze": {"tool": "codecortex_codebase", "action": "analyze"},
    "codebase search": {"tool": "codecortex_codebase", "action": "search"},
    "codebase audit": {"tool": "codecortex_codebase", "action": "audit"},
    "codebase graph": {"tool": "codecortex_codebase", "action": "graph_build"},
    "codebase status": {"tool": "codecortex_codebase", "action": "status"},
    "codebase index": {"tool": "codecortex_codebase", "action": "index"},
    "codebase test": {"tool": "codecortex_codebase", "action": "test"},
    "codebase refactor": {"tool": "codecortex_codebase", "action": "refactor"},

    # scaffolder subcommands
    "scaffolder list_stacks": {"tool": "codecortex_scaffolder", "action": "list_stacks"},
    "scaffolder get_stack": {"tool": "codecortex_scaffolder", "action": "get_stack"},
    "scaffolder validate_name": {"tool": "codecortex_scaffolder", "action": "validate_name"},
    "scaffolder list_licenses": {"tool": "codecortex_scaffolder", "action": "list_licenses"},
    "scaffolder generate_content": {"tool": "codecortex_scaffolder", "action": "generate_content"},
    "scaffolder generate_class": {"tool": "codecortex_scaffolder", "action": "generate_class"},
    "scaffolder create_project": {"tool": "codecortex_scaffolder", "action": "create_project"},

    # neocortex subcommands (kebab-case to snake_case)
    "neocortex think-start": {"tool": "codecortex_neocortex", "action": "think_start"},
    "neocortex analyze": {"tool": "codecortex_neocortex", "action": "analyze"},
    "neocortex projects": {"tool": "codecortex_neocortex", "action": "projects"},
    "neocortex project-add": {"tool": "codecortex_neocortex", "action": "project_add"},
    "neocortex project-status": {"tool": "codecortex_neocortex", "action": "project_status"},
    "neocortex code-analyze": {"tool": "codecortex_neocortex", "action": "code_analyze"},
    "neocortex code-search": {"tool": "codecortex_neocortex", "action": "code_search"},

    # server subcommands
    "server start": {"tool": "server", "action": "start"},
    "server stop": {"tool": "server", "action": "stop"},
    "server status": {"tool": "server", "action": "status"},

    # cloud subcommands
    "cloud deploy": {"tool": "cloud", "action": "deploy"},
    "cloud logs": {"tool": "cloud", "action": "logs"},
    "cloud status": {"tool": "cloud", "action": "status"},

    # remote subcommands
    "remote path-map": {"tool": "remote", "action": "path_map"},
    "remote list": {"tool": "remote", "action": "list"},
    "remote unmap": {"tool": "remote", "action": "unmap"},
    "remote resolve": {"tool": "remote", "action": "resolve"},

    # ai subcommands
    "ai analyze": {"tool": "codecortex_ai", "action": "analyze"},
}


def detect_legacy_command(args: list) -> Dict[str, Any]:
    """Detect if command is legacy format and return conversion mapping."""
    if len(args) < 2:
        return {}

    domain = args[0]
    subcommand = args[1] if len(args) > 1 else ""
    key = f"{domain} {subcommand}"

    return LEGACY_COMMANDS.get(key, {})


def convert_legacy_to_unified(args: list) -> tuple:
    """Convert legacy CLI args to unified format."""
    mapping = detect_legacy_command(args)
    if not mapping:
        return args, False

    tool = mapping["tool"]
    action = mapping["action"]

    new_args = [tool, "--action", action]
    if len(args) > 2:
        new_args.extend(args[2:])

    return new_args, True
