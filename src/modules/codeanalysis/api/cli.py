from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

DOMAIN = "codebase"
ALIASES = ["cb"]


# ── JSON Output ───────────────────────────────────────────

def output(data: Any, pretty: bool = True) -> None:
    """Print JSON to stdout as UTF-8 bytes (avoids Windows cp1252 issues)."""
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    text = json.dumps(data, **kwargs, default=str)
    buf = sys.stdout.buffer
    buf.write(text.encode("utf-8", errors="replace"))
    buf.write(b"\n")
    buf.flush()


def ok(message: str, data: Any = None) -> Dict[str, Any]:
    import dataclasses
    if dataclasses.is_dataclass(data):
        data = dataclasses.asdict(data)
    elif isinstance(data, list) and all(dataclasses.is_dataclass(d) for d in data):
        data = [dataclasses.asdict(d) for d in data]
    return {"success": True, "status_code": 200, "message": message, "data": data}


def err(message: str, code: str = "CLI_ERROR", status: int = 400) -> Dict[str, Any]:
    return {"success": False, "status_code": status, "message": message, "data": None, "error_code": code}


# ── Async Runner ──────────────────────────────────────────

def run_async(coro):
    """Safely run a coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


# ══════════════════════════════════════════════════════════════
# CODEBASE (8 actions)
# ══════════════════════════════════════════════════════════════

def cmd_cb_analyze(args_ns: argparse.Namespace) -> Dict:
    from src.modules.codeanalysis.services.analyze import Analyze, AnalyzeRequest
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        service = Analyze(db=orch.db.connection, fs_service=orch.fs_service)
        req = AnalyzeRequest(
            target=args_ns.target,
            mode=getattr(args_ns, "mode", "auto"),
            max_depth=getattr(args_ns, "max_depth", 3),
            include_docstring=True,
            focus=getattr(args_ns, "focus", None),
            follow_depth=getattr(args_ns, "follow_depth", 2),
            cursor=getattr(args_ns, "cursor", None),
        )
        result = service.analyze(req)
        return ok("Analysis complete", result)
    except Exception as e:
        return err(f"Analyze failed: {e}", "CB_ANALYZE_ERROR", 500)
    finally:
        orch.db.close()


def cmd_cb_search(args_ns: argparse.Namespace) -> Dict:
    from src.modules.codeanalysis.services.search import Search as SearchService
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        from src.modules.codeanalysis.core.dtos import SearchRequest
        service = SearchService(db=orch.db)
        req = SearchRequest(query=args_ns.query)
        result = service.search(request=req)
        return ok(f"Found {len(result.get('matches', []))} results", result)
    except Exception as e:
        return err(f"Search failed: {e}", "CB_SEARCH_ERROR", 500)
    finally:
        orch.db.close()


def cmd_cb_audit(args_ns: argparse.Namespace) -> Dict:
    from src.modules.codeanalysis.services.audit import Audit, AuditRequest
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        service = Audit(db=orch.db, fs_service=orch.fs_service)
        req = AuditRequest(
            target=args_ns.target,
            severity_threshold=getattr(args_ns, "severity", "medium"),
            max_file_size_kb=getattr(args_ns, "max_size", 1024),
            files=getattr(args_ns, "files", None),
        )
        result = service.audit(req)
        return ok("Code audit complete", result)
    except Exception as e:
        return err(f"Audit failed: {e}", "CB_AUDIT_ERROR", 500)
    finally:
        orch.db.close()


def cmd_cb_graph(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        sub = args_ns.graph_action
        target = args_ns.target
        rid = orch.get_repo_id(target)
        if not rid:
            return err("Repository not found. Initialize it first.", "REPO_NOT_FOUND", 404)

        if sub == "build":
            from src.modules.codegraph.services.graph import Graph
            svc = Graph(db=orch.db)
            result = run_async(svc.map_relationships(rid))
            return ok("Graph built", result)
        elif sub == "query":
            from src.modules.codegraph.services.search import GraphSearchService
            svc = GraphSearchService(db=orch.db)
            result = run_async(svc.query(
                target=target,
                query_node=getattr(args_ns, "query_node", None),
                max_depth=getattr(args_ns, "max_depth", 3),
            ))
            return ok("Graph query complete", result)
        elif sub == "relationships":
            from src.modules.codegraph.services.relationship import RelationshipService
            svc = RelationshipService(db=orch.db)
            result = run_async(svc.get_relationships(
                node_id=args_ns.target_node,
                direction=getattr(args_ns, "direction", "outgoing"),
            ))
            return ok("Relationships retrieved", result)
        elif sub == "audit":
            from src.modules.codegraph.services.audit import GraphAuditService
            svc = GraphAuditService(db=orch.db)
            result = run_async(svc.run_audit(
                rid, max_depth=getattr(args_ns, "max_depth", 3),
            ))
            return ok("Graph audit complete", result)
        else:
            return err(f"Unknown graph action: {sub}", "GRAPH_ERROR")
    except Exception as e:
        return err(f"Graph operation failed: {e}", "GRAPH_ERROR", 500)
    finally:
        orch.db.close()


def cmd_cb_index(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        sub = args_ns.index_action
        path = args_ns.target
        rid = orch.get_repo_id(path)

        if sub == "status":
            status = orch.db.conn.execute(
                "SELECT id, root_path, sync_at, created_at FROM repositories ORDER BY created_at DESC"
            ).fetchall()
            return ok("Index status", {"repositories": [dict(r) for r in status]})
        elif sub == "build":
            if not rid:
                return err("Repository not found", "REPO_NOT_FOUND", 404)
            run_async(orch.index_service.index_repository(rid))
            return ok("Index built", {"repo_id": rid})
        elif sub == "reindex":
            if not rid:
                rid = run_async(orch.repo_service.sync_repository(path))
            run_async(orch.index_service.index_repository(rid))
            return ok("Re-index complete", {"repo_id": rid})
        elif sub == "clear":
            if not rid:
                return err("Repository not found", "REPO_NOT_FOUND", 404)
            orch.db.conn.execute("DELETE FROM indexed_files WHERE repository_id=?", (rid,))
            orch.db.conn.execute("DELETE FROM embeddings WHERE repository_id=?", (rid,))
            orch.db.conn.commit()
            return ok("Index cleared", {"repo_id": rid})
        elif sub == "remove":
            if not rid:
                return err("Repository not found", "REPO_NOT_FOUND", 404)
            orch.db.conn.execute("DELETE FROM indexed_files WHERE repository_id=?", (rid,))
            orch.db.conn.execute("DELETE FROM embeddings WHERE repository_id=?", (rid,))
            orch.db.conn.execute("DELETE FROM symbols WHERE repository_id=?", (rid,))
            orch.db.conn.commit()
            return ok("Index removed", {"repo_id": rid})
        else:
            return err(f"Unknown index action: {sub}", "INDEX_ERROR")
    except Exception as e:
        return err(f"Index operation failed: {e}", "INDEX_ERROR", 500)
    finally:
        orch.db.close()


def cmd_cb_status(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        rid = args_ns.repo_id
        row = orch.db.conn.execute(
            "SELECT id, root_path, vcs_type, created_at, sync_at FROM repositories WHERE id=?",
            (rid,),
        ).fetchone()
        if not row:
            return err(f"Repository not found: {rid}", "REPO_NOT_FOUND", 404)
        return ok("Repository status", dict(row))
    except Exception as e:
        return err(f"Status failed: {e}", "STATUS_ERROR", 500)
    finally:
        orch.db.close()


def cmd_cb_test(args_ns: argparse.Namespace) -> Dict:
    from src.modules.codetester.services.tester import Tester
    from src.modules.codetester.core.dtos import CodeTesterRequest
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        service = Tester(db=orch.db)
        req = CodeTesterRequest(
            action="run",
            target_path=args_ns.path,
            test_framework=getattr(args_ns, "framework", "auto") or "auto",
        )
        result = service.run_tests(req)
        return ok("Tests completed", result)
    except Exception as e:
        return err(f"Test failed: {e}", "TEST_ERROR", 500)
    finally:
        orch.db.close()


def cmd_cb_refactor(args_ns: argparse.Namespace) -> Dict:
    from src.modules.coderefactor.services.refactor import Refactor
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        service = Refactor(
            db=orch.db,
            fs_service=orch.fs_service,
            git_service=orch.git_service,
            graph_service=orch.graph_service,
        )
        
        target_symbol = getattr(args_ns, "old_name", args_ns.target) or args_ns.target
        source_file = getattr(args_ns, "file", "")
        new_name = getattr(args_ns, "new_name", None)

        if new_name:
            result = run_async(service.rename_symbol(
                repo_id=args_ns.repo_id,
                symbol_name=target_symbol,
                source_file=source_file,
                new_name=new_name,
                dry_run=True,
            ))
        else:
            result = run_async(service.analyze_impact(
                repo_id=args_ns.repo_id,
                symbol_name=target_symbol,
                source_file=source_file,
            ))
            
        return ok("Refactoring complete", result)
    except Exception as e:
        return err(f"Refactor failed: {e}", "REFACTOR_ERROR", 500)
    finally:
        orch.db.close()


CB_COMMANDS = {
    "analyze": cmd_cb_analyze,
    "search": cmd_cb_search,
    "audit": cmd_cb_audit,
    "graph": cmd_cb_graph,
    "index": cmd_cb_index,
    "status": cmd_cb_status,
    "test": cmd_cb_test,
    "refactor": cmd_cb_refactor,
}


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("codebase", aliases=["cb"], help="Codebase intelligence and analysis")
    sp = p.add_subparsers(dest="cb_action", required=True)

    a = sp.add_parser("analyze", help="Analyze codebase")
    a.add_argument("target", help="File or directory path")
    a.add_argument("--mode", choices=["auto", "full", "quick"], default="auto", help="Analysis mode")
    a.add_argument("--max-depth", type=int, default=3, help="Max traversal depth")

    s = sp.add_parser("search", help="Semantic search")
    s.add_argument("query", help="Search query")
    s.add_argument("--target", help="Scope search to path")

    au = sp.add_parser("audit", help="Code audit")
    au.add_argument("target", help="Target path")
    au.add_argument("--mode", choices=["auto", "security", "quality"], default="auto", help="Audit mode")

    g = sp.add_parser("graph", help="Knowledge graph operations")
    g.add_argument("target", help="Repository path")
    g.add_argument("graph_action", choices=["build", "query", "relationships", "audit"], help="Graph sub-action")
    g.add_argument("--max-depth", type=int, default=3, help="Max traversal depth")
    g.add_argument("--query-node", help="Node name for query")
    g.add_argument("--target-node", help="Node ID for relationships")
    g.add_argument("--direction", choices=["incoming", "outgoing", "both"], default="outgoing", help="Relationship direction")

    ix = sp.add_parser("index", help="Index management")
    ix.add_argument("target", help="Repository path")
    ix.add_argument("index_action", choices=["status", "build", "reindex", "clear", "remove"], help="Index sub-action")

    st = sp.add_parser("status", help="Repository status")
    st.add_argument("repo_id", help="Repository ID")

    t = sp.add_parser("test", help="Run tests")
    t.add_argument("path", help="Test path")
    t.add_argument("--framework", help="Test framework")

    r = sp.add_parser("refactor", help="Refactor code")
    r.add_argument("repo_id", help="Repository ID")
    r.add_argument("target", help="Target path or symbol")
    r.add_argument("--old-name", help="Old name")
    r.add_argument("--new-name", help="New name")
    r.add_argument("--file", help="File path")
    r.add_argument("--symbol", action="store_true", help="Refactor symbol")
