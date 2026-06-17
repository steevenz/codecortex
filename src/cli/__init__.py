"""
CodeCortex CLI — Orchestrator

Imports all module-level CLIs and wires them together.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from src.cli.common import (
    PROJECT_ROOT, output, ok, err, run_async,
    _remote_url, _send_remote, cmd_version,
)

from src.modules.coderepository.api.cli import (
    DOMAIN as REPO_DOMAIN, ALIASES as REPO_ALIASES,
    COMMANDS as REPO_COMMANDS, build_parser as build_repo_parser,
)

from src.modules.filesystem.api.cli import (
    DOMAIN as FS_DOMAIN, ALIASES as FS_ALIASES,
    FS_COMMANDS, build_parser as build_fs_parser,
)

from src.modules.codeanalysis.api.cli import (
    DOMAIN as CB_DOMAIN, ALIASES as CB_ALIASES,
    CB_COMMANDS, build_parser as build_cb_parser,
)

from src.modules.scaffolder.api.cli import (
    DOMAIN as SC_DOMAIN, ALIASES as SC_ALIASES,
    SC_COMMANDS, build_parser as build_sc_parser,
)

from src.modules.knowledgegraph.api.cli import (
    DOMAIN as KG_DOMAIN, ALIASES as KG_ALIASES,
    KG_COMMANDS, build_parser as build_kg_parser,
)

from src.modules.idegraph.api.cli import (
    DOMAIN as IG_DOMAIN, ALIASES as IG_ALIASES,
    IG_COMMANDS, build_parser as build_ig_parser,
)

from src.modules.codegraph.api.cli import (
    DOMAIN as CG_DOMAIN, ALIASES as CG_ALIASES,
    CG_COMMANDS, build_parser as build_cg_parser,
)

from src.modules.codeindex.api.cli import (
    DOMAIN as CI_DOMAIN, ALIASES as CI_ALIASES,
    CI_COMMANDS, build_parser as build_ci_parser,
)

from src.modules.coderefactor.api.cli import (
    DOMAIN as CR_DOMAIN, ALIASES as CR_ALIASES,
    REF_COMMANDS as CR_COMMANDS, build_parser as build_cr_parser,
)

from src.modules.codetester.api.cli import (
    DOMAIN as QA_DOMAIN, ALIASES as QA_ALIASES,
    QA_COMMANDS, build_parser as build_qa_parser,
)

from src.cli.server import (
    COMMANDS as SERVER_COMMANDS, build_parser as build_server_parser,
)

from src.cli.cloud import (
    COMMANDS as CLOUD_COMMANDS, build_parser as build_cloud_parser,
)

from src.cli.neocortex import (
    COMMANDS as neocortex_COMMANDS, build_parser as build_neocortex_parser,
)

from src.cli.ai import (
    cmd_ai_analyze, build_parser as build_ai_parser,
)

from src.cli.remote import (
    COMMANDS as REMOTE_COMMANDS, build_parser as build_remote_parser,
)

from src.cli.search import (
    SEARCH_COMMANDS, build_parser as build_search_parser,
)

from src.cli.indexing import (
    INDEX_COMMANDS, build_parser as build_indexing_parser,
)

from src.modules.codelogs.api.cli import (
    DOMAIN as LOG_DOMAIN, ALIASES as LOG_ALIASES,
    LOG_COMMANDS, build_parser as build_log_parser,
)

sys.path.insert(0, str(PROJECT_ROOT))


_DOMAIN_REGISTRY: Dict[str, Any] = {}


def _register(domain: str, aliases, commands, parser_builder):
    _DOMAIN_REGISTRY[domain] = {
        "domain": domain,
        "aliases": aliases,
        "commands": commands,
        "build_parser": parser_builder,
    }
    for alias in aliases:
        _DOMAIN_REGISTRY[alias] = _DOMAIN_REGISTRY[domain]


def _init_registry():
    _register("repository", ["repo"], REPO_COMMANDS, build_repo_parser)
    _register("filesystem", ["fs"], FS_COMMANDS, build_fs_parser)
    _register("codebase", ["cb"], CB_COMMANDS, build_cb_parser)
    _register("scaffolder", ["sc"], SC_COMMANDS, build_sc_parser)
    _register("knowledge", ["kg"], KG_COMMANDS, build_kg_parser)
    _register("idegraph", ["ig"], IG_COMMANDS, build_ig_parser)
    _register("codegraph", ["cg"], CG_COMMANDS, build_cg_parser)
    _register("codeindex", ["ci"], CI_COMMANDS, build_ci_parser)
    _register("coderefactor", ["refactor", "ref"], CR_COMMANDS, build_cr_parser)
    _register("codetester", ["qa", "tester"], QA_COMMANDS, build_qa_parser)
    _register("server", [], SERVER_COMMANDS, build_server_parser)
    _register("cloud", [], CLOUD_COMMANDS, build_cloud_parser)
    _register("neocortex", [], neocortex_COMMANDS, build_neocortex_parser)
    _register("remote", [], REMOTE_COMMANDS, build_remote_parser)
    _register("search", ["s", "find", "unified-search"], SEARCH_COMMANDS, build_search_parser)
    _register("indexing", ["idx", "index", "unified-index"], INDEX_COMMANDS, build_indexing_parser)
    _register("log", ["logs", "logging"], LOG_COMMANDS, build_log_parser)


def main() -> None:
    _init_registry()

    parser = argparse.ArgumentParser(
        prog="codecortex",
        description="CodeCortex — Universal Code Intelligence Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  codecortex repo init /path/to/project
  codecortex repo analyze /path/to/project
  codecortex fs read /path/to/file.py
  codecortex fs search /path --pattern "*.py" --content "class "
  codecortex cb search "database connection"
  codecortex cb graph /path build
  codecortex sc list-stacks
  codecortex sc make entity User --stack python
  codecortex sc create MyProject --stack python --dry-run
  codecortex kg extract /path/to/project
  codecortex kg query "how does auth work"
  codecortex ig search "payment"
  codecortex ig ingest
  codecortex ig harvest
  codecortex ci status --repo-id <uuid>
  codecortex ci index --path /path/to/project
  codecortex ci export --repo-id <uuid> --output symbols.json
  codecortex ref impact --repo-id <uuid> src/service.py::process_order
  codecortex ref rename --repo-id <uuid> src/utils.py::calc --new-name calculate_total
  codecortex ref rename --repo-id <uuid> src/utils.py::calc --new-name calculate_total --apply
  codecortex ref rename-file --repo-id <uuid> src/old.py --new-path src/new.py
  codecortex ref modularize --repo-id <uuid> src/monolith.py --target-domain src/domain/ --apply
  codecortex search "authentication module" --model codecortex-combo
  codecortex s "database connection" --type code --max-results 10
  codecortex search models
  codecortex find "class User" --model codecortex-codebase
  codecortex cg build /path/to/repo
  codecortex cg query callers MyService --repo-id <uuid>
  codecortex cg query visualize MyModule --repo-id <uuid> --viz-format mermaid
  codecortex cg search symbol authenticate --symbol-type function
  codecortex cg audit <repo_id> --types god_nodes,circular_deps --fix-suggestions
  codecortex cg refactor <repo_id> impact split_module LargeClass
  codecortex cg refactor <repo_id> apply split_module LargeClass --options '{"new_module_name":"CoreClass"}'
  codecortex cg refactor <repo_id> undo_list
  codecortex cloud init http://server:8001
  codecortex cloud push
  codecortex cloud pull
  codecortex cloud sync
  codecortex cloud status
  codecortex server status
  codecortex version
        """,
    )
    parser.add_argument("--no-pretty", action="store_true", help="Disable pretty-printed JSON output")
    parser.add_argument("--remote", help="Execute on remote server (URL or alias from $CODECORTEX_REMOTE)")
    parser.add_argument("--ai", action="store_true", help="Enrich output with AI insight via neocortex Server")
    parser.add_argument("--ai-format", default="insight", help="AI output format: insight|summary|remediation|explain")

    subparsers = parser.add_subparsers(dest="domain", required=True)

    # Build all registered domain parsers (unique builders only)
    for _, info in _DOMAIN_REGISTRY.items():
        builder = info.get("build_parser")
        if builder:
            builder(subparsers)
            # Mark as built so aliases don't re-add the same parser
            info["build_parser"] = None

    subparsers.add_parser("help", help="Show this help message")

    version_parser = subparsers.add_parser("version", help="Show version information")

    args_ns, _ = parser.parse_known_args()

    pretty = not getattr(args_ns, "no_pretty", False)
    domain = args_ns.domain

    # Remote execution intercept
    remote_url = _remote_url(args_ns)
    if remote_url and domain not in ("server", "remote", "cloud", "version", "help"):
        result = _send_remote(remote_url, domain, args_ns, _DOMAIN_REGISTRY)
        output(result, pretty=pretty)
        if not result.get("success", False):
            sys.exit(1)
        return

    result: Dict[str, Any] = {"success": False, "message": "Unknown command"}

    try:
        if domain == "help":
            parser.print_help()
            result = ok("Help displayed", {"usage": parser.format_usage()})

        elif domain == "version":
            result = cmd_version(args_ns)

        elif domain == "ai":
            result = cmd_ai_analyze(args_ns)

        else:
            info = _DOMAIN_REGISTRY.get(domain)
            if info:
                commands = info["commands"]
                action_key = f"{domain}_action" if domain in _DOMAIN_REGISTRY else None
                # Find action name: it's either <domain>_action or <alias>_action
                action = None
                for key in vars(args_ns):
                    if key.endswith("_action"):
                        action = getattr(args_ns, key)
                        break
                handler = commands.get(action) if action else None
                if handler:
                    result = handler(args_ns)
                else:
                    result = err(f"Unknown action: {action} for domain: {domain}", "CLI_ERROR")
            else:
                result = err(f"Unknown domain: {domain}", "CLI_ERROR")

    except Exception as e:
        if type(e).__name__ == "ApiError":
            result = err(str(e), getattr(e, "error_code", "CLI_ERROR"), getattr(e, "status_code", 400))
        else:
            result = err(f"Unexpected error: {e}", "CLI_UNEXPECTED", 500)

    # --ai flag enrichment
    if getattr(args_ns, "ai", False) and result.get("success") and result.get("data") is not None:
        try:
            from src.core.cognitive.bridge import CortexBridge
            bridge = CortexBridge.instance()
            if bridge.discover():
                insight = bridge.enrich(
                    tool_name=domain,
                    data=result.get("data"),
                    context={"action": action if 'action' in dir() else None},
                )
                if insight:
                    result["insight"] = insight
        except Exception:
            pass

    output(result, pretty=pretty)
    if not result.get("success", False):
        sys.exit(1)


if __name__ == "__main__":
    main()
