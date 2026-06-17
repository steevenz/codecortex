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
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-API-v1.0
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
    Register 5 consolidated MCP tools that dispatch to all domain services.

    Tools: repository, filesystem, codebase, scaffolder, update.

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

    def _coerce_args(args: Any) -> Dict:
        """Coerce args from JSON string to dict, or return original if already dict.

        Returns a dict — never None. Passes through if already a dict or None (→ {}).
        If args is a JSON string, attempts to parse it.

        Raises TypeError with clear message if args is an unsupported type.
        """
        import json
        if args is None:
            return {}
        if isinstance(args, dict):
            return args
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
                if not isinstance(parsed, dict):
                    raise TypeError(
                        f"args is a JSON string but parsed to {type(parsed).__name__}, "
                        f"expected JSON object (dict). "
                        f"Hint: pass args as {{'key': 'value'}}, not '...' wrapping the object."
                    )
                return parsed
            except json.JSONDecodeError as e:
                raise TypeError(
                    f"args is a JSON string but failed to parse: {e}. "
                    f"Hint: args should be a JSON object like {{\"content\": \"...\"}}, "
                    f"not a JSON string or array."
                )
        raise TypeError(
            f"args must be a dict or JSON string, got {type(args).__name__}. "
            f"If using an MCP client, ensure args is sent as a JSON object, not a string."
        )

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
        args: Optional[Any] = None,
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
        try:
            coerced_args = _coerce_args(args)
        except TypeError as e:
            from src.core import api_response as _api_resp, new_request_id as _new_rid
            return _api_resp(success=False, status_code=400, message=str(e),
                             data=None, request_id=_new_rid(), error_code="API_400")
        result = await _router().dispatch_repository(
            action, repo_path, repo_id, coerced_args,
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
        args: Optional[Any] = None,
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
        try:
            coerced_args = _coerce_args(args)
        except TypeError as e:
            from src.core import api_response as _api_resp, new_request_id as _new_rid
            return _api_resp(success=False, status_code=400, message=str(e),
                             data=None, request_id=_new_rid(), error_code="API_400")
        result = await _router().dispatch_filesystem(
            action, path, repo_id, coerced_args,
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
        args: Optional[Any] = None,
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
          - check_quality: Scan codebase for quality anti-patterns (TODO, console.log, empty catch, mock data).
            args: {target:".", checks:["zero_placeholder","dead_code","console_log"], files:"*.{py,js,ts,tsx,rs,go,java,kt,cpp,c,cs,rb,php}"}

        @param repo_id: Repository UUID (primary identification, preferred).
        @param repo_path: Path to repository on disk (alternative to repo_id).
        @param args: Action-specific parameters dict (see action list above).
        @return: Dict with success, data, meta.
        """
        t0 = time.monotonic()
        if hasattr(ctx, "info"):
            await ctx.info(f"codebase.{action} started")
        try:
            coerced_args = _coerce_args(args)
        except TypeError as e:
            from src.core import api_response as _api_resp, new_request_id as _new_rid
            return _api_resp(success=False, status_code=400, message=str(e),
                             data=None, request_id=_new_rid(), error_code="API_400")
        _long_actions = {"analyze", "audit", "test", "graph_build"}
        _is_long = action in _long_actions or (action == "graph" and coerced_args.get("sub_action") == "build")
        if _is_long and hasattr(ctx, "report_progress"):
            await ctx.report_progress(0, 5, f"Starting {action}...")
        result = await _router().dispatch_codebase(
            action, repo_id, repo_path, coerced_args,
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
        args: Optional[Any] = None,
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
        try:
            coerced_args = _coerce_args(args)
        except TypeError as e:
            from src.core import api_response as _api_resp, new_request_id as _new_rid
            return _api_resp(success=False, status_code=400, message=str(e),
                             data=None, request_id=_new_rid(), error_code="API_400")
        result = await _router().dispatch_scaffolder(
            action, coerced_args,
        )
        result.setdefault("meta", {})["duration_ms"] = int((time.monotonic() - t0) * 1000)
        return _inject_insight(result, "codecortex_scaffolder", action)

    # ══════════════════════════════════════════════════════════
    # TOOL 5: codecortex:update (synchronous — no await needed)
    # ══════════════════════════════════════════════════════════
    @mcp.tool(
        annotations=ToolAnnotations(
            title="CodeCortex Auto-Update",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    async def update(
        action: str,
    ) -> Dict[str, Any]:
        """
        Auto-update management — check, download, and apply CodeCortex updates.

        @param action: Operation to perform. One of:
          - check:   One-shot version check against GitHub Releases API.
                     Writes signal file at ~/.coddy/codecortex/update_signal.json for AI consumption.
          - status:  Show last check result and current update status.
          - signal:  Read the current AI-visible update signal file.
          - dismiss: Dismiss the update signal (mark as read).
          - download: Fetch the latest version via git pull (requires check first).
          - apply:   Merge fetched changes + sync dependencies (requires download first).

        @return: Dict with success, data, meta.
        """
        t0 = time.monotonic()
        result = _router().dispatch_update(action)
        result.setdefault("meta", {})["duration_ms"] = int((time.monotonic() - t0) * 1000)
        return _inject_insight(result, "codecortex_update", action)

    # ══════════════════════════════════════════════════════════
    # TOOL 6: codecortex:search — Unified Search (9Router-compatible)
    # ══════════════════════════════════════════════════════════
    @mcp.tool(
        annotations=ToolAnnotations(
            title="CodeCortex Unified Search",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def search(
        action: str = "search",
        query: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        max_results: Optional[int] = None,
        search_type: Optional[str] = None,
        repo_path: Optional[str] = None,
        repo_id: Optional[str] = None,
        file_pattern: Optional[str] = None,
        content_regex: Optional[str] = None,
        log_levels: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        auto_index: Optional[bool] = None,
        force_update: Optional[bool] = None,
        regraph: Optional[bool] = None,
        reindex: Optional[bool] = None,
        args: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Unified search across ALL CodeCortex providers (17Router-compatible).
        Orchestrates: codebase symbols, filesystem content, graph relationships,
        IDE memories, knowledge graph, log entries, TODO/FIXME tags, empty stubs,
        security audit, empty files, SVN status, and git blame — all in one call.

        @param action: Search operation. One of:
          - search: Execute unified search across provider(s).
          - models: List available search providers.
          - info: Get provider details.

        @param query: Search query string. For todo/stub/security/empty providers,
          filter by tag name, stub type, or security finding type.
        @param model: Provider ID. Use 'codecortex-combo' for all providers.
          Options: codecortex-codebase, codecortex-repowt, codecortex-filesystem,
                   codecortex-graph, codecortex-idegraph, codecortex-knowledge,
                   codecortex-crossproject, codecortex-codeindex, codecortex-agentart,
                   codecortex-codelogs, codecortex-todo, codecortex-stub,
                   codecortex-security, codecortex-empty, codecortex-svn,
                   codecortex-blame, codecortex-combo (all 17 providers)
        @param provider: Alias for 'model'. Either can be used.
        @param max_results: Maximum results (default 20, max 200).
        @param search_type: 'all' (default), 'code', 'file', 'memory', 'knowledge',
          'log', 'todo', 'stub', 'security', 'empty', 'svn', 'blame'.
        @param repo_path: Repository filesystem path to search within.
        @param repo_id: Repository UUID.
        @param file_pattern: File glob pattern(s) for filesystem or codelogs search.
        @param content_regex: Content regex for filesystem search.
        @param log_levels: Comma-separated log levels for codelogs search (ERROR,WARN,INFO,DEBUG).
        @param date_from: Start date (ISO format) for codelogs time-range filter.
        @param date_to: End date (ISO format) for codelogs time-range filter.
        @param args: Additional params dict.

        @return: 9Router-compatible search response with results, usage, metrics, errors.
        """
        t0 = time.monotonic()
        try:
            coerced_args = _coerce_args(args)
        except TypeError as e:
            from src.core import api_response as _api_resp, new_request_id as _new_rid
            return _api_resp(success=False, status_code=400, message=str(e),
                             data=None, request_id=_new_rid(), error_code="API_400")

        if action == "models":
            from src.services.unified_search import SEARCH_PROVIDERS
            return {
                "success": True,
                "status_code": 200,
                "message": "OK",
                "data": {
                    "object": "list",
                    "data": [
                        {"id": pid, "name": info["name"], "kind": info["kind"],
                         "description": info["description"], "owned_by": info["owned_by"]}
                        for pid, info in SEARCH_PROVIDERS.items()
                    ],
                },
                "meta": {"duration_ms": int((time.monotonic() - t0) * 1000)},
            }

        if action == "info":
            from src.services.unified_search import SEARCH_PROVIDERS
            pid = model or coerced_args.get("model") or coerced_args.get("provider") or "codecortex-combo"
            info = SEARCH_PROVIDERS.get(pid)
            if not info:
                return {
                    "success": False, "status_code": 404,
                    "message": f"Provider '{pid}' not found. Available: {list(SEARCH_PROVIDERS.keys())}",
                    "data": None, "meta": {},
                }
            return {
                "success": True, "status_code": 200, "message": "OK",
                "data": info,
                "meta": {"duration_ms": int((time.monotonic() - t0) * 1000)},
            }

        # Action: search
        from src.services.unified_search import SearchRequest, get_search_engine

        if not query and "query" not in coerced_args:
            from src.core import api_response as _api_resp, new_request_id as _new_rid
            return _api_resp(success=False, status_code=400,
                             message="query is required for search action",
                             data=None, request_id=_new_rid(), error_code="API_400")

        actual_query = query or coerced_args.get("query", "")
        actual_model = model or provider or coerced_args.get("model") or coerced_args.get("provider") or "codecortex-combo"

        req = SearchRequest(
            query=actual_query,
            model=actual_model,
            max_results=max_results or coerced_args.get("max_results", 20),
            search_type=search_type or coerced_args.get("search_type", "all"),
            repo_path=repo_path or coerced_args.get("repo_path"),
            repo_id=repo_id or coerced_args.get("repo_id"),
            symbol_type=coerced_args.get("symbol_type", "any"),
            language=coerced_args.get("language"),
            file_pattern=file_pattern or coerced_args.get("file_pattern", "*"),
            content_regex=content_regex or coerced_args.get("content_regex"),
            recursive=coerced_args.get("recursive", True),
            max_depth=coerced_args.get("max_depth", 20),
            search_mode=coerced_args.get("search_mode", "keyword"),
            project_name=coerced_args.get("project_name"),
            ide_name=coerced_args.get("ide_name"),
            knowledge_type=coerced_args.get("knowledge_type"),
            direction=coerced_args.get("direction", "both"),
            relation_type=coerced_args.get("relation_type"),
            graph_max_depth=coerced_args.get("graph_max_depth", 3),
            log_levels=log_levels or coerced_args.get("log_levels"),
            date_from=date_from or coerced_args.get("date_from"),
            date_to=date_to or coerced_args.get("date_to"),
            auto_index=auto_index if auto_index is not None else coerced_args.get("auto_index", True),
            force_update=force_update if force_update is not None else coerced_args.get("force_update", False),
            regraph=regraph if regraph is not None else coerced_args.get("regraph", False),
            reindex=reindex if reindex is not None else coerced_args.get("reindex", False),
        )

        engine = get_search_engine()
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            try:
                nest_asyncio.apply()
                response = loop.run_until_complete(engine.search(req))
            except Exception:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(lambda: asyncio.run(engine.search(req)))
                    response = future.result(timeout=60)
        else:
            response = loop.run_until_complete(engine.search(req))

        response_dict = response.to_dict()
        response_dict.setdefault("meta", {})["duration_ms"] = int((time.monotonic() - t0) * 1000)
        return response_dict

    # ══════════════════════════════════════════════════════════
    # TOOL 7: codecortex:indexing — Unified Indexing (sequential/periodic)
    # ══════════════════════════════════════════════════════════
    @mcp.tool(
        annotations=ToolAnnotations(
            title="CodeCortex Unified Indexing",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    async def indexing(
        action: str = "run",
        repo_path: Optional[str] = None,
        repo_id: Optional[str] = None,
        provider: Optional[str] = None,
        mode: Optional[str] = None,
        interval: Optional[int] = None,
        args: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Unified indexing across ALL CodeCortex providers (7 providers, sequential execution).
        Orchestrates: code index (AST), graph build, embeddings, knowledge graph,
        IDE memory harvest, log index, and security scan — in sequence.

        @param action: Indexing operation. One of:
          - run: Execute unified indexing across provider(s).
          - schedule: Start periodic indexing scheduler.
          - stop: Stop the periodic indexing scheduler.
          - status: Show scheduler status and last run result.
          - providers: List available index providers.

        @param repo_path: Repository filesystem path to index.
        @param repo_id: Repository UUID.
        @param provider: Provider ID. Use 'codecortex-full' for all 7 providers.
          Options: codecortex-codeindex, codecortex-graph, codecortex-embeddings,
                   codecortex-knowledge, codecortex-idegraph, codecortex-codelogs,
                   codecortex-security, codecortex-full (all 7 providers)
        @param mode: Indexing mode. 'full' (default) or 'incremental'.
        @param interval: Schedule interval in seconds (default: 3600, min: 60).
        @param args: Additional params dict.

        @return: Dict with success, data containing indexing results or scheduler status.
        """
        t0 = time.monotonic()
        try:
            coerced_args = _coerce_args(args)
        except TypeError as e:
            from src.core import api_response as _api_resp, new_request_id as _new_rid
            return _api_resp(success=False, status_code=400, message=str(e),
                             data=None, request_id=_new_rid(), error_code="API_400")

        from src.services.unified_indexing import IndexingRequest, get_indexing_engine
        engine = get_indexing_engine()

        try:
            # Action: providers
            if action == "providers":
                return {
                    "success": True, "status_code": 200, "message": "OK",
                    "data": engine.get_providers(),
                    "meta": {"duration_ms": int((time.monotonic() - t0) * 1000)},
                }

            # Action: status
            if action == "status":
                sched = engine.scheduler_status()
                last = engine.get_last_result()
                return {
                    "success": True, "status_code": 200, "message": "OK",
                    "data": {"scheduler": sched, "last_run": last},
                    "meta": {"duration_ms": int((time.monotonic() - t0) * 1000)},
                }

            # Action: schedule
            if action == "schedule":
                effective_path = repo_path or coerced_args.get("repo_path")
                if not effective_path:
                    from src.core import api_response as _api_resp, new_request_id as _new_rid
                    return _api_resp(success=False, status_code=400,
                                     message="repo_path required for schedule action",
                                     data=None, request_id=_new_rid(), error_code="API_400")
                effective_interval = interval or coerced_args.get("interval", 3600)
                result = engine.start_scheduler(effective_path, interval_seconds=effective_interval)
                result.setdefault("meta", {})["duration_ms"] = int((time.monotonic() - t0) * 1000)
                return result

            # Action: stop
            if action == "stop":
                result = engine.stop_scheduler()
                result.setdefault("meta", {})["duration_ms"] = int((time.monotonic() - t0) * 1000)
                return result

            # Default action: run
            effective_path = repo_path or coerced_args.get("repo_path")
            if not effective_path:
                from src.core import api_response as _api_resp, new_request_id as _new_rid
                return _api_resp(success=False, status_code=400,
                                 message="repo_path required for run action",
                                 data=None, request_id=_new_rid(), error_code="API_400")

            req = IndexingRequest(
                provider=provider or coerced_args.get("provider", "codecortex-full"),
                repo_path=effective_path,
                repo_id=repo_id or coerced_args.get("repo_id"),
                mode=mode or coerced_args.get("mode", "full"),
                detect_modular=coerced_args.get("detect_modular", True),
                build_dependency_graph=coerced_args.get("build_dependency_graph", True),
                embedding_model=coerced_args.get("embedding_model", "codebert"),
                file_pattern=coerced_args.get("file_pattern", "*"),
                severity=coerced_args.get("severity", "medium"),
                sequential=True,
            )

            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                try:
                    nest_asyncio.apply()
                    result_obj = loop.run_until_complete(engine.index(req))
                except Exception:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(lambda: asyncio.run(engine.index(req)))
                        result_obj = future.result(timeout=600)
            else:
                result_obj = loop.run_until_complete(engine.index(req))

            result = result_obj.to_dict()
            result.setdefault("meta", {})["duration_ms"] = int((time.monotonic() - t0) * 1000)
            return {
                "success": result["success"],
                "status_code": 200 if result["success"] else 500,
                "message": f"Indexing {'completed' if result['success'] else 'failed'} — "
                           f"{sum(1 for s in result['steps'] if s['status'] == 'completed')}/"
                           f"{len(result['steps'])} steps successful",
                "data": result,
                "meta": {"duration_ms": int((time.monotonic() - t0) * 1000)},
            }

        except Exception as e:
            return {
                "success": False, "status_code": 500,
                "message": f"Indexing failed: {str(e)}",
                "data": None,
                "meta": {"duration_ms": int((time.monotonic() - t0) * 1000)},
                "error_code": "INDEXING_ERROR",
            }

    # ══════════════════════════════════════════════════════════
    # TOOL 8: codecortex:loggraph — Log Visualization & Management (enhanced)
    # ══════════════════════════════════════════════════════════
    @mcp.tool(
        annotations=ToolAnnotations(
            title="CodeCortex Log Graph",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def loggraph(
        action: str = "summary",
        days: Optional[int] = 7,
        path: Optional[str] = None,
        file_pattern: Optional[str] = "*.log",
        granularity: Optional[str] = "hourly",
        max_files: Optional[int] = 50,
        search_paths: Optional[str] = None,
        detect_language: Optional[bool] = None,
        detect_os: Optional[bool] = None,
        detect_servers: Optional[bool] = None,
        detect_databases: Optional[bool] = None,
        max_results: Optional[int] = None,
        args: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Log visualization and statistics — error frequency, time trends, summary stats,
        anomaly detection, health assessment, file correlation, and log discovery.

        Uses systematic log path collection across languages, OS, servers, and databases
        per logging-standard.md and project-structure-standard.md.

        @param action: Visualization mode. One of:
          - summary:         Full summary with level distribution, error frequency, top messages.
          - error-frequency: Error frequency by level (ERROR, CRITICAL, WARN, INFO, DEBUG).
          - time-trend:      Trend over time (hourly or daily buckets).
          - scan:            List all log files in configured directories.
          - discover:        Discover log files via systematic path collection across
                             languages, OS, servers, databases. Returns file list + detection info.
          - anomalies:       Spike detection and anomaly analysis (z-score based).
          - files:           File-level metrics (size distribution, error correlation, growth).
          - health:          Log health assessment with health score (0-100).
          - info:            Show configured log directories and detection diagnostics.

        @param days: Time window in days (default: 7).
        @param path: Project root path to scan for log dirs.
        @param file_pattern: Log file glob pattern (default: *.log).
        @param granularity: Aggregation granularity for time-trend (hourly|daily).
        @param max_files: Max files to scan (default: 50).
        @param search_paths: Comma-separated additional paths to search for logs.
        @param detect_language: Enable language detection for log paths (default: true for discover).
        @param detect_os: Enable OS detection for log paths (default: true for discover).
        @param detect_servers: Enable server detection for log paths (default: true for discover).
        @param detect_databases: Enable database detection for log paths (default: true for discover).
        @param max_results: Max results for discover action (default: 200).
        @param args: Additional params dict.

        @return: Dict with success, data containing graph/scan results.
        """
        t0 = time.monotonic()
        try:
            coerced_args = _coerce_args(args)
        except TypeError as e:
            from src.core import api_response as _api_resp, new_request_id as _new_rid
            return _api_resp(success=False, status_code=400, message=str(e),
                             data=None, request_id=_new_rid(), error_code="API_400")

        project_root = path or coerced_args.get("path") or os.getcwd()
        effective_days = days or coerced_args.get("days", 7)
        effective_file_pat = file_pattern or coerced_args.get("file_pattern", "*.log")
        effective_max_files = max_files or coerced_args.get("max_files", 50)
        effective_granularity = granularity or coerced_args.get("granularity", "hourly")
        effective_search_paths = search_paths or coerced_args.get("search_paths")
        effective_max_results = max_results or coerced_args.get("max_results", 200)
        detect_lang = detect_language if detect_language is not None else coerced_args.get("detect_language", True)
        detect_os_bool = detect_os if detect_os is not None else coerced_args.get("detect_os", True)
        detect_serv = detect_servers if detect_servers is not None else coerced_args.get("detect_servers", True)
        detect_db = detect_databases if detect_databases is not None else coerced_args.get("detect_databases", True)
        detect_dev = coerced_args.get("detect_dev_tools", True)

        try:
            from src.modules.codelogs.services.loggraph_service import LogGraphService
            from src.modules.codelogs.services.log_service import LogService

            log_svc = LogService(project_root=project_root)
            graph_svc = LogGraphService(log_service=log_svc)

            # Action: scan
            if action == "scan":
                files = log_svc.scan_logs(search_paths=effective_search_paths)
                result = {
                    "total_files": len(files),
                    "project_root": project_root,
                    "files": files,
                }
                message = f"Found {len(files)} log files"

            # Action: discover
            elif action == "discover":
                data = graph_svc.discover(
                    custom_paths=effective_search_paths,
                    detect_language=detect_lang,
                    detect_os=detect_os_bool,
                    detect_servers=detect_serv,
                    detect_databases=detect_db,
                    detect_dev_tools=detect_dev,
                    max_results=effective_max_results,
                )
                result = data
                message = f"Discovered {data.get('total_files', 0)} log files"

            # Action: error-frequency
            elif action == "error-frequency":
                data = graph_svc.error_frequency(
                    days=effective_days, file_pattern=effective_file_pat,
                    max_files=effective_max_files, search_paths=effective_search_paths,
                )
                result = data
                message = f"Error frequency for last {effective_days} days"

            # Action: time-trend
            elif action == "time-trend":
                data = graph_svc.time_trend(
                    days=effective_days, granularity=effective_granularity,
                    file_pattern=effective_file_pat, max_files=effective_max_files,
                    search_paths=effective_search_paths,
                )
                result = data
                message = f"Time trend for last {effective_days} days"

            # Action: anomalies
            elif action == "anomalies":
                data = graph_svc.anomalies(
                    days=effective_days, file_pattern=effective_file_pat,
                    max_files=effective_max_files, search_paths=effective_search_paths,
                )
                result = data
                message = f"Anomaly detection for last {effective_days} days"

            # Action: files
            elif action == "files":
                data = graph_svc.files(
                    days=effective_days, max_files=effective_max_files,
                    search_paths=effective_search_paths,
                )
                result = data
                message = f"File-level metrics for last {effective_days} days"

            # Action: health
            elif action == "health":
                data = graph_svc.health(
                    days=effective_days, file_pattern=effective_file_pat,
                    max_files=effective_max_files, search_paths=effective_search_paths,
                )
                result = data
                message = f"Log health assessment: {data.get('status', 'unknown')}"

            # Action: info
            elif action == "info":
                roots = log_svc._get_log_roots(effective_search_paths)
                collector = log_svc.path_collector
                langs = collector._detect_languages() if log_svc._project_root else []
                servs = collector._detect_servers() if log_svc._project_root else []
                dbs = collector._detect_databases() if log_svc._project_root else []
                result = {
                    "project_root": log_svc._project_root,
                    "allowed_log_roots": list(log_svc.ALLOWED_LOG_ROOTS),
                    "active_roots": roots,
                    "detected_languages": langs,
                    "detected_servers": servs,
                    "detected_databases": dbs,
                    "operating_system": collector._detect_os(),
                }
                message = "Log system diagnostics"

            # Default: summary
            else:
                data = graph_svc.summary(
                    days=effective_days, file_pattern=effective_file_pat,
                    max_files=effective_max_files, search_paths=effective_search_paths,
                )
                result = data
                message = f"Log summary for last {effective_days} days"

            return {
                "success": True,
                "status_code": 200,
                "message": message,
                "data": result,
                "meta": {"duration_ms": int((time.monotonic() - t0) * 1000)},
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": 500,
                "message": str(e),
                "data": None,
                "meta": {"duration_ms": int((time.monotonic() - t0) * 1000)},
                "error_code": "CODELOGS_GRAPH_ERROR",
            }
