"""
CodeGraph CLI — Command-Line Interface for the CodeGraph domain.

Commands:
  build        Build / rebuild the code relationship graph
  query        Query code relationships (callers, callees, hierarchy, etc.)
  search       Search symbols, trace relations, semantic search
  audit        Run architectural audit (god nodes, dead code, security, etc.)
  relationship Explore architecture relationships with community detection
  refactor     Architectural-scale refactoring (impact / preview / apply / undo)
  viz          Render a subgraph as Mermaid or DOT diagram

:project: CodeCortex
:package: Modules.Codegraph.Api.Cli
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeGraph-v1.0
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

DOMAIN = "codegraph"
ALIASES = ["cg"]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (self-contained; avoids circular import issues)
# ─────────────────────────────────────────────────────────────────────────────

def _output(data: Any, pretty: bool = True) -> None:
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    text = json.dumps(data, **kwargs, default=str)
    buf = sys.stdout.buffer
    buf.write(text.encode("utf-8", errors="replace"))
    buf.write(b"\n")
    buf.flush()


def _ok(message: str, data: Any = None) -> Dict[str, Any]:
    return {"success": True, "status_code": 200, "message": message, "data": data}


def _err(message: str, code: str = "CG_CLI_ERROR", status: int = 400) -> Dict[str, Any]:
    return {"success": False, "status_code": status, "message": message, "data": {"explanation": f"No relevant data is available because an error occurred: {message}"}, "error_code": code}


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


def _parse_json_arg(value: Optional[str], flag: str) -> Dict:
    """Parse a --options / --fields JSON string argument safely."""
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"{flag} must be valid JSON: {exc}") from exc


def _parse_list_arg(value: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated string into a list, or None if empty."""
    if not value:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


@contextlib.contextmanager
def _cg_ctx():
    """Lazy orchestrator lifecycle — creates DB, yields it, closes on exit."""
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        yield orch
    finally:
        orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 1. graph_build
# ─────────────────────────────────────────────────────────────────────────────

