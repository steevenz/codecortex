from __future__ import annotations
import json
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from src.core import api_response, new_request_id
from src.domain.codegraph.core.security import validate_url, validate_graph_path, sanitize_label

# ---------------------------------------------------------------------------
# Relation type aliases: user-friendly → internal service types
# ---------------------------------------------------------------------------
_RELATION_ALIASES: Dict[str, str] = {
    "callers":     "find_callers",
    "callees":     "find_callees",
    "imports":     "find_importers",
    "modifies":    "who_modifies",
    "hierarchy":   "class_hierarchy",
    "overrides":   "overrides",
    "dead_code":   "dead_code",
    "chain":       "call_chain",
    "deps":        "module_deps",
    "complexity":  "find_complexity",
    "all_callers": "find_all_callers",
    "all_callees": "find_all_callees",
}


def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """
    Register consolidated codegraph tools to the FastMCP instance.
    Tool count: 20 → 7 (namespace-prefixed).

    @param mcp: FastMCP server instance
    @param orchestrator_factory: Factory to create orchestrator instances
    """

    # -------------------------------------------------------------------------
    # 1. graph_find_symbols — Replaces: find_by_function_name, find_by_class_name,
    #                                   find_by_variable_name, search_symbols (main)
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def graph_find_symbols(
        search_term: str,
        symbol_type: str = "any",
        repo_path: Optional[str] = None,
        fuzzy_search: bool = False,
        edit_distance: int = 2,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Find symbols (functions, classes, variables) by name across the codebase.

        Use this to locate where a specific function, class, or variable is defined.
        Supports exact and fuzzy/approximate name matching.

        @param search_term: Symbol name to search for (e.g. "UserService", "process_payment")
        @param symbol_type: Filter by type — "function" | "class" | "variable" | "any" (default: "any")
        @param repo_path: Optional path to limit search to a specific repository root
        @param fuzzy_search: Enable approximate name matching (tolerates typos), default False
        @param edit_distance: Max edit distance for fuzzy search (default 2)
        @param limit: Max results to return (default 20)
        @return: List of matching symbols with file paths and line numbers
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            if symbol_type in ("function", "any"):
                fn_results = await orchestrator.graph_service.find_by_function_name(
                    search_term, repo_path, fuzzy_search, edit_distance, limit
                )
            else:
                fn_results = []

            if symbol_type in ("class", "any"):
                cls_results = await orchestrator.graph_service.find_by_class_name(
                    search_term, repo_path, fuzzy_search, edit_distance, limit
                )
            else:
                cls_results = []

            if symbol_type in ("variable", "any"):
                var_results = await orchestrator.graph_service.find_by_variable_name(
                    search_term, repo_path, limit
                )
            else:
                var_results = []

            combined = {
                "functions": fn_results,
                "classes":   cls_results,
                "variables": var_results,
                "total":     len(fn_results) + len(cls_results) + len(var_results),
            }
            return api_response(
                success=True, status_code=200,
                message=f"Found {combined['total']} symbol(s) matching '{search_term}'",
                data=combined, request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Error finding symbols: {str(e)}",
                data=None, request_id=request_id, error_code="GRPH_001",
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 2. graph_query — Replaces: find_callers, find_callees, who_imports_module,
    #                            find_class_hierarchy, analyze_code_relationships
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def graph_query(
        query_type: str,
        target: str,
        context: Optional[str] = None,
        repo_path: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Query code relationships in the graph by specifying a relation type and target symbol.

        Use this to trace how code connects — who calls a function, what a class inherits from,
        which files import a module, or how execution flows through the codebase.

        @param query_type: Relationship to query. Options:
            - "callers"     → who calls target function
            - "callees"     → what target function calls
            - "all_callers" → deep recursive callers
            - "all_callees" → deep recursive callees
            - "imports"     → files that import the target module
            - "modifies"    → what modifies the target variable/state
            - "hierarchy"   → parent and child classes of target
            - "overrides"   → methods that override target
            - "chain"       → call chain from target
            - "deps"        → module dependencies of target
            - "complexity"  → cyclomatic complexity of target
            - "dead_code"   → unused functions in scope of target
        @param target: Symbol name or module name to analyze (e.g. "process_payment", "utils.auth")
        @param context: Optional file path to disambiguate if symbol exists in multiple files
        @param repo_path: Optional path to scope query to a specific repository
        @param limit: Max results (default 20)
        @return: Relationship analysis result for the given target
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            # Resolve user-friendly aliases to internal service types
            resolved_type = _RELATION_ALIASES.get(query_type, query_type)

            results = await orchestrator.graph_service.analyze_code_relationships(
                resolved_type, target, context, repo_path
            )
            return api_response(
                success=True, status_code=200,
                message=f"Relationship query '{query_type}' on '{target}' completed",
                data=results, request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Error in graph_query ({query_type}): {str(e)}",
                data=None, request_id=request_id, error_code="GRPH_002",
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 3. graph_find_related — Replaces: find_related_code
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def graph_find_related(
        user_query: str,
        repo_path: Optional[str] = None,
        limit: int = 15,
    ) -> Dict[str, Any]:
        """
        Semantic cross-symbol search: find functions, classes, and variables related to a natural-language query.

        Use this when you don't know the exact symbol name but want to find code by concept or intent.
        Example: "payment retry logic", "authentication middleware", "database connection pool".

        @param user_query: Natural language or keyword description of the code you're looking for
        @param repo_path: Optional path to scope to a specific repository
        @param limit: Max results to return (default 15)
        @return: Ranked list of relevant symbols with file locations and relevance scores
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            results = await orchestrator.graph_service.find_related_code(
                user_query, repo_path=repo_path, limit=limit
            )
            return api_response(
                success=True, status_code=200,
                message=f"Found related code for query: '{user_query}'",
                data=results, request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Error finding related code: {str(e)}",
                data=None, request_id=request_id, error_code="GRPH_003",
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 4. graph_build — Replaces: build_repository_graph, get_graph_stats
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def graph_build(
        repo_id: str,
        repo_path: str,
        include_stats: bool = True,
    ) -> Dict[str, Any]:
        """
        Build (or rebuild) the full code relationship graph for a repository using Tree-sitter parsing.

        Run this after indexing a repository to create the graph of function calls, class hierarchies,
        and import relationships. Use `include_stats=True` to also return graph node/edge counts.

        @param repo_id: Repository UUID (obtained from repo_init or index_repo)
        @param repo_path: Absolute path to the repository root directory
        @param include_stats: Whether to include node/edge count statistics in the response (default True)
        @return: Build result with statistics (functions, classes, files, calls, inherits counts)
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            repo_path_obj = Path(repo_path).resolve()
            if not repo_path_obj.exists():
                return api_response(
                    success=False, status_code=400,
                    message=f"Path not found: {repo_path}",
                    data=None, request_id=request_id, error_code="GRPH_004",
                )

            # Collect code files from DB
            cursor = orchestrator.db.conn.execute(
                "SELECT id, name, directory_id FROM files WHERE repository_id = ?", (repo_id,)
            )
            files = cursor.fetchall()
            file_paths = []
            for f in files:
                dir_cursor = orchestrator.db.conn.execute(
                    "SELECT relative_path FROM directories WHERE id = ?", (f["directory_id"],)
                )
                dir_row = dir_cursor.fetchone()
                if dir_row:
                    dir_path = dir_row["relative_path"] or ""
                    file_rel = f"{dir_path}/{f['name']}" if dir_path else f["name"]
                    file_paths.append(repo_path_obj / file_rel)

            build_stats = await orchestrator.graph_service.build_repository_graph(
                repo_id, repo_path_obj, file_paths
            )
            result = {"build": build_stats}

            if include_stats:
                backend = orchestrator.graph_service.graph_manager.get_backend()
                with backend.get_session() as session:
                    repo_row = orchestrator.db.conn.execute(
                        "SELECT root_path FROM repositories WHERE id = ?", (repo_id,)
                    ).fetchone()
                    p = repo_row["root_path"] if repo_row else None
                    queries = {
                        "functions": ("MATCH (r:Repository {path:$p})-[:CONTAINS*1..2]->(n:Function) RETURN count(n) AS count", {"p": p}) if p else ("MATCH (n:Function) RETURN count(n) AS count", {}),
                        "classes":   ("MATCH (r:Repository {path:$p})-[:CONTAINS*1..2]->(n:Class) RETURN count(n) AS count", {"p": p}) if p else ("MATCH (n:Class) RETURN count(n) AS count", {}),
                        "files":     ("MATCH (r:Repository {path:$p})-[:CONTAINS]->(n:File) RETURN count(n) AS count", {"p": p}) if p else ("MATCH (n:File) RETURN count(n) AS count", {}),
                        "calls":     ("MATCH (r:Repository {path:$p})-[:CONTAINS*1..2]->(a)-[e:CALLS]->() RETURN count(e) AS count", {"p": p}) if p else ("MATCH ()-[r:CALLS]->() RETURN count(r) AS count", {}),
                        "inherits":  ("MATCH (r:Repository {path:$p})-[:CONTAINS*1..2]->(a)-[e:INHERITS]->() RETURN count(e) AS count", {"p": p}) if p else ("MATCH ()-[r:INHERITS]->() RETURN count(r) AS count", {}),
                    }
                    stats = {}
                    for label, (q, params) in queries.items():
                        row = session.run(q, **params).single()
                        stats[label] = row["count"] if row else 0
                result["stats"] = stats

            return api_response(
                success=True, status_code=200,
                message="Graph construction completed",
                data=result, request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Error building graph: {str(e)}",
                data=None, request_id=request_id, error_code="GRPH_004",
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 5. graph_trace_flow — Moved from main.py; replaces: trace_execution_flow
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def graph_trace_flow(
        start_symbol_id: str,
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """
        Recursively trace the call graph starting from a specific symbol to identify the 'Happy Path'.

        Use this to understand the full execution flow of an entry point — API handler, CLI command,
        or any function — and map all downstream dependencies up to a configurable depth.

        @param start_symbol_id: Graph node ID of the starting symbol (use graph_find_symbols to get IDs)
        @param max_depth: Maximum recursion depth for call chain tracing (default 5)
        @return: Hierarchical call tree showing the execution flow and all transitive dependencies
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result = await orchestrator.graph_service.trace_execution_flow(
                start_symbol_id, max_depth
            )
            return api_response(
                success=True, status_code=200,
                message=f"Execution flow traced from '{start_symbol_id}' (depth={max_depth})",
                data=result, request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Error tracing execution flow: {str(e)}",
                data=None, request_id=request_id, error_code="GRPH_005",
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 6. arch_analyze — Replaces: analyze_architecture, get_architecture_summary (main)
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def arch_analyze(
        repo_id: Optional[str] = None,
        path: Optional[str] = None,
        include_summary: bool = True,
    ) -> Dict[str, Any]:
        """
        Run a full architectural analysis of a repository, detecting coupling, god nodes, and security issues.

        Provide either `repo_id` (for already-indexed repos) or `path` (for on-demand analysis).
        When `include_summary=True`, also generates a human-readable architectural narrative in Markdown.

        @param repo_id: Repository UUID from a previous indexing operation. Use this if repo is already indexed.
        @param path: Absolute path to the repo root. Use this for on-demand analysis without pre-indexing.
        @param include_summary: Whether to generate a high-level Markdown summary (default True)
        @return: Architectural analysis with coupling metrics, god nodes, security findings, and optional summary
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            if not repo_id and not path:
                return api_response(
                    success=False, status_code=400,
                    message="Provide either 'repo_id' or 'path'",
                    data=None, request_id=request_id, error_code="GRPH_006",
                )

            # If path given, sync repo first to get repo_id
            if path and not repo_id:
                repo_id = await orchestrator.repository_service.sync_repository(path)

            result = await orchestrator.graph_service.analyze_architecture(repo_id)

            if include_summary:
                try:
                    summary = await orchestrator.graph_service.build_comprehensive_report(repo_id)
                    result["markdown_summary"] = summary
                except Exception:
                    pass  # Summary is best-effort

            return api_response(
                success=True, status_code=200,
                message="Architectural analysis completed",
                data=result, request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Architecture analysis failed: {str(e)}",
                data=None, request_id=request_id, error_code="GRPH_006",
            )
        finally:
            orchestrator.db.close()

    # -------------------------------------------------------------------------
    # 7. arch_audit — Replaces: find_god_nodes, audit_security_hygiene,
    #                           find_dead_code, find_most_complex_functions
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def arch_audit(
        repo_id: str,
        audit_type: str = "all",
        threshold: int = 10,
        limit: int = 50,
        repo_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Audit the codebase for architectural smells: god nodes, security issues, dead code, and complexity hotspots.

        Run individual audits or run all at once with `audit_type="all"`. Results are actionable findings
        you can use to prioritize refactoring, security reviews, or dead code removal.

        @param repo_id: Repository UUID to audit
        @param audit_type: What to audit — "god_nodes" | "security" | "dead_code" | "complexity" | "all" (default: "all")
        @param threshold: Minimum in-degree to classify a node as a god node (default 10, used for god_nodes audit)
        @param limit: Max results per audit category (default 50, used for dead_code and complexity)
        @param repo_path: Optional repository path for graph-scoped queries
        @return: Audit findings organized by type, with severity levels and actionable recommendations
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            result: Dict[str, Any] = {}

            if audit_type in ("god_nodes", "all"):
                try:
                    G = await orchestrator.graph_service._build_graph_from_db(repo_id)
                    result["god_nodes"] = orchestrator.graph_service.find_god_nodes(G, threshold)
                except Exception as e:
                    result["god_nodes"] = {"error": str(e)}

            if audit_type in ("security", "all"):
                try:
                    result["security"] = orchestrator.graph_service._audit_security_hygiene(repo_id)
                except Exception as e:
                    result["security"] = {"error": str(e)}

            if audit_type in ("dead_code", "all"):
                try:
                    result["dead_code"] = await orchestrator.graph_service.find_dead_code(
                        repo_id, repo_path, limit
                    )
                except Exception as e:
                    result["dead_code"] = {"error": str(e)}

            if audit_type in ("complexity", "all"):
                try:
                    result["complexity"] = await orchestrator.graph_service.find_most_complex_functions(
                        limit, repo_path
                    )
                except Exception as e:
                    result["complexity"] = {"error": str(e)}

            if not result:
                return api_response(
                    success=False, status_code=400,
                    message=f"Unknown audit_type '{audit_type}'. Use: god_nodes, security, dead_code, complexity, all",
                    data=None, request_id=request_id, error_code="GRPH_007",
                )

            return api_response(
                success=True, status_code=200,
                message=f"Audit '{audit_type}' completed for repo '{repo_id}'",
                data=result, request_id=request_id,
            )
        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Audit failed: {str(e)}",
                data=None, request_id=request_id, error_code="GRPH_007",
            )
        finally:
            orchestrator.db.close()
