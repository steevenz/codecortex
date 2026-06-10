from __future__ import annotations
import argparse
import asyncio
import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from src.core import api_response, new_request_id

DOMAIN = "idegraph"
ALIASES = ["ig"]


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


# ── Async Runner ──────────────────────────────────────────

def run_async(coro):
    """Safely run a coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


@contextlib.contextmanager
def _idegraph_ctx():
    """Lazy import + lifecycle. Closes DB on exit."""
    from src.modules.idegraph.services.sidecortex import SideCortex
    from src.modules.idegraph.services.storage import Storage
    from src.modules.idegraph.services.search import Search
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        yield (SideCortex(db=orch.db), Search(db=orch.db), Storage(db=orch.db))
    finally:
        orch.db.close()


def cmd_ig_search(args_ns: argparse.Namespace) -> Dict:
    request_id = new_request_id()
    with _idegraph_ctx() as (_, s, _):
        # Use enhanced search engine if any advanced params provided
        use_enhanced = bool(
            args_ns.search_mode or args_ns.search_fields or args_ns.date_from or
            args_ns.date_to or args_ns.min_messages is not None or args_ns.max_messages is not None
        )
        if use_enhanced:
            from src.modules.idegraph.services.search_engine import SearchEngine, SearchQuery, SearchMode, SearchField
            engine = SearchEngine(db=s._db if hasattr(s, '_db') else None)
            sq = engine.explain_query(args_ns.query)
            if args_ns.search_mode:
                try:
                    sq.mode = SearchMode(args_ns.search_mode.lower())
                except ValueError:
                    pass
            if args_ns.search_fields:
                sq.fields = []
                for f in args_ns.search_fields.split(","):
                    f = f.strip().lower()
                    try:
                        sq.fields.append(SearchField(f))
                    except ValueError:
                        pass
                if not sq.fields:
                    sq.fields = [SearchField.ALL]
            if args_ns.date_from:
                from datetime import datetime as dt_parse
                try:
                    sq.date_from = dt_parse.fromisoformat(args_ns.date_from.replace("Z", "+00:00"))
                except Exception:
                    pass
            if args_ns.date_to:
                from datetime import datetime as dt_parse
                try:
                    sq.date_to = dt_parse.fromisoformat(args_ns.date_to.replace("Z", "+00:00"))
                except Exception:
                    pass
            if args_ns.min_messages is not None:
                sq.min_messages = args_ns.min_messages
            if args_ns.max_messages is not None:
                sq.max_messages = args_ns.max_messages
            sq.project_name = args_ns.project
            sq.ide_name = args_ns.ide
            results = engine.search(sq, limit=args_ns.limit)
            return api_response(True, 200, f"Found {len(results)} matches", {
                "count": len(results),
                "search_mode": sq.mode.value,
                "items": [{
                    "id": r.engram.id,
                    "title": r.engram.title,
                    "source": r.engram.source,
                    "project_name": r.engram.project_name,
                    "score": round(r.score, 3),
                    "matched_fields": r.matched_fields,
                    "snippets": r.match_snippets[:2],
                } for r in results],
            }, request_id, insight="idegraph_search")
        else:
            results = s.search(args_ns.query, project_name=args_ns.project, ide_name=args_ns.ide, limit=args_ns.limit)
            return api_response(True, 200, f"Found {len(results)} matches", {
                "count": len(results),
                "items": [{"id": e.id, "title": e.title, "source": e.source, "project_name": e.project_name} for e in results],
            }, request_id, insight="idegraph_search")


def cmd_ig_get(args_ns: argparse.Namespace) -> Dict:
    request_id = new_request_id()
    with _idegraph_ctx() as (_, s, _):
        e = s.get_by_id(args_ns.id)
        if e is None:
            return api_response(False, 404, f"Memory not found: {args_ns.id}", None, request_id, "IDEGRAPH_404")
        summary_mode = getattr(args_ns, 'summary', False)
        if summary_mode:
            record = e.to_summary_record(request_id=request_id, version="1.0.0")
            return api_response(True, 200, "Memory retrieved (summary)", record, request_id, insight="idegraph_get")
        else:
            record = e.to_export_record(request_id=request_id, version="1.0.0")
            return api_response(True, 200, "Memory retrieved", record, request_id, insight="idegraph_get")


def cmd_ig_list(args_ns: argparse.Namespace) -> Dict:
    request_id = new_request_id()
    with _idegraph_ctx() as (_, _, st):
        items = st.list_memories(
            project_name=args_ns.project, workspace_key=args_ns.workspace_key,
            ide_name=args_ns.ide, limit=args_ns.limit, offset=args_ns.offset,
        )
        return api_response(True, 200, f"Returned {len(items)} memories", {"items": items}, request_id, insight="idegraph_list")


def cmd_ig_ingest(args_ns: argparse.Namespace) -> Dict:
    request_id = new_request_id()
    with _idegraph_ctx() as (sc, _, _):
        path = sc.ingest_all_to_jsonl(request_id=request_id)
        summary = sc.get_summary()
        return api_response(True, 200, "Ingestion completed", {"output_path": str(path), "summary": summary}, request_id, insight="idegraph_ingest")


def cmd_ig_health(args_ns: argparse.Namespace) -> Dict:
    request_id = new_request_id()
    with _idegraph_ctx() as (_, _, st):
        snap = st.health_snapshot()
        status = "healthy" if snap.get("failed_runs", 0) == 0 else "degraded"
        return api_response(True, 200, status, {"status": status, **snap}, request_id, insight="idegraph_health")


def cmd_ig_stats(args_ns: argparse.Namespace) -> Dict:
    request_id = new_request_id()
    with _idegraph_ctx() as (_, _, st):
        stats = st.ingestion_stats(ide_name=args_ns.ide, since_iso=args_ns.since)
        return api_response(True, 200, "Ingestion stats", stats, request_id, insight="idegraph_stats")


def cmd_ig_compact(args_ns: argparse.Namespace) -> Dict:
    request_id = new_request_id()
    from src.modules.idegraph.services.compact import Compact
    with _idegraph_ctx() as (_, s, _):
        compactor = Compact()
        engrams = s.search("", limit=args_ns.limit)
        results = []
        for e in engrams[:args_ns.limit]:
            text = "\n".join(f"### {m.role.upper()}\n{(m.content or '')[:2000]}" for m in e.messages[:30])
            record = compactor.compact(text, e.title or e.source)
            if record:
                results.append({"id": e.id, "goal": record.get("goal", "?")[:80]})
        return api_response(True, 200, f"Compacted {len(results)} conversations", {"results": results, "total": len(results)}, request_id, insight="idegraph_compact")


def cmd_ig_workspace(args_ns: argparse.Namespace) -> Dict:
    request_id = new_request_id()
    with _idegraph_ctx() as (_, _, st):
        ws = st.get_workspace(workspace_key=args_ns.workspace_key)
        if ws is None:
            return api_response(False, 404, f"Workspace not found: {args_ns.workspace_key}", None, request_id, "IDEGRAPH_404")
        return api_response(True, 200, "Workspace found", ws, request_id, insight="idegraph_workspace")


def cmd_ig_refresh(args_ns: argparse.Namespace) -> Dict:
    request_id = new_request_id()
    with _idegraph_ctx() as (sc, _, st):
        result = sc.refresh_project(project_path=args_ns.project_path, force=args_ns.force)
        health = st.health_snapshot()
        return api_response(True, 200, "Project refreshed", {"result": result, "storage": health}, request_id, insight="idegraph_refresh")


def cmd_ig_harvest(args_ns: argparse.Namespace) -> Dict:
    request_id = new_request_id()
    with _idegraph_ctx() as (_, _, st):
        from src.modules.idegraph.services.ide_harvest import IdeHarvest
        from src.modules.idegraph.core.orchestrator import SideCortexOrchestrator
        harvester = IdeHarvest(st)
        totals = {"ides": 0, "configs": 0, "extensions": 0, "settings": 0}
        orch = SideCortexOrchestrator()
        for parser in orch.parsers:
            try:
                installations = parser.find_installations()
                counts = harvester.harvest_installations(
                    ide_name=parser.ide_name, ide_type="vscode-extension",
                    installations=list(installations), request_id=request_id,
                )
                totals["ides"] += 1
                totals["configs"] += counts.get("configurations_upserted", 0)
                totals["extensions"] += counts.get("ide_extensions_upserted", 0)
                totals["settings"] += counts.get("ide_settings_upserted", 0)
            except Exception:
                pass
        return api_response(True, 200, "Harvest completed", totals, request_id, insight="idegraph_harvest")


IG_COMMANDS = {
    "search": cmd_ig_search,
    "get": cmd_ig_get,
    "list": cmd_ig_list,
    "ingest": cmd_ig_ingest,
    "refresh": cmd_ig_refresh,
    "health": cmd_ig_health,
    "stats": cmd_ig_stats,
    "compact": cmd_ig_compact,
    "workspace": cmd_ig_workspace,
    "harvest": cmd_ig_harvest,
}


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("idegraph", aliases=["ig"], help="Cross-IDE memory harvesting")
    sp = p.add_subparsers(dest="ig_action", required=True)

    search_parser = sp.add_parser("search", help="Search memories")
    search_parser.add_argument("query", help="Search keyword. Supports: *.py (glob), /auth.* /i (regex), ~auth~ (fuzzy), auth AND oauth (boolean), title:auth (field prefix)")
    search_parser.add_argument("--project", help="Filter by project name")
    search_parser.add_argument("--ide", help="Filter by IDE name")
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument("--search-mode", choices=["keyword", "glob", "regex", "fuzzy", "boolean"], help="Search mode (default: keyword)")
    search_parser.add_argument("--search-fields", help="Comma-separated fields: all, title, content, code, diffs, tools, source, project")
    search_parser.add_argument("--date-from", help="ISO timestamp filter (inclusive)")
    search_parser.add_argument("--date-to", help="ISO timestamp filter (inclusive)")
    search_parser.add_argument("--min-messages", type=int, help="Minimum message count")
    search_parser.add_argument("--max-messages", type=int, help="Maximum message count")

    get_parser = sp.add_parser("get", help="Get memory by ID")
    get_parser.add_argument("id", help="Memory ID")
    get_parser.add_argument("--summary", action="store_true", help="Return summary without full messages (token efficient)")

    lp = sp.add_parser("list", help="List memories")
    lp.add_argument("--project", help="Filter by project name")
    lp.add_argument("--workspace-key", help="Filter by workspace key")
    lp.add_argument("--ide", help="Filter by IDE name")
    lp.add_argument("--limit", type=int, default=20)
    lp.add_argument("--offset", type=int, default=0)

    sp.add_parser("ingest", help="Run all IDE parsers")

    refp = sp.add_parser("refresh", help="Re-ingest a specific project path")
    refp.add_argument("project_path", help="Project path to refresh")
    refp.add_argument("--force", action="store_true", help="Force re-ingestion")

    sp.add_parser("health", help="Check DB health")

    statp = sp.add_parser("stats", help="Ingestion statistics")
    statp.add_argument("--ide", help="Filter by IDE name")
    statp.add_argument("--since", help="ISO timestamp filter")

    cp = sp.add_parser("compact", help="Compact conversations via LLM")
    cp.add_argument("--limit", type=int, default=5)

    wp = sp.add_parser("workspace", help="Get workspace details")
    wp.add_argument("workspace_key", help="Workspace key hash")

    sp.add_parser("harvest", help="Harvest IDE configs and artifacts")