def cmd_cg_build(args_ns: argparse.Namespace) -> Dict:
    """Build or rebuild the code relationship graph for a repository."""
    from src.modules.codegraph.services.coddy import CODDY
    with _cg_ctx() as orch:
        builder = CODDY(orch.db, orch.graph_service.graph_manager)
        result = _run_async(builder.build(
            repo_path=args_ns.repo_path,
            repo_id=getattr(args_ns, "repo_id", None),
            detect_modular=not args_ns.no_modular,
            build_dependency_graph=not args_ns.no_deps,
            include_core_contracts=not args_ns.no_contracts,
            scan_hmvc_p=not args_ns.no_hmvc,
            max_depth=args_ns.max_depth,
            use_cache=not args_ns.no_cache,
            incremental=not args_ns.force,
        ))
        mode = result.get("build_mode", "full_build")
        repo_id = result.get("repo_id", "")
        total_mods = result.get("modular_summary", {}).get("total_modules", 0)
        return _ok(
            f"Graph {mode} for '{args_ns.repo_path}' (repo_id={repo_id}, modules={total_mods})",
            result,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. graph_query
# ─────────────────────────────────────────────────────────────────────────────

def cmd_cg_query(args_ns: argparse.Namespace) -> Dict:
    """Query code relationships."""
    from src.modules.codegraph.services.trace import CODDYGraphTrace
    import networkx as nx

    query_type: str = args_ns.query_type
    target: str = args_ns.target
    fields = _parse_list_arg(getattr(args_ns, "fields", None))

    with _cg_ctx() as orch:
        # ── visualize ──────────────────────────────────────────────────────
        if query_type == "visualize":
            repo_id = getattr(args_ns, "repo_id", None)
            if not repo_id:
                return _err("--repo-id required for query_type=visualize", "CG_CLI_MISSING_ARG")
            G = _run_async(orch.graph_service._build_graph_from_db(repo_id))
            target_nodes = [n for n, d in G.nodes(data=True) if d.get("label", "") == target or n == target]
            if not target_nodes:
                return _err(f"Node '{target}' not found in graph for repo_id='{repo_id}'", "CG_CLI_NOT_FOUND", 404)
            sub_nodes: set = set()
            for tn in target_nodes:
                try:
                    ego = nx.ego_graph(G, tn, radius=min(args_ns.max_depth, 5), undirected=True)
                    sub_nodes.update(ego.nodes())
                except Exception:
                    sub_nodes.add(tn)
            subgraph = G.subgraph(sub_nodes)
            fmt = getattr(args_ns, "viz_format", "mermaid")
            if fmt == "dot":
                lines = ["digraph G {"]
                for n, d in subgraph.nodes(data=True):
                    label = d.get("label", n)
                    shape = "box" if d.get("type", "") in ("class", "module") else "ellipse"
                    lines.append(f'  "{n}" [label="{label}" shape={shape}];')
                for u, v, d in subgraph.edges(data=True):
                    lines.append(f'  "{u}" -> "{v}" [label="{d.get("relation_type", "")}"];')
                lines.append("}")
                diagram = "\n".join(lines)
            else:
                lines = ["graph LR"]
                seen: set = set()
                for u, v, d in subgraph.edges(data=True):
                    ul = subgraph.nodes[u].get("label", u)
                    vl = subgraph.nodes[v].get("label", v)
                    if (u, v) not in seen:
                        seen.add((u, v))
                        lines.append(f'  {ul}["{ul}"] -->|"{d.get("relation_type","")}"| {vl}["{vl}"]')
                diagram = "\n".join(lines)
            viz_data = {
                "format": fmt, "target": target,
                "node_count": subgraph.number_of_nodes(),
                "edge_count": subgraph.number_of_edges(),
                "diagram": diagram,
            }
            if fields:
                viz_data = {k: v for k, v in viz_data.items() if k in set(fields)}
            return _ok(f"Subgraph for '{target}' ({fmt})", viz_data)

        # ── trace_flow ─────────────────────────────────────────────────────
        if query_type == "trace_flow":
            result = _run_async(orch.graph_service.trace_execution_flow(target, min(args_ns.max_depth, 10)))
            return _ok(f"Execution flow from '{target}'", result)

        # ── trace_path / callers / callees (tracer) ────────────────────────
        if query_type in ("trace_path", "callers", "callees"):
            repo_id = getattr(args_ns, "repo_id", None)
            if not repo_id:
                return _err(f"--repo-id required for query_type={query_type}", "CG_CLI_MISSING_ARG")
            from src.modules.codegraph.services.trace import CODDYGraphTrace
            tracer = CODDYGraphTrace(orch.db, orch.graph_service.graph_manager)
            qt_mapped = "trace_path" if query_type == "trace_path" else f"find_{query_type}"
            result = _run_async(tracer.trace(
                repo_id=repo_id,
                query_type=qt_mapped,
                target_node=target,
                max_depth=min(args_ns.max_depth, 10),
                end_node=getattr(args_ns, "end_node", None),
                limit=args_ns.limit,
            ))
            return _ok(f"Query '{query_type}' on '{target}'", result)

        # ── all other query types (SQLite-backed) ──────────────────────────
        _RELATION_ALIASES = {
            "all_callers": "callers_recursive", "all_callees": "callees_recursive",
            "chain": "call_chain", "deps": "dependencies",
        }
        resolved = _RELATION_ALIASES.get(query_type, query_type)
        result = orch.graph_service.analyze_code_relationships(
            resolved, target,
            getattr(args_ns, "context", None),
            getattr(args_ns, "repo_path", None),
        )
        if fields and isinstance(result, dict):
            result = {k: v for k, v in result.items() if k in set(fields)}
        return _ok(f"Query '{query_type}' on '{target}'", result)


# ─────────────────────────────────────────────────────────────────────────────
# 3. graph_search
# ─────────────────────────────────────────────────────────────────────────────

def cmd_cg_search(args_ns: argparse.Namespace) -> Dict:
    """Unified symbol / relation / semantic / modular search."""
    from src.modules.codegraph.services.search import CODDYGraphSearch

    action: str = args_ns.action
    query: str = getattr(args_ns, "query", "") or ""
    fields = _parse_list_arg(getattr(args_ns, "fields", None))

    with _cg_ctx() as orch:
        if action == "symbol":
            symbol_type = getattr(args_ns, "symbol_type", "any")
            fuzzy = getattr(args_ns, "fuzzy", False)
            edit_dist = getattr(args_ns, "edit_distance", 2)
            repo_path = getattr(args_ns, "repo_path", None)
            combined: Dict[str, Any] = {"functions": [], "classes": [], "variables": [], "total": 0}
            if symbol_type in ("function", "any"):
                combined["functions"] = orch.graph_service.find_by_function_name(
                    query, repo_path, fuzzy, edit_dist, args_ns.limit)
            if symbol_type in ("class", "any"):
                combined["classes"] = orch.graph_service.find_by_class_name(
                    query, repo_path, fuzzy, edit_dist, args_ns.limit)
            if symbol_type in ("variable", "any"):
                combined["variables"] = orch.graph_service.find_by_variable_name(
                    query, repo_path, args_ns.limit)
            combined["total"] = len(combined["functions"]) + len(combined["classes"]) + len(combined["variables"])
            data = combined
            if fields:
                data = {k: v for k, v in data.items() if k in set(fields)}
            return _ok(f"Found {combined['total']} symbol(s) matching '{query}'", data)

        if action == "semantic":
            results = orch.graph_service.find_related_code(
                query, repo_path=getattr(args_ns, "repo_path", None), limit=args_ns.limit)
            return _ok(f"Semantic search for '{query}'", results)

        if action in ("relation", "trace_flow", "modular"):
            repo_id = getattr(args_ns, "repo_id", None)
            if not repo_id:
                return _err(f"--repo-id required for action={action}", "CG_CLI_MISSING_ARG")
            searcher = CODDYGraphSearch(orch.db, orch.graph_service.graph_manager)
            result = _run_async(searcher.search(
                repo_id=repo_id, action=action, query=query,
                relation_type=getattr(args_ns, "relation_type", None),
                target_symbol_id=getattr(args_ns, "target_symbol_id", None),
                max_depth=min(getattr(args_ns, "max_depth", 3), 10),
                modular_type=getattr(args_ns, "modular_type", None),
                fuzzy=getattr(args_ns, "fuzzy", False),
                limit=min(args_ns.limit, 200),
            ))
            return _ok(f"graph_search '{action}' completed", result)

        return _err(f"Unknown action '{action}'. Use: symbol, relation, trace_flow, modular, semantic", "CG_CLI_BAD_ACTION")


# ─────────────────────────────────────────────────────────────────────────────
# 4. graph_audit
# ─────────────────────────────────────────────────────────────────────────────

def cmd_cg_audit(args_ns: argparse.Namespace) -> Dict:
    """Full architectural audit."""
    from src.modules.codegraph.services.audit import CODDYGraphAudit

    repo_id: str = args_ns.repo_id
    audit_types = _parse_list_arg(getattr(args_ns, "types", None))
    fields = _parse_list_arg(getattr(args_ns, "fields", None))
    fix_suggestions: bool = getattr(args_ns, "fix_suggestions", False)
    degree_threshold: int = getattr(args_ns, "degree_threshold", 10)
    limit: int = args_ns.limit

    with _cg_ctx() as orch:
        import asyncio as _asyncio

        types = audit_types or ["god_nodes", "security", "dead_code", "complexity", "communities", "coupling", "circular_deps"]
        all_flag = "all" in types
        result: Dict[str, Any] = {}

        if all_flag or "god_nodes" in types:
            try:
                G = _run_async(orch.graph_service._build_graph_from_db(repo_id))
                result["god_nodes"] = orch.graph_service.find_god_nodes(G, degree_threshold)
            except Exception as e:
                result["god_nodes"] = {"error": str(e)}

        if all_flag or "security" in types:
            try:
                result["security"] = orch.graph_service._audit_security_hygiene(repo_id)
            except Exception as e:
                result["security"] = {"error": str(e)}

        if all_flag or "dead_code" in types:
            try:
                result["dead_code"] = orch.graph_service.find_dead_code(
                    repo_path=getattr(args_ns, "repo_path", None), limit=limit)
            except Exception as e:
                result["dead_code"] = {"error": str(e)}

        if all_flag or "complexity" in types:
            try:
                result["complexity"] = orch.graph_service.find_most_complex_functions(
                    limit=limit, repo_path=getattr(args_ns, "repo_path", None))
            except Exception as e:
                result["complexity"] = {"error": str(e)}

        if all_flag or "communities" in types or "coupling" in types:
            try:
                G = _run_async(orch.graph_service._build_graph_from_db(repo_id))
                communities = _run_async(_asyncio.to_thread(orch.graph_service.cluster_communities, G))
                if all_flag or "communities" in types:
                    result["communities"] = {"count": len(communities), "clusters": {str(k): v for k, v in communities.items()}}
                if all_flag or "coupling" in types:
                    node_to_comm = {node: cid for cid, nodes in communities.items() for node in nodes}
                    coupling = []
                    for u, v, data in G.edges(data=True):
                        score = orch.graph_service.calculate_surprise_score(G, u, v, node_to_comm)
                        if score > 0.4:
                            coupling.append({"source": u, "target": v, "score": score})
                    result["coupling"] = sorted(coupling, key=lambda x: x["score"], reverse=True)[:limit]
            except Exception as e:
                result["communities"] = {"error": str(e)}

        if all_flag or "circular_deps" in types:
            try:
                auditor = CODDYGraphAudit(orch.db, orch.graph_service.graph_manager)
                audit_result = _run_async(auditor.audit(repo_id=repo_id, max_depth=5, include_suggestions=True))
                result["circular_deps"] = {
                    "count": len(audit_result.get("circular_dependencies", [])),
                    "items": audit_result.get("circular_dependencies", []),
                    "suggestions": audit_result.get("suggestions", []),
                }
            except Exception as e:
                result["circular_deps"] = {"error": str(e)}

        # fix_suggestions: attach graph_refactor hints to god_node findings
        if fix_suggestions and "god_nodes" in result:
            god_list = result["god_nodes"]
            if isinstance(god_list, list):
                for gn in god_list:
                    name = gn.get("name") or gn.get("node_name", "")
                    if name:
                        gn["fix_suggestion"] = {
                            "command": f"codecortex cg refactor {repo_id} apply split_module {name}",
                            "hint": f"Run: codecortex cg refactor {repo_id} impact split_module {name}",
                        }

        if fields:
            result = {k: v for k, v in result.items() if k in set(fields)}

        completed = ", ".join(k for k in result)
        return _ok(f"Audit completed: {completed}", result)


# ─────────────────────────────────────────────────────────────────────────────
# 5. graph_relationship
# ─────────────────────────────────────────────────────────────────────────────

def cmd_cg_relationship(args_ns: argparse.Namespace) -> Dict:
    """Explore architecture relationships with community detection."""
    from src.modules.codegraph.services.relationship import CODDYGraphRelationship

    with _cg_ctx() as orch:
        rel = CODDYGraphRelationship(orch.db, orch.graph_service.graph_manager)
        result = _run_async(rel.explore(
            repo_id=args_ns.repo_id,
            target_node=args_ns.target_node,
            relation_type=_parse_list_arg(getattr(args_ns, "relation_type", None)),
            direction=getattr(args_ns, "direction", "both"),
            depth=getattr(args_ns, "depth", 1),
            modular_type=getattr(args_ns, "modular_type", None),
            include_community=getattr(args_ns, "community", False),
            min_confidence=getattr(args_ns, "min_confidence", "INFERRED"),
            limit=args_ns.limit,
        ))
        return _ok(f"Relationships for '{args_ns.target_node}'", result)


# ─────────────────────────────────────────────────────────────────────────────
# 6. graph_refactor
# ─────────────────────────────────────────────────────────────────────────────

def cmd_cg_refactor(args_ns: argparse.Namespace) -> Dict:
    """Architectural-scale code transformation."""
    from src.modules.codegraph.services.refactor import CODDYGraphRefactor

    action: str = args_ns.refactor_action
    repo_id: str = args_ns.repo_id

    with _cg_ctx() as orch:
        # ── undo_list ─────────────────────────────────────────────────────
        if action == "undo_list":
            try:
                rows = orch.db.conn.execute(
                    "SELECT id, target_node, refactor_type, created_at FROM refactor_undo_log ORDER BY created_at DESC LIMIT 20"
                ).fetchall()
                entries = [{"undo_id": r["id"], "target_node": r["target_node"],
                            "refactor_type": r["refactor_type"], "created_at": r["created_at"]}
                           for r in (rows or [])]
            except Exception:
                entries = []
            return _ok(f"Found {len(entries)} refactor log entries", {"entries": entries})

        # ── undo ──────────────────────────────────────────────────────────
        if action == "undo":
            undo_id = getattr(args_ns, "undo_id", None)
            if not undo_id:
                return _err("--undo-id required for action=undo", "CG_CLI_MISSING_ARG")
            try:
                row = orch.db.conn.execute(
                    "SELECT * FROM refactor_undo_log WHERE id = ?", (undo_id,)
                ).fetchone()
                if not row:
                    return _err(f"Undo log '{undo_id}' not found", "CG_CLI_NOT_FOUND", 404)
                changes = json.loads(row["changes"])
                orch.db.conn.execute("DELETE FROM refactor_undo_log WHERE id = ?", (undo_id,))
                orch.db.conn.commit()
                return _ok(
                    f"Undo log '{undo_id}' retrieved for {row['refactor_type']} on '{row['target_node']}'",
                    {"undo_id": undo_id, "target_node": row["target_node"],
                     "refactor_type": row["refactor_type"], "original_changes": changes},
                )
            except Exception as exc:
                return _err(f"Undo failed: {exc}", "CG_CLI_ERROR", 500)

        # ── impact / preview / apply ──────────────────────────────────────
        refactor_type = getattr(args_ns, "refactor_type", None)
        target_node = getattr(args_ns, "target_node", None)
        if not refactor_type:
            return _err("refactor_type required for impact/preview/apply", "CG_CLI_MISSING_ARG")
        if not target_node:
            return _err("target_node required for impact/preview/apply", "CG_CLI_MISSING_ARG")

        options_raw = getattr(args_ns, "options", None)
        options = _parse_json_arg(options_raw, "--options") if isinstance(options_raw, str) else (options_raw or {})
        dry_run: bool = getattr(args_ns, "dry_run", False)

        refacter = CODDYGraphRefactor(orch.db, orch.graph_service.graph_manager)
        result = _run_async(refacter.refactor(
            repo_id=repo_id, action=action, refactor_type=refactor_type,
            target_node=target_node, options=options, dry_run=dry_run,
        ))
        return _ok(f"graph_refactor '{action}' on '{target_node}' ({refactor_type})", result)


# ─────────────────────────────────────────────────────────────────────────────
# Command registry
# ─────────────────────────────────────────────────────────────────────────────

def cmd_cg_viz(args_ns: argparse.Namespace) -> Dict:
    """Visualize a subgraph — alias for `query visualize`."""
    args_ns.query_type = "visualize"
    if not hasattr(args_ns, "context"):
        args_ns.context = None
    if not hasattr(args_ns, "end_node"):
        args_ns.end_node = None
    if not hasattr(args_ns, "direction"):
        args_ns.direction = "both"
    if not hasattr(args_ns, "repo_path"):
        args_ns.repo_path = None
    return cmd_cg_query(args_ns)


CG_COMMANDS: Dict[str, Any] = {
    "build":        cmd_cg_build,
    "query":        cmd_cg_query,
    "search":       cmd_cg_search,
    "audit":        cmd_cg_audit,
    "relationship": cmd_cg_relationship,
    "rel":          cmd_cg_relationship,
    "refactor":     cmd_cg_refactor,
    "viz":          cmd_cg_viz,
}


# ─────────────────────────────────────────────────────────────────────────────
# Argument parser builder
# ─────────────────────────────────────────────────────────────────────────────

def build_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "codegraph", aliases=["cg"],
        help="Code relationship graph — build, query, audit, refactor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
CodeGraph — Code Relationship Intelligence

Commands:
  build        Build / rebuild the code relationship graph
  query        Query relationships (callers, hierarchy, trace, visualize, ...)
  search       Find symbols, trace relations, semantic search
  audit        Architectural audit (god nodes, dead code, complexity, ...)
  relationship Explore relationships with community detection
  refactor     Architectural-scale refactoring

Examples:
  codecortex cg build /path/to/repo
  codecortex cg build /path/to/repo --force
  codecortex cg query callers MyClass --repo-id <uuid>
  codecortex cg query visualize MyService --repo-id <uuid> --viz-format mermaid
  codecortex cg search symbol __init__ --symbol-type function
  codecortex cg search semantic "database connection handler"
  codecortex cg audit <repo_id>
  codecortex cg audit <repo_id> --types god_nodes,circular_deps --fix-suggestions
  codecortex cg relationship <repo_id> MyModule --community
  codecortex cg refactor <repo_id> impact split_module LargeService
  codecortex cg refactor <repo_id> apply split_module LargeService --options '{"new_module_name":"CoreService"}'
  codecortex cg refactor <repo_id> undo_list
  codecortex cg refactor <repo_id> undo --undo-id abc12345
        """,
    )
    sp = p.add_subparsers(dest="cg_action", required=True)

    # ── build ──────────────────────────────────────────────────────────────
    bp = sp.add_parser("build", help="Build the code relationship graph")
    bp.add_argument("repo_path", help="Absolute path to repository root")
    bp.add_argument("--repo-id", dest="repo_id", help="Repository UUID (auto-resolved if omitted)")
    bp.add_argument("--force", action="store_true", help="Force full rebuild (ignore cache + hash)")
    bp.add_argument("--no-cache", action="store_true", help="Disable all caching")
    bp.add_argument("--no-modular", action="store_true", help="Skip modular structure detection")
    bp.add_argument("--no-deps", action="store_true", help="Skip dependency graph build")
    bp.add_argument("--no-contracts", action="store_true", help="Skip core contracts scan")
    bp.add_argument("--no-hmvc", action="store_true", help="Skip HMVC-P scan")
    bp.add_argument("--max-depth", dest="max_depth", type=int, default=5, metavar="N",
                    help="Max submodule traversal depth (default: 5)")

    # ── query ──────────────────────────────────────────────────────────────
    qp = sp.add_parser("query", help="Query code relationships")
    qp.add_argument("query_type", choices=[
        "callers", "callees", "all_callers", "all_callees",
        "trace_path", "imports", "hierarchy", "overrides",
        "chain", "deps", "complexity", "dead_code", "trace_flow", "visualize",
    ], help="Relationship type to query")
    qp.add_argument("target", help="Symbol name (use module::function to disambiguate)")
    qp.add_argument("--repo-id", dest="repo_id", help="Repository UUID (required for trace_path/callers/callees/visualize)")
    qp.add_argument("--repo-path", dest="repo_path", help="Scope path for SQLite-backed queries")
    qp.add_argument("--max-depth", dest="max_depth", type=int, default=3, metavar="N")
    qp.add_argument("--end-node", dest="end_node", help="End node for trace_path query")
    qp.add_argument("--context", help="File path to disambiguate symbol name")
    qp.add_argument("--direction", choices=["inbound", "outbound", "both"], default="both")
    qp.add_argument("--limit", type=int, default=20)
    qp.add_argument("--viz-format", dest="viz_format", choices=["mermaid", "dot"], default="mermaid",
                    help="Visualization format for query_type=visualize (default: mermaid)")
    qp.add_argument("--fields", help="Comma-separated list of result fields to return")

    # ── viz alias ──────────────────────────────────────────────────────────
    vzp = sp.add_parser("viz", help="Render subgraph as Mermaid or DOT (alias for query visualize)")
    vzp.add_argument("target", help="Symbol name")
    vzp.add_argument("--repo-id", dest="repo_id", required=True)
    vzp.add_argument("--viz-format", dest="viz_format", choices=["mermaid", "dot"], default="mermaid")
    vzp.add_argument("--max-depth", dest="max_depth", type=int, default=3)
    vzp.add_argument("--fields", help="Comma-separated result fields")
    vzp.add_argument("--limit", type=int, default=20)

    # ── search ─────────────────────────────────────────────────────────────
    srp = sp.add_parser("search", help="Unified symbol / semantic / relation search")
    srp.add_argument("action", choices=["symbol", "relation", "trace_flow", "modular", "semantic"],
                     help="Search action")
    srp.add_argument("query", nargs="?", default="", help="Search keyword")
    srp.add_argument("--repo-id", dest="repo_id", help="Required for relation/trace_flow/modular")
    srp.add_argument("--repo-path", dest="repo_path", help="Scope path for symbol/semantic")
    srp.add_argument("--symbol-type", dest="symbol_type",
                     choices=["function", "class", "variable", "any"], default="any")
    srp.add_argument("--fuzzy", action="store_true", help="Enable fuzzy matching")
    srp.add_argument("--edit-distance", dest="edit_distance", type=int, default=2)
    srp.add_argument("--relation-type", dest="relation_type",
                     help="Relation subtype: callers, callees, imports, overrides, hierarchy, deps")
    srp.add_argument("--target-symbol-id", dest="target_symbol_id", help="Graph node ID for trace_flow")
    srp.add_argument("--max-depth", dest="max_depth", type=int, default=3)
    srp.add_argument("--modular-type", dest="modular_type",
                     help="Filter: module | plugin | widget | component | service")
    srp.add_argument("--limit", type=int, default=20)
    srp.add_argument("--fields", help="Comma-separated result fields")

    # ── audit ──────────────────────────────────────────────────────────────
    ap = sp.add_parser("audit", help="Architectural audit: god nodes, dead code, complexity, ...")
    ap.add_argument("repo_id", help="Repository UUID from graph_build")
    ap.add_argument("--types", help="Comma-separated audit types (default: all). "
                    "Options: god_nodes,security,dead_code,complexity,communities,coupling,circular_deps")
    ap.add_argument("--repo-path", dest="repo_path", help="Scope path for graph queries")
    ap.add_argument("--degree-threshold", dest="degree_threshold", type=int, default=10,
                    help="Min in-degree to classify as god node (default: 10)")
    ap.add_argument("--fix-suggestions", dest="fix_suggestions", action="store_true",
                    help="Attach graph_refactor CLI hints to god_node findings")
    ap.add_argument("--limit", type=int, default=50, help="Max results per audit type")
    ap.add_argument("--fields", help="Comma-separated top-level fields to return (reduces output size)")

    # ── relationship ───────────────────────────────────────────────────────
    rp = sp.add_parser("relationship", aliases=["rel"], help="Explore architecture relationships")
    rp.add_argument("repo_id", help="Repository UUID")
    rp.add_argument("target_node", help="Target module/class/function name")
    rp.add_argument("--relation-type", dest="relation_type",
                    help="Comma-separated: calls, imports, contains, inherits")
    rp.add_argument("--direction", choices=["inbound", "outbound", "both"], default="both")
    rp.add_argument("--depth", type=int, default=1)
    rp.add_argument("--modular-type", dest="modular_type",
                    help="Filter: module | plugin | widget | component | service")
    rp.add_argument("--community", action="store_true", help="Include community detection results")
    rp.add_argument("--min-confidence", dest="min_confidence",
                    choices=["EXTRACTED", "INFERRED", "AMBIGUOUS"], default="INFERRED")
    rp.add_argument("--limit", type=int, default=100)

    # ── refactor ───────────────────────────────────────────────────────────
    rfp = sp.add_parser("refactor", help="Architectural-scale code transformation")
    rfp.add_argument("repo_id", help="Repository UUID")
    rfp.add_argument("refactor_action", choices=["impact", "preview", "apply", "undo", "undo_list"],
                     help="Action: impact | preview | apply | undo | undo_list")
    rfp.add_argument("refactor_type", nargs="?",
                     choices=["split_module", "extract_component", "reroute_dependency",
                               "extract_interface", "inline_module", "extract_method", "inline_function"],
                     help="Refactor type (required for impact/preview/apply)")
    rfp.add_argument("target_node", nargs="?", help="Target module/class/function (required for impact/preview/apply)")
    rfp.add_argument("--options", help='JSON options dict, e.g. \'{"new_module_name":"Core"}\'')
    rfp.add_argument("--dry-run", dest="dry_run", action="store_true",
                     help="Simulate only, do not write changes")
    rfp.add_argument("--undo-id", dest="undo_id", help="Undo log ID (required for action=undo)")
