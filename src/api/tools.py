"""
CodeCortex MCP API — 4 top-level unified tools.

repository  : repo lifecycle (init, inspect, analyze, sync, audit, staleness,
              list, compact, cleanup, dump, restore, git, svn)
filesystem  : file operations (read, write, delete, copy, move, mkdir,
              list, search, watch, usage, audit, read_lines, write_lines)
codebase    : code intelligence (analyze, search, audit, graph, status,
              index, test, refactor)
scaffolder  : project scaffolding (list_stacks, get_stack, validate_name,
              list_licenses, generate_content, generate_class, create_project).

:project: CodeCortex
:package: Api.Tools
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-API-v1.0
"""
from __future__ import annotations
import time
from typing import Any, Callable, Dict, Optional
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Context
from mcp.types import ToolAnnotations

from src.api.orchestration import ActionRouter

def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """
    Register 4 consolidated MCP tools that dispatch to all 38 domain tools.

    Each tool uses action + args pattern:
      - action: string (which operation to perform)
      - args:   dict (operation-specific parameters, see docstring)
    """
    router = None

    def _router() -> ActionRouter:
        nonlocal router
        if router is None:
            router = ActionRouter(orchestrator_factory)
        return router

    # ══════════════════════════════════════════════════════════
    # TOOL 1: codecortex:repository
    # ══════════════════════════════════════════════════════════
    def _inject_insight(response: Dict, tool_name: str, action: str) -> Dict:
        """Inject insight into unified tool responses if not already present."""
        if response.get("success") and "insight" not in response and response.get("data") is not None:
            from src.core.insight import generate_insight
            try:
                ins = generate_insight(tool_name, response["data"], {"action": action})
                response["insight"] = ins.to_dict()
            except Exception:
                pass
        return response

    @mcp.tool(
        annotations=ToolAnnotations(
            title="CodeCortex Repository",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    async def repository(
        ctx: Context,
        action: str,
        repo_path: Optional[str] = None,
        repo_id: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Repository lifecycle management — init, inspect, analyze, sync, audit, and more.

        @param action: Operation to perform. One of:
          - init: Clone or initialize a repository.
            args: {vcs_type:"git", remote_url:?, force:?, scope:{include,exclude}, run_audit:true, audit_categories:?, parallel:true, max_workers:4}
          - inspect: Fast health check, zero parsing. Returns file counts, git status, metadata.
            args: {include_git_diagnostics:true, include_index_metadata:true, include_file_stats:true, timeout:30}
          - analyze: Deep analysis — AST parsing, graph building, VCS integration.
            args: {force:?, incremental:true, parallel:true, build_graph:true, extract_symbols:true, store_embeddings:?, embedding_model:"codebert", timeout:300, dry_run:?}
          - sync: Incremental sync — detect changed files, re-index.
            args: {mode:"auto", scope:{include,exclude}, reindex_updated:true, remove_deleted:true, dry_run:?}
          - audit: Multi-layer security audit — secrets, PII, misconfig, vulnerabilities.
            args: {secrets:true, scope:{exclude}, include_git_history:true}
          - staleness: Check if index is stale vs remote VCS.
            args: {compare_remote:true, fetch_remote:?, include_local_changes:true, timeout:30}
          - list: List all registered repositories.
            args: {filter_status:"all", limit:50, offset:0, order_by:"last_analyzed", order_dir:"desc"}
          - compact: Compact database, VACUUM, export snapshot.
            args: {output_format:"yaml", output_path:?, compact_db:true, dry_run:?}
          - cleanup: Permanently delete ALL data for a repo.
            args: {delete_snapshot:true, dry_run:?, force:?}
          - dump: Export all data to portable files.
            args: {output_dir:?, format:"yaml", include_findings:true, dry_run:?}
          - restore: Import data from dump file or snapshot directory.
            args: {source:, repo_path:?, overwrite:?, verify_checksum:true, dry_run:?}
          - git: Execute arbitrary git commands. args: {subcommand:, args:?, flags:?, dry_run:?, timeout:300}
          - svn: Execute arbitrary SVN commands. args: {target:, subcommand:, args:?, flags:?, dry_run:?, timeout:300}

        @param repo_path: Path to repository on disk (required for most actions).
        @param repo_id: Repository UUID alternative to repo_path.
        @param args: Action-specific parameters dict (see action list above).
        @return: Dict with success, data, meta.
        """
        t0 = time.monotonic()
        if hasattr(ctx, "info"):
            await ctx.info(f"repository.{action} started")
        if action in ("analyze", "sync", "audit") and hasattr(ctx, "report_progress"):
            await ctx.report_progress(0, 6, "Starting...")
        result = await _router().dispatch_repository(
            action, repo_path, repo_id, args or {},
        )
        if action in ("analyze", "sync", "audit") and hasattr(ctx, "report_progress"):
            await ctx.report_progress(6, 6, "Complete")
        if hasattr(ctx, "info"):
            await ctx.info(f"repository.{action} finished")
        result.setdefault("meta", {})["duration_ms"] = int((time.monotonic() - t0) * 1000)
        return _inject_insight(result, "codecortex_repository", action)

    # ══════════════════════════════════════════════════════════
    # TOOL 2: codecortex:filesystem
    # ══════════════════════════════════════════════════════════
    @mcp.tool(
        annotations=ToolAnnotations(
            title="CodeCortex Filesystem",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    async def filesystem(
        action: str,
        path: Optional[str] = None,
        repo_id: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Filesystem operations — read, write, delete, search, watch, disk usage, and audit.
        Line operations: read_lines, write_lines for targeted line editing.
        Hybrid: read/write accept optional 'lines' parameter for line-specific operations.

        @param action: Operation to perform. One of:
          - read: Read a file. args: {encoding:"utf-8", lines:{start_line:1, end_line:?}}
          - write: Write/create a file. args: {content:, encoding:"utf-8", atomic:true, backup:?, create_parents:true, overwrite:?}
          - delete: Delete file or directory. args: {recursive:?, dry_run:?}
          - copy: Copy file or directory. args: {dest:, overwrite:?, create_dest_parents:true, dry_run:?}
          - move: Move/rename file or directory. args: {dest:, overwrite:?, create_dest_parents:true, dry_run:?}
          - mkdir: Create directory. args: {create_parents:true, dry_run:?}
          - list (or ls): List directory contents. args: {recursive:?, max_depth:?, include_hidden:?, file_pattern:"*"}
          - search: Search filesystem — filename regex + content regex. args: {root_path:?, file_pattern:"*", file_regex:?, content_regex:?, recursive:true, max_depth:?, max_results:100, exclude_patterns:?, replace_text:?, dry_run:true}
          - watch: Poll-based filesystem change detection. args: {target:".", recursive:true, events:?, poll_interval:1, max_events:100}
          - usage: Disk usage analysis. args: {target:".", recursive:true, depth:10, unit:"auto", aggregate_by:"file", max_items:100}
          - audit: File permissions and security audit. args: {target:".", recursive:true, severity:?, check_permissions:true, max_file_size_mb:100, limit:200}
          - read_lines: Read specific lines from a file. args: {start_line:1, end_line:?, encoding:"utf-8"}
          - write_lines: Write/edit specific lines in a file. args: {start_line:1, end_line:?, content:[], encoding:"utf-8", dry_run:true}

        @param path: Target file or directory path (required for CRUD operations).
        @param repo_id: Repository context for relative path resolution.
        @param args: Action-specific parameters dict (see action list above).
        @return: Dict with success, data, meta.
        """
        t0 = time.monotonic()
        result = await _router().dispatch_filesystem(
            action, path, repo_id, args or {},
        )
        result.setdefault("meta", {})["duration_ms"] = int((time.monotonic() - t0) * 1000)
        return _inject_insight(result, "codecortex_filesystem", action)

    # ══════════════════════════════════════════════════════════
    # TOOL 3: codecortex:codebase
    # ══════════════════════════════════════════════════════════
    @mcp.tool(
        annotations=ToolAnnotations(
            title="CodeCortex Codebase",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    async def codebase(
        ctx: Context,
        action: str,
        repo_id: Optional[str] = None,
        repo_path: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Code intelligence — search, graph analysis, audit, indexing, testing, refactoring.

        @param action: Operation to perform. One of:
          - analyze: Deep AST analysis of a single target (file/symbol/dir).
            args: {target:, mode:"auto", max_depth:3, focus:?, follow_depth:1, include_docstring:true, include_comments:?, page_size:100}
          - search: Unified multi-layer search (FTS + optional semantic + graph).
            args: {query:, search_type:"text", symbol_type:"any", semantic:?, graph_enrichment:?, limit:50, file_pattern:"*"}
          - audit: Standards compliance audit (coding-standard.md checks).
            args: {target:".", scan_categories:?, severity_threshold:"medium", entropy_threshold:4.5, max_file_size_kb:1024, files:?, use_ast:true, use_aiignore:true, since:?}
          - graph: All graph operations via sub_action.
            sub_action "build": args: {detect_modular:true, build_dependency_graph:true, scan_hmvc_p:true, max_depth:5, use_cache:true}
            sub_action "query": args: {target:, query_type:"callers"|"callees"|"path"|"ancestors"|"descendants"|"trace_flow"|"trace_path", max_depth:3, end_node:?, direction:"both", limit:20}
            sub_action "audit": args: {audit_types:?, degree_threshold:10, include_summary:?, limit:50}
            sub_action "relationships": args: {target_node:, relation_type:?, direction:"both", depth:1, include_community:?, min_confidence:"INFERRED", limit:100}
          - status: Codebase metrics snapshot — files, LOC, symbols, graph stats.
            args: {include_metrics:true, include_vcs:true, include_symbols:true, language:?}
          - index: Manage AST index via sub_action.
            sub_action "build"|"rebuild": Build or rebuild the AST index.
            sub_action "remove": Remove all index data for a repo.
            sub_action "status": Show index statistics (file count, symbol count).
            args: {files:?}
          - test: Run, discover, diagnose, or generate tests via sub_action.
            sub_action "run": Execute tests. sub_action "discover": Find tests. sub_action "diagnose": Debug failures. sub_action "generate": Generate missing tests.
            args: {target_path:?, test_framework:"auto", test_filter:?, test_names:?, categories:?, coverage_format:"summary", target_symbol:?, max_duration:300, async_mode:?}
          - refactor: Safe semantic refactoring via sub_action.
            sub_action "impact": Analyze change impact. sub_action "rename": Rename symbol. sub_action "move": Move code element. sub_action "extract": Extract function. sub_action "inline": Inline function. sub_action "signature": Change signature.
            args: {target_symbol:, changes:{new_name, source_file, target_file, ...}, dry_run:true}

        @param repo_id: Repository UUID (primary identification, preferred).
        @param repo_path: Path to repository on disk (alternative to repo_id).
        @param args: Action-specific parameters dict (see action list above).
        @return: Dict with success, data, meta.
        """
        t0 = time.monotonic()
        if hasattr(ctx, "info"):
            await ctx.info(f"codebase.{action} started")
        _long_actions = {"analyze", "audit", "test", "graph_build"}
        _is_long = action in _long_actions or (action == "graph" and (args or {}).get("sub_action") == "build")
        if _is_long and hasattr(ctx, "report_progress"):
            await ctx.report_progress(0, 5, f"Starting {action}...")
        result = await _router().dispatch_codebase(
            action, repo_id, repo_path, args or {},
        )
        if _is_long and hasattr(ctx, "report_progress"):
            await ctx.report_progress(5, 5, f"{action} complete")
        if hasattr(ctx, "info"):
            await ctx.info(f"codebase.{action} finished")
        result.setdefault("meta", {})["duration_ms"] = int((time.monotonic() - t0) * 1000)
        return _inject_insight(result, "codecortex_codebase", action)

    # ══════════════════════════════════════════════════════════
    # TOOL 4: codecortex:scaffolder
    # ══════════════════════════════════════════════════════════
    @mcp.tool(
        annotations=ToolAnnotations(
            title="CodeCortex Scaffolder",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def scaffolder(
        action: str,
        args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Project scaffolding — inspect stacks, validate names, generate files, and scaffold projects.

        @param action: Operation to perform. One of:
          - list_stacks: List all available technology stacks.
            args: (none)
          - get_stack: Get detailed info for one stack.
            args: {stack_name:}
          - validate_name: Validate/normalize a project name.
            args: {name:}
          - list_licenses: List all available license types.
            args: (none)
          - generate_content: Preview a content file without writing.
            args: {file_type:, project_category:"standard", project_name:, author:, email:, license_name:}
            file_type: gitignore, env, pyproject, readme, requirements, dockerfile,
                       docker_compose, setup_sh, setup_bat, setup_ps1, logger_py,
                       author_file, ai_ignore
          - generate_class: Generate a class file per Decision Matrix (28 types).
            args: {type:, name:, stack:"python", module:, project_name:, author:, target_path:, overwrite:false}
            type: interface, abstract, model, repository, controller, service,
                  value_object, dto, event, listener, job, middleware, factory,
                  seeder, migration, enum, trait, helper, validator, mapper, ...
          - create_project: Full project scaffolding.
            args: {name:, stack:"python", project_type:"standard", target_path:, author:,
                   email:, version:"0.1.0", license:"MIT", overwrite:false,
                   include_ai:false, include_trainer:false, dry_run:true}

        @return: Dict with success, data.
        """
        t0 = time.monotonic()
        result = await _router().dispatch_scaffolder(
            action, args or {},
        )
        result.setdefault("meta", {})["duration_ms"] = int((time.monotonic() - t0) * 1000)
        return _inject_insight(result, "codecortex_scaffolder", action)
