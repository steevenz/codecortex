"""
Tools.

:project: CodeCortex
:package: Modules.Codegraph.Api.Tools
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

from __future__ import annotations
import asyncio
import json
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from src.core import api_response, new_request_id, ApiError
from src.modules.codegraph.services.aegis import AEGIS
from src.modules.codegraph.services.search import AEGISGraphSearch
from src.modules.codegraph.services.audit import AEGISGraphAudit
from src.modules.codegraph.services.trace import AEGISGraphTrace
from src.modules.codegraph.services.relationship import AEGISGraphRelationship
from src.modules.codegraph.services.refactor import AEGISGraphRefactor


_RELATION_ALIASES: Dict[str, str] = {
    "callers": "find_callers", "callees": "find_callees",
    "imports": "find_importers", "modifies": "who_modifies",
    "hierarchy": "class_hierarchy", "overrides": "overrides",
    "dead_code": "dead_code", "chain": "call_chain",
    "deps": "module_deps", "complexity": "find_complexity",
    "all_callers": "find_all_callers", "all_callees": "find_all_callees",
}


def _wrap_result(*, request_id: str, repo_id: Optional[str], raw: Any, default_message: str, default_status_code: int = 200, limit: Optional[int] = None) -> Dict[str, Any]:
    status_code = default_status_code
    payload = raw
    message = default_message
    error_code = None
    details = None
    if isinstance(raw, dict) and "status_code" in raw and "data" in raw:
        status_code = int(raw.get("status_code", default_status_code))
        payload = raw.get("data")
        message = str(raw.get("message", default_message))
        meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
        details = meta.get("details") if isinstance(meta, dict) else None
        if status_code >= 400:
            error_code = meta.get("error_code") if isinstance(meta, dict) else None

    pagination = None
    if isinstance(payload, dict):
        next_cursor = payload.get("next_cursor")
        has_more = payload.get("has_more")
        total = payload.get("total")
        if next_cursor is not None or has_more is not None or total is not None:
            pagination = {
                "next_cursor": next_cursor,
                "has_more": bool(has_more) if has_more is not None else None,
                "total": total,
                "limit": limit,
            }
            payload = {k: v for k, v in payload.items() if k not in ("next_cursor", "has_more", "total")}

    return api_response(
        success=(status_code < 400),
        status_code=status_code,
        message=message,
        data=payload,
        request_id=request_id,
        error_code=error_code,
        details=details,
        repo_id=repo_id,
        pagination=pagination,
    )


def _orchestrator_scope(orchestrator_factory):
    """Context manager to create and cleanup orchestrator."""
    class Scope:
        def __init__(self):
            self.orchestrator = orchestrator_factory()
        def close(self):
            pass
    return Scope()


def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """Register 6 consolidated codegraph tools (merged from 11)."""

    # ═══════════════════════════════════════════════════════════════════
    # 1. graph_search = graph_find_symbols + graph_search + graph_find_related
    # ═══════════════════════════════════════════════════════════════════

    @mcp.tool()
    async def graph_search(
        action: str,
        query: Optional[str] = None,
        repo_id: Optional[str] = None,
        repo_path: Optional[str] = None,
        symbol_type: str = "any",
        fuzzy: bool = False,
        edit_distance: int = 2,
        relation_type: Optional[str] = None,
        target_symbol_id: Optional[str] = None,
        max_depth: int = 3,
        modular_type: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Unified search: find symbols, trace relations, or semantic search.

        Actions:
        - "symbol": Find functions/classes/variables by name (fuzzy supported)
        - "relation": Find callers, callees, imports, hierarchy, overrides
        - "trace_flow": Trace execution path from a symbol
        - "modular": List modules, plugins, widgets, components
        - "semantic": Natural-language search for related code

        @param action: "symbol" | "relation" | "trace_flow" | "modular" | "semantic"
        @param query: Search keyword (for symbol, relation, semantic actions)
        @param repo_id: Repository UUID (required for relation/trace_flow/modular)
        @param repo_path: Optional path to scope search (for symbol/semantic actions)
        @param symbol_type: Filter by "function" | "class" | "variable" | "any" (default: "any")
        @param fuzzy: Enable fuzzy/typo-tolerant name matching (default False)
        @param edit_distance: Max edit distance for fuzzy search (default 2)
        @param relation_type: Relation subtype: "callers", "callees", "imports", "overrides", "hierarchy", "modifies", "deps"
        @param target_symbol_id: Graph node ID for trace_flow action
        @param max_depth: Traversal depth for relation/trace_flow (default 3, max 10)
        @param modular_type: Filter by "module" | "plugin" | "widget" | "component" | "core" | "service"
        @param limit: Max results (default 20, max 200)
        @param cursor: Pagination cursor for large result sets
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            if action == "symbol":
                combined = {"functions": [], "classes": [], "variables": [], "total": 0}
                if symbol_type in ("function", "any"):
                    combined["functions"] = await orchestrator.graph_service.find_by_function_name(
                        query or "", repo_path, fuzzy, edit_distance, limit
                    )
                if symbol_type in ("class", "any"):
                    combined["classes"] = await orchestrator.graph_service.find_by_class_name(
                        query or "", repo_path, fuzzy, edit_distance, limit
                    )
                if symbol_type in ("variable", "any"):
                    combined["variables"] = await orchestrator.graph_service.find_by_variable_name(
                        query or "", repo_path, limit
                    )
                combined["total"] = len(combined["functions"]) + len(combined["classes"]) + len(combined["variables"])
                return api_response(success=True, insight="graph_search", status_code=200,
                    message=f"Found {combined['total']} symbol(s) matching '{query}'",
                    data=combined, request_id=request_id)

            if action == "semantic":
                results = await orchestrator.graph_service.find_related_code(
                    query or "", repo_path=repo_path, limit=limit
                )
                return api_response(success=True, insight="graph_search", status_code=200,
                    message=f"Found related code for: '{query}'",
                    data=results, request_id=request_id)

            if action in ("relation", "trace_flow", "modular"):
                if not repo_id:
                    return api_response(success=False, status_code=400,
                        message=f"repo_id required for action='{action}'",
                        data=None, request_id=request_id, error_code="GRPH_008")
                searcher = AEGISGraphSearch(orchestrator.db, orchestrator.graph_service.graph_manager)
                result = await searcher.search(
                    repo_id=repo_id, action=action, query=query,
                    relation_type=relation_type, target_symbol_id=target_symbol_id,
                    max_depth=min(max_depth, 10), modular_type=modular_type,
                    fuzzy=fuzzy, limit=min(limit, 200), cursor=cursor,
                )
                return _wrap_result(
                    request_id=request_id,
                    repo_id=repo_id,
                    raw=result,
                    default_message=f"graph_search '{action}' completed",
                    limit=min(limit, 200),
                )

            return api_response(success=False, status_code=400,
                message=f"Unknown action '{action}'. Use: symbol, relation, trace_flow, modular, semantic",
                data=None, request_id=request_id, error_code="GRPH_008")
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details)
        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"graph_search error: {str(e)}", data=None,
                request_id=request_id, error_code="GRPH_008")

    # ═══════════════════════════════════════════════════════════════════
    # 2. graph_query = graph_query + graph_trace_flow + graph_trace
    # ═══════════════════════════════════════════════════════════════════

    @mcp.tool()
    async def graph_query(
        query_type: str,
        target: str,
        repo_id: Optional[str] = None,
        repo_path: Optional[str] = None,
        max_depth: int = 3,
        end_node: Optional[str] = None,
        context: Optional[str] = None,
        direction: str = "both",
        limit: int = 20,
        viz_format: str = "mermaid",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Query code relationships: callers, callees, hierarchy, trace path, and more.

        query_type options:
          "callers"/"callees"         → direct callers/callees of target
          "all_callers"/"all_callees" → recursive deep callers/callees
          "trace_path"                → shortest path between target and end_node
          "imports"                   → files that import the target module
          "hierarchy"                 → parent/child classes of target
          "overrides"                 → methods that override target
          "chain"                     → call chain from target
          "deps"                      → module dependencies
          "complexity"                → cyclomatic complexity
          "dead_code"                 → unused functions in scope
          "trace_flow"                → full execution flow from target
          "visualize"                 → render subgraph as DOT or Mermaid diagram

        @param query_type: Relationship type to query
        @param target: Symbol name (use "module::function" to disambiguate)
        @param repo_id: Repository UUID (required for trace_path/trace_flow/visualize)
        @param repo_path: Optional path to scope SQLite-backed queries
        @param max_depth: Max traversal depth for recursive queries (default 3, max 10)
        @param end_node: Target end symbol for trace_path query
        @param context: Optional file path to disambiguate symbol name
        @param direction: "inbound" | "outbound" | "both" (default: "both")
        @param limit: Max results (default 20)
        @param viz_format: Visualization format for query_type="visualize": "mermaid" | "dot" (default: "mermaid")
        @param fields: Return only these top-level result keys — reduces response size
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            if query_type == "trace_flow":
                result = await orchestrator.graph_service.trace_execution_flow(target, min(max_depth, 10))
                return api_response(success=True, insight="graph_query", status_code=200,
                    message=f"Execution flow traced from '{target}' (depth={max_depth})",
                    data=result, request_id=request_id)

            if query_type == "trace_path":
                if not repo_id:
                    return api_response(success=False, status_code=400,
                        message="repo_id required for trace_path", data=None,
                        request_id=request_id, error_code="GRPH_002")
                tracer = AEGISGraphTrace(orchestrator.db, orchestrator.graph_service.graph_manager)
                result = await tracer.trace(
                    repo_id=repo_id, query_type="trace_path", target_node=target,
                    max_depth=min(max_depth, 10), end_node=end_node, limit=limit)
                return _wrap_result(request_id=request_id, repo_id=repo_id, raw=result, default_message="trace_path completed", limit=limit)

            if query_type in ("callers", "callees") and repo_id:
                tracer = AEGISGraphTrace(orchestrator.db, orchestrator.graph_service.graph_manager)
                result = await tracer.trace(
                    repo_id=repo_id, query_type=f"find_{query_type}", target_node=target,
                    max_depth=min(max_depth, 10), limit=limit)
                return _wrap_result(request_id=request_id, repo_id=repo_id, raw=result, default_message=f"find_{query_type} completed", limit=limit)

            if query_type == "visualize":
                if not repo_id:
                    return api_response(success=False, status_code=400,
                        message="repo_id required for query_type='visualize'",
                        data=None, request_id=request_id, error_code="GRPH_002")
                G = await orchestrator.graph_service._build_graph_from_db(repo_id)
                # Extract ego-graph around target up to max_depth
                import networkx as _nx
                target_nodes = [n for n, d in G.nodes(data=True) if d.get("label", "") == target or n == target]
                if not target_nodes:
                    return api_response(success=False, status_code=404,
                        message=f"Node '{target}' not found in graph for repo_id='{repo_id}'",
                        data=None, request_id=request_id, error_code="GRPH_002")
                sub_nodes: set = set()
                for tn in target_nodes:
                    try:
                        ego = _nx.ego_graph(G, tn, radius=min(max_depth, 5), undirected=True)
                        sub_nodes.update(ego.nodes())
                    except Exception:
                        sub_nodes.add(tn)
                subgraph = G.subgraph(sub_nodes)
                if viz_format == "dot":
                    lines = ["digraph G {"]
                    for n, d in subgraph.nodes(data=True):
                        label = d.get("label", n)
                        ntype = d.get("type", "")
                        shape = "box" if ntype in ("class", "module") else "ellipse"
                        lines.append(f'  "{n}" [label="{label}" shape={shape}];')
                    for u, v, d in subgraph.edges(data=True):
                        rel = d.get("relation_type", "")
                        lines.append(f'  "{u}" -> "{v}" [label="{rel}"];')
                    lines.append("}")
                    diagram = "\n".join(lines)
                else:  # mermaid
                    lines = ["graph LR"]
                    seen_edges: set = set()
                    for u, v, d in subgraph.edges(data=True):
                        ul = subgraph.nodes[u].get("label", u)
                        vl = subgraph.nodes[v].get("label", v)
                        rel = d.get("relation_type", "")
                        edge_key = (u, v)
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            lines.append(f'  {ul}["{ul}"] -->|"{rel}"| {vl}["{vl}"]')
                    diagram = "\n".join(lines)
                viz_data = {
                    "format": viz_format,
                    "target": target,
                    "node_count": subgraph.number_of_nodes(),
                    "edge_count": subgraph.number_of_edges(),
                    "diagram": diagram,
                }
                if fields:
                    viz_data = {k: v for k, v in viz_data.items() if k in set(fields)}
                return api_response(success=True, insight="graph_query", status_code=200,
                    message=f"Subgraph visualization for '{target}' ({viz_format})",
                    data=viz_data, request_id=request_id)

            resolved_type = _RELATION_ALIASES.get(query_type, query_type)
            results = await orchestrator.graph_service.analyze_code_relationships(
                resolved_type, target, context, repo_path)
            if fields:
                results = {k: v for k, v in results.items() if k in set(fields)} if isinstance(results, dict) else results
            return api_response(success=True, insight="graph_query", status_code=200,
                message=f"Query '{query_type}' on '{target}' completed",
                data=results, request_id=request_id)
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details)
        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"graph_query error ({query_type}): {str(e)}",
                data=None, request_id=request_id, error_code="GRPH_002")

    # ═══════════════════════════════════════════════════════════════════
    # 3. graph_audit = arch_analyze + arch_audit + graph_audit (AEGIS)
    # ═══════════════════════════════════════════════════════════════════

    @mcp.tool()
    async def graph_audit(
        repo_id: str,
        audit_types: Optional[List[str]] = None,
        repo_path: Optional[str] = None,
        include_summary: bool = False,
        include_fix_suggestions: bool = False,
        degree_threshold: int = 10,
        limit: int = 50,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Full architectural audit: god nodes, security, dead code, complexity, communities, coupling.

        audit_types (default all):
          "god_nodes"     → symbols with high in-degree (central hubs)
          "security"      → security hygiene issues
          "dead_code"     → uncalled functions and unused code
          "complexity"    → functions with highest cyclomatic complexity
          "communities"   → Leiden community clusters and coupling
          "circular_deps" → circular dependency chains
          "coupling"      → surprising connections between unrelated modules

        @param repo_id: Repository UUID from graph_build or repo_analyze
        @param audit_types: List of audit types to run (default: all)
        @param repo_path: Optional path for graph-scoped queries
        @param include_summary: Generate comprehensive markdown report (default False)
        @param include_fix_suggestions: Attach ready-to-use graph_refactor call hints to god_node findings (default False)
        @param degree_threshold: Min in-degree to classify as god node (default 10)
        @param limit: Max results per audit type (default 50)
        @param fields: Return only these top-level result keys (e.g. ["god_nodes","security"]) — reduces response size
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            types = audit_types or ["god_nodes", "security", "dead_code", "complexity", "communities", "coupling", "circular_deps"]
            all_flag = "all" in types
            result: Dict[str, Any] = {}

            if all_flag or "god_nodes" in types:
                try:
                    G = await orchestrator.graph_service._build_graph_from_db(repo_id)
                    result["god_nodes"] = orchestrator.graph_service.find_god_nodes(G, degree_threshold)
                except Exception as e:
                    result["god_nodes"] = {"error": str(e)}

            if all_flag or "security" in types:
                try:
                    result["security"] = orchestrator.graph_service._audit_security_hygiene(repo_id)
                except Exception as e:
                    result["security"] = {"error": str(e)}

            if all_flag or "dead_code" in types:
                try:
                    result["dead_code"] = await orchestrator.graph_service.find_dead_code(repo_id, repo_path, limit)
                except Exception as e:
                    result["dead_code"] = {"error": str(e)}

            if all_flag or "complexity" in types:
                try:
                    result["complexity"] = await orchestrator.graph_service.find_most_complex_functions(limit, repo_path)
                except Exception as e:
                    result["complexity"] = {"error": str(e)}

            if all_flag or "communities" in types or "coupling" in types:
                try:
                    G = await orchestrator.graph_service._build_graph_from_db(repo_id)
                    communities = await asyncio.to_thread(orchestrator.graph_service.cluster_communities, G)
                    if all_flag or "communities" in types:
                        result["communities"] = {
                            "count": len(communities),
                            "clusters": {str(k): v for k, v in communities.items()},
                        }
                    if all_flag or "coupling" in types:
                        node_to_comm = {node: cid for cid, nodes in communities.items() for node in nodes}
                        coupling = []
                        for u, v, data in G.edges(data=True):
                            score = orchestrator.graph_service.calculate_surprise_score(G, u, v, node_to_comm)
                            if score > 0.4:
                                coupling.append({"source": u, "target": v, "score": score, "relation": data.get("relation_type", "CALLS")})
                        result["coupling"] = sorted(coupling, key=lambda x: x["score"], reverse=True)[:limit]
                except Exception as e:
                    if all_flag or "communities" in types:
                        result["communities"] = {"error": str(e)}
                    if all_flag or "coupling" in types:
                        result["coupling"] = {"error": str(e)}

            if all_flag or "circular_deps" in types:
                try:
                    auditor = AEGISGraphAudit(orchestrator.db, orchestrator.graph_service.graph_manager)
                    audit_result = await auditor.audit(repo_id=repo_id, max_depth=5, include_suggestions=True)
                    result["circular_deps"] = {
                        "count": len(audit_result.get("circular_dependencies", [])),
                        "items": audit_result.get("circular_dependencies", []),
                        "suggestions": audit_result.get("suggestions", []),
                    }
                except Exception as e:
                    result["circular_deps"] = {"error": str(e)}

            if include_summary:
                try:
                    summary = await orchestrator.graph_service.build_comprehensive_report(repo_id)
                    result["markdown_summary"] = summary
                except Exception:
                    pass

            # ── fix_suggestions: attach graph_refactor hints to god_node findings ──
            if include_fix_suggestions and "god_nodes" in result:
                god_list = result["god_nodes"]
                if isinstance(god_list, list):
                    for gn in god_list:
                        name = gn.get("name") or gn.get("node_name", "")
                        if name:
                            gn["fix_suggestion"] = {
                                "tool": "graph_refactor",
                                "params": {
                                    "repo_id": repo_id,
                                    "action": "impact",
                                    "refactor_type": "split_module",
                                    "target_node": name,
                                },
                                "hint": f"Run graph_refactor with action='preview' then action='apply' to split '{name}'",
                            }

            # ── fields filter: return only requested keys (token reduction) ──────
            if fields:
                allowed = set(fields)
                result = {k: v for k, v in result.items() if k in allowed}

            return api_response(success=True, insight="graph_audit", status_code=200,
                message=f"Audit completed: {', '.join(k for k in result if k != 'markdown_summary')}",
                data=result, request_id=request_id)
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details)
        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"graph_audit failed: {str(e)}", data=None,
                request_id=request_id, error_code="GRPH_009")

    # ═══════════════════════════════════════════════════════════════════
    # 4. graph_build (unchanged)
    # ═══════════════════════════════════════════════════════════════════

    @mcp.tool()
    async def graph_build(
        repo_path: str,
        repo_id: Optional[str] = None,
        detect_modular: bool = True,
        build_dependency_graph: bool = True,
        include_core_contracts: bool = True,
        scan_hmvc_p: bool = True,
        max_depth: int = 5,
        use_cache: bool = True,
        incremental: bool = True,
        include_stats: bool = True,
    ) -> Dict[str, Any]:
        """
        Build (or rebuild) the full code relationship graph for a repository using Tree-sitter parsing.

        @param repo_path: Absolute path to the repository root directory
        @param repo_id: Optional UUID of the repository (auto-resolved if not provided)
        @param detect_modular: Detect AEGIS modular structure
        @param build_dependency_graph: Build module dependency graph
        @param include_core_contracts: Include core/Contracts/ as nodes in the graph
        @param scan_hmvc_p: Scan HMVC-P structure
        @param max_depth: Maximum depth for submodule traversal
        @param use_cache: Use cached graph if available (default: True)
        @param incremental: Use hash-based auto-invalidation — skip rebuild if files unchanged (default: True). Set False to force full rebuild.
        @param include_stats: Whether to include node/edge count statistics
        @return: Build result with modular summary, dependency graph, metrics, AI recommendations, and build_mode indicator
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            repo_path_obj = Path(repo_path).resolve()
            if not repo_path_obj.exists():
                return api_response(success=False, status_code=400,
                    message=f"Path not found: {repo_path}", data=None,
                    request_id=request_id, error_code="GRPH_004")

            builder = AEGIS(orchestrator.db, orchestrator.graph_service.graph_manager)
            result = await builder.build(
                repo_path=str(repo_path_obj), repo_id=repo_id,
                detect_modular=detect_modular, build_dependency_graph=build_dependency_graph,
                include_core_contracts=include_core_contracts, scan_hmvc_p=scan_hmvc_p,
                max_depth=max_depth, use_cache=use_cache, incremental=incremental,
            )
            if include_stats:
                backend = orchestrator.graph_service.graph_manager.get_backend()
                with backend.get_session() as session:
                    repo_row = orchestrator.db.conn.execute(
                        "SELECT root_path FROM repositories WHERE root_path = ?", (str(repo_path_obj),)
                    ).fetchone()
                    p = repo_row["root_path"] if repo_row else None
                    queries = {
                        "functions": (f"MATCH (r:Repository {{path:$p}})-[*1..2]->(n:Function) RETURN count(n) AS count" if p else "MATCH (n:Function) RETURN count(n) AS count", {"p": p} if p else {}),
                        "classes": (f"MATCH (r:Repository {{path:$p}})-[*1..2]->(n:Class) RETURN count(n) AS count" if p else "MATCH (n:Class) RETURN count(n) AS count", {"p": p} if p else {}),
                        "files": (f"MATCH (r:Repository {{path:$p}})->(n:File) RETURN count(n) AS count" if p else "MATCH (n:File) RETURN count(n) AS count", {"p": p} if p else {}),
                        "calls": (f"MATCH (r:Repository {{path:$p}})-[*1..2]->(a)-[e:CALLS]->() RETURN count(e) AS count" if p else "MATCH ()-[r:CALLS]->() RETURN count(r) AS count", {"p": p} if p else {}),
                        "inherits": (f"MATCH (r:Repository {{path:$p}})-[*1..2]->(a)-[e:INHERITS]->() RETURN count(e) AS count" if p else "MATCH ()-[r:INHERITS]->() RETURN count(r) AS count", {"p": p} if p else {}),
                    }
                    stats = {}
                    for label, (q, params) in queries.items():
                        try:
                            row = session.run(q, **params).single()
                            stats[label] = row["count"] if row else 0
                        except Exception:
                            stats[label] = 0
                    if isinstance(result, dict):
                        result["graph_stats"] = stats

            effective_repo_id = result.get("repo_id") if isinstance(result, dict) else repo_id
            return api_response(success=True, insight="graph_build",
                status_code=200,
                message="graph_build completed",
                data=result,
                request_id=request_id,
                repo_id=effective_repo_id,
            )
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details)
        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"graph_build error: {str(e)}", data=None,
                request_id=request_id, error_code="GRPH_004")

    # ═══════════════════════════════════════════════════════════════════
    # 5. graph_relationship (unchanged)
    # ═══════════════════════════════════════════════════════════════════

    @mcp.tool()
    async def graph_relationship(
        repo_id: str,
        target_node: str,
        relation_type: Optional[List[str]] = None,
        direction: str = "both",
        depth: int = 1,
        modular_type: Optional[str] = None,
        include_community: bool = False,
        min_confidence: str = "INFERRED",
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Explore architecture relationships with community detection.

        @param repo_id: Repository UUID from graph_build or repo_analyze
        @param target_node: Target module/class/function name
        @param relation_type: "calls", "imports", "contains", "inherits"
        @param direction: "inbound" | "outbound" | "both" (default: "both")
        @param depth: Exploration depth (default 1)
        @param modular_type: Filter by: "module" | "plugin" | "widget" | "component" | "service"
        @param include_community: Include Leiden community detection results
        @param min_confidence: Minimum confidence: "EXTRACTED" | "INFERRED" | "AMBIGUOUS"
        @param limit: Maximum results (default 100)
        @param cursor: Pagination cursor
        @return: Relationship exploration with metrics and community info
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            explorer = AEGISGraphRelationship(orchestrator.db, orchestrator.graph_service.graph_manager)
            result = await explorer.explore(
                repo_id=repo_id, target_node=target_node, relation_type=relation_type,
                direction=direction, depth=depth, modular_type=modular_type,
                include_community=include_community, min_confidence=min_confidence,
                limit=limit, cursor=cursor,
            )
            return _wrap_result(request_id=request_id, repo_id=repo_id, raw=result, default_message="graph_relationship completed", limit=limit)
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details)
        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"graph_relationship error: {str(e)}", data=None,
                request_id=request_id, error_code="GRPH_011")

    # ═══════════════════════════════════════════════════════════════════
    # 6. graph_refactor (unchanged)
    # ═══════════════════════════════════════════════════════════════════

    @mcp.tool()
    async def graph_refactor(
        repo_id: str,
        action: str,
        refactor_type: Optional[str] = None,
        target_node: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        undo_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Architectural-scale code transformation using graph-first approach.

        @param repo_id: Repository UUID from graph_build or repo_analyze
        @param action: "impact" | "preview" | "apply" | "undo" | "undo_list"
        @param refactor_type: "split_module" | "extract_component" | "reroute_dependency" | "extract_interface" | "inline_module" | "extract_method" | "inline_function"
        @param target_node: Target module/class/function name
        @param options: Refactor-specific options dict (varies by refactor_type)
        @param dry_run: If True, only simulate without writing changes (default: False)
        @param undo_id: Undo log ID returned by a previous apply action (required for action="undo")
        @return: Impact analysis, preview, apply confirmation with undo_id, or undo result
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            # ── undo_list: list recent refactor log entries ──────────────────
            if action == "undo_list":
                try:
                    rows = orchestrator.db.conn.execute(
                        "SELECT id, target_node, refactor_type, created_at FROM refactor_undo_log ORDER BY created_at DESC LIMIT 20"
                    ).fetchall()
                    entries = [{"undo_id": r["id"], "target_node": r["target_node"], "refactor_type": r["refactor_type"], "created_at": r["created_at"]} for r in (rows or [])]
                except Exception:
                    entries = []
                return api_response(success=True, insight="graph_refactor", status_code=200,
                    message=f"Found {len(entries)} refactor log entries",
                    data={"entries": entries}, request_id=request_id)

            # ── undo: revert a previous apply ────────────────────────────────
            if action == "undo":
                if not undo_id:
                    return api_response(success=False, status_code=400,
                        message="undo_id is required for action='undo'",
                        data=None, request_id=request_id, error_code="GRPH_012")
                try:
                    row = orchestrator.db.conn.execute(
                        "SELECT * FROM refactor_undo_log WHERE id = ?", (undo_id,)
                    ).fetchone()
                    if not row:
                        return api_response(success=False, status_code=404,
                            message=f"Undo log entry '{undo_id}' not found",
                            data=None, request_id=request_id, error_code="GRPH_012")
                    import json as _json
                    changes = _json.loads(row["changes"])
                    orchestrator.db.conn.execute("DELETE FROM refactor_undo_log WHERE id = ?", (undo_id,))
                    orchestrator.db.conn.commit()
                    return api_response(success=True, insight="graph_refactor", status_code=200,
                        message=f"Undo log '{undo_id}' retrieved. Manual revert required for: {row['refactor_type']} on '{row['target_node']}'",
                        data={"undo_id": undo_id, "target_node": row["target_node"], "refactor_type": row["refactor_type"], "original_changes": changes, "status": "undo_log_cleared"},
                        request_id=request_id)
                except Exception as ex:
                    return api_response(success=False, status_code=500,
                        message=f"Undo failed: {str(ex)}", data=None,
                        request_id=request_id, error_code="GRPH_012")

            # ── impact / preview / apply ──────────────────────────────────────
            if not refactor_type:
                return api_response(success=False, status_code=400,
                    message="refactor_type is required for impact/preview/apply actions",
                    data=None, request_id=request_id, error_code="GRPH_012")
            if not target_node:
                return api_response(success=False, status_code=400,
                    message="target_node is required for impact/preview/apply actions",
                    data=None, request_id=request_id, error_code="GRPH_012")

            refacter = AEGISGraphRefactor(orchestrator.db, orchestrator.graph_service.graph_manager)
            result = await refacter.refactor(
                repo_id=repo_id, action=action, refactor_type=refactor_type,
                target_node=target_node, options=options or {}, dry_run=dry_run,
            )
            return _wrap_result(request_id=request_id, repo_id=repo_id, raw=result, default_message="graph_refactor completed")
        except ApiError as e:
            return api_response(success=False, status_code=e.status_code, message=str(e), data=None, request_id=request_id, error_code=e.error_code, details=e.details)
        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"graph_refactor error: {str(e)}", data=None,
                request_id=request_id, error_code="GRPH_012")
