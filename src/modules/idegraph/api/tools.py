"""
@project   CodeCortex
@package   modules.idegraph.api
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.api
:standard: Aegis-IdeGraph-v1.0

MCP Tools for IDE Graph — 1 unified tool with 10 actions.

codecortex:idegraph
  ├── search     — Search memories/conversations
  ├── get        — Get single memory by ID
  ├── list       — List memories, workspaces, or projects
  ├── ingest     — Trigger full ingestion
  ├── refresh    — Refresh a specific project's data
  ├── health     — Health check
  ├── stats      — Ingestion statistics
  ├── compact    — Compact conversation with local LLM
  ├── workspace  — Get/set workspace details
  └── harvest    — Harvest IDE configs and artifacts
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Context
from mcp.types import ToolAnnotations
from src.core import api_response, new_request_id
from src.core.insight import generate_insight


def _build_tools(mcp: FastMCP, orchestrator_factory: Callable) -> None:

    @mcp.tool(
        annotations=ToolAnnotations(
            title="CodeCortex IDE Graph",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def idegraph(
        ctx: Context,
        action: str,
        query: Optional[str] = None,
        memory_id: Optional[str] = None,
        project_path: Optional[str] = None,
        project_name: Optional[str] = None,
        workspace_key: Optional[str] = None,
        workspace_id: Optional[str] = None,
        ide_name: Optional[str] = None,
        source: Optional[str] = None,
        focus: Optional[str] = None,
        force: bool = False,
        since: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        include_engram_count: bool = True,
        summary_mode: bool = False,
        search_mode: Optional[str] = None,
        search_fields: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_messages: Optional[int] = None,
        max_messages: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        IDE Graph — search, ingest, and explore cross-IDE memories and configurations.

        @param action: Operation to perform:
          - search: Search memories by keyword (query required)
          - get: Get single memory by ID (memory_id required)
          - list: List memories. Use project_name, workspace_key, ide_name filters.
          - ingest: Run all IDE parsers and persist results.
          - refresh: Re-ingest a specific project path (project_path required).
          - health: Database health check.
          - stats: Ingestion statistics by IDE.
          - compact: Run LLM compaction on recent memories (limit).
          - workspace: Get workspace details (workspace_key required).
          - harvest: Harvest IDE configs/settings/extensions.
        @param query: Search keyword (required for search action). Supports:
          - Glob: `*.py`, `src/**`
          - Regex: `/auth.* /i`
          - Fuzzy: `~auth~`
          - Boolean: `auth AND oauth NOT facebook`
          - Field prefix: `title:auth`, `code:def validate`, `source:*.py`
        @param memory_id: Memory ID (required for get action).
        @param project_path: Repository path (required for refresh).
        @param project_name: Filter by project name.
        @param workspace_key: Filter by workspace key hash.
        @param workspace_id: Alias for workspace_key.
        @param ide_name: Filter by IDE name (cursor, trae, claude, etc.).
        @param source: Filter by source file path substring.
        @param focus: Focus topic for compaction summary.
        @param force: Force re-ingestion (default false).
        @param since: ISO timestamp filter for stats.
        @param limit: Max results (default 20, max 200).
        @param offset: Offset for pagination (default 0).
        @param include_engram_count: Include engram counts in list (default true).
        @param summary_mode: Return summary without full messages (default false).
        @param search_mode: Search mode: keyword (default), glob, regex, fuzzy, boolean.
        @param search_fields: Comma-separated fields: all, title, content, code, diffs, tools, source, project.
        @param date_from: ISO timestamp filter (inclusive) for search.
        @param date_to: ISO timestamp filter (inclusive) for search.
        @param min_messages: Minimum message count filter.
        @param max_messages: Maximum message count filter.
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        if hasattr(ctx, "info"): await ctx.info(f"idegraph.{action} started")
        from src.modules.idegraph.services.sidecortex import SideCortex
        from src.modules.idegraph.services.storage import Storage
        from src.modules.idegraph.services.search import Search
        from src.modules.idegraph.services.search_engine import SearchEngine, SearchQuery, SearchMode, SearchField

        sidecortex = SideCortex(db=orchestrator.db)
        search = Search(db=orchestrator.db)
        storage = Storage(db=orchestrator.db)
        search_engine = SearchEngine(db=orchestrator.db)
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))

        try:
            if action == "search":
                q = query
                if not q:
                    return api_response(False, 400, "query is required for search", None, request_id, "IDEGRAPH_001")
                if memory_id:
                    return _handle_get(request_id, search, memory_id)

                # Use enhanced search engine when search_mode or advanced params provided
                use_enhanced = bool(search_mode or search_fields or date_from or date_to or min_messages or max_messages)

                if use_enhanced:
                    sq = search_engine.explain_query(q)
                    if search_mode:
                        try:
                            sq.mode = SearchMode(search_mode.lower())
                        except ValueError:
                            pass
                    if search_fields:
                        sq.fields = []
                        for f in search_fields.split(","):
                            f = f.strip().lower()
                            try:
                                sq.fields.append(SearchField(f))
                            except ValueError:
                                pass
                        if not sq.fields:
                            sq.fields = [SearchField.ALL]
                    if date_from:
                        try:
                            from datetime import datetime as dt_parse
                            sq.date_from = dt_parse.fromisoformat(date_from.replace("Z", "+00:00"))
                        except Exception:
                            pass
                    if date_to:
                        try:
                            from datetime import datetime as dt_parse
                            sq.date_to = dt_parse.fromisoformat(date_to.replace("Z", "+00:00"))
                        except Exception:
                            pass
                    if min_messages is not None:
                        sq.min_messages = min_messages
                    if max_messages is not None:
                        sq.max_messages = max_messages
                    sq.project_name = project_name
                    sq.ide_name = ide_name
                    sq.workspace_key = workspace_key or workspace_id

                    results = search_engine.search(sq, limit=limit)
                    items = []
                    for r in results:
                        e = r.engram
                        wk = e.compute_workspace_key(
                            project_path=e.project_path,
                            project_name=e.project_name,
                            workspace_id=e.workspace_id,
                            source_file=e.source_file,
                        )
                        item = {
                            "id": e.id, "title": e.title, "source": e.source,
                            "project_name": e.project_name, "workspace_key": wk,
                            "created_at": e.created_at.isoformat(),
                            "score": round(r.score, 3),
                            "matched_fields": r.matched_fields,
                            "snippets": r.match_snippets[:3],
                        }
                        items.append(item)
                    return api_response(True, 200, f"Found {len(items)} matches", {
                        "items": items, "count": len(items),
                        "search_mode": sq.mode.value,
                        "query": sq.raw,
                    }, request_id, insight="idegraph_search")
                else:
                    # Legacy search path
                    results = search.search(q, project_name=project_name, ide_name=ide_name, limit=limit)
                    resolved_key = workspace_key or workspace_id
                    filtered = []
                    for e in results:
                        wk = e.compute_workspace_key(
                            project_path=e.project_path,
                            project_name=e.project_name,
                            workspace_id=e.workspace_id,
                            source_file=e.source_file,
                        )
                        if resolved_key and wk != resolved_key:
                            continue
                        if source and source.lower() not in (e.source_file or "").lower():
                            continue
                        filtered.append(e)
                    items = []
                    for e in filtered:
                        wk = e.compute_workspace_key(
                            project_path=e.project_path,
                            project_name=e.project_name,
                            workspace_id=e.workspace_id,
                            source_file=e.source_file,
                        )
                        items.append({
                            "id": e.id, "title": e.title, "source": e.source,
                            "project_name": e.project_name, "workspace_key": wk,
                            "created_at": e.created_at.isoformat(),
                        })
                    return api_response(True, 200, f"Found {len(items)} matches", {
                        "items": items, "count": len(items),
                    }, request_id, insight="idegraph_search")

            elif action == "get":
                if not memory_id:
                    return api_response(False, 400, "memory_id is required for get", None, request_id, "IDEGRAPH_002")
                return _handle_get(request_id, search, memory_id, summary_mode)

            elif action == "list":
                items = storage.list_memories(
                    project_name=project_name, workspace_key=workspace_key or workspace_id,
                    ide_name=ide_name, limit=limit, offset=offset,
                )
                return api_response(True, 200, f"Returned {len(items)} memories", {
                    "items": items, "limit": limit, "offset": offset,
                }, request_id, insight="idegraph_list")

            elif action == "ingest":
                output_path = sidecortex.ingest_all_to_jsonl(request_id=request_id)
                summary = sidecortex.get_summary()
                health = storage.health_snapshot()
                return api_response(True, 200, "Ingestion completed", {
                    "output_path": str(output_path), "summary": summary, "storage": health,
                }, request_id, insight="idegraph_ingest")

            elif action == "refresh":
                if not project_path:
                    return api_response(False, 400, "project_path is required for refresh", None, request_id, "IDEGRAPH_003")
                result = sidecortex.refresh_project(project_path=project_path, force=force)
                health = storage.health_snapshot()
                return api_response(True, 200, "Project refreshed", {
                    "result": result, "storage": health,
                }, request_id, insight="idegraph_refresh")

            elif action == "health":
                snapshot = storage.health_snapshot()
                status = "healthy" if snapshot.get("failed_runs", 0) == 0 else "degraded"
                return api_response(True, 200, status, {"status": status, **snapshot},
                                    request_id, insight="idegraph_health")

            elif action == "stats":
                since_iso = None
                if since:
                    from datetime import datetime
                    try:
                        datetime.fromisoformat(since.replace("Z", "+00:00"))
                        since_iso = since
                    except Exception:
                        pass
                stats = storage.ingestion_stats(ide_name=ide_name, since_iso=since_iso)
                return api_response(True, 200, "Ingestion stats", stats, request_id, insight="idegraph_stats")

            elif action == "compact":
                from src.modules.idegraph.services.compact import Compact
                compactor = Compact()
                results = []
                engrams = search.search("", limit=limit)
                for e in engrams[:limit]:
                    text = _format_engram(e)
                    record = compactor.compact(text, e.title or e.source)
                    if record:
                        results.append({"id": e.id, "goal": record.get("goal", "?")[:80]})
                return api_response(True, 200, f"Compacted {len(results)} conversations", {
                    "results": results, "total": len(results),
                }, request_id, insight="idegraph_compact")

            elif action == "workspace":
                wk = workspace_key or workspace_id
                if not wk:
                    return api_response(False, 400, "workspace_key is required for workspace", None, request_id, "IDEGRAPH_004")
                ws = storage.get_workspace(workspace_key=wk)
                if ws is None:
                    return api_response(False, 404, f"Workspace not found: {wk}", None, request_id, "IDEGRAPH_005")
                return api_response(True, 200, "Workspace found", ws, request_id, insight="idegraph_workspace")

            elif action == "harvest":
                from src.modules.idegraph.services.ide_harvest import IdeHarvest
                harvester = IdeHarvest(storage)
                totals = {"ides": 0, "configs": 0, "extensions": 0, "settings": 0}
                from src.modules.idegraph.core.orchestrator import SideCortexOrchestrator
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

            elif action == "store_session":
                from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
                from datetime import datetime as _dt
                import uuid as _uuid

                session_id_val = args.get("session_id") or str(_uuid.uuid4())
                title = args.get("title") or args.get("problem_statement", "")[:80] or "Neocortex Session"
                problem = args.get("problem_statement", "")
                thoughts = args.get("thoughts") or []
                repo_path = args.get("repo_path", "")
                model = args.get("model", "unknown")
                source = args.get("source", "neocortex")
                duration_ms = args.get("duration_ms", 0)
                project_name = args.get("project_name") or (repo_path.split("/")[-1] if repo_path else "default")

                # Build messages: first message is the problem statement,
                # subsequent messages are thought steps (user=LLM input, assistant=LLM output)
                messages = [Message(
                    role="user",
                    content=problem or title,
                    timestamp=_dt.now().isoformat(),
                    metadata={"type": "problem_statement"},
                )]
                for i, thought in enumerate(thoughts):
                    if not isinstance(thought, dict):
                        continue
                    content = thought.get("content") or thought.get("summary") or str(thought)[:500]
                    strategy = thought.get("strategy", "")
                    thought_num = thought.get("thought_number", i + 1)
                    messages.append(Message(
                        role="assistant",
                        content=content,
                        timestamp=thought.get("timestamp") or _dt.now().isoformat(),
                        metadata={
                            "type": "thinking_step",
                            "strategy": strategy,
                            "thought_number": thought_num,
                            "session_id": session_id_val,
                        },
                    ))
                if duration_ms:
                    messages.append(Message(
                        role="assistant",
                        content=f"Session completed. Duration: {duration_ms}ms. Thoughts: {len(thoughts)}.",
                        timestamp=_dt.now().isoformat(),
                        metadata={"type": "session_summary", "duration_ms": duration_ms},
                    ))

                engram = Engram(
                    id=f"neocortex_{session_id_val}",
                    source=source,
                    source_file=f"neocortex://session/{session_id_val}",
                    messages=messages,
                    created_at=_dt.now(),
                    project_path=repo_path or None,
                    project_name=project_name,
                    title=title,
                    model=model,
                    metadata={
                        "session_id": session_id_val,
                        "problem_statement": problem[:300] if problem else "",
                        "repo_path": repo_path,
                        "thought_count": len(thoughts),
                        "duration_ms": duration_ms,
                        "source": source,
                    },
                    ide_info=IDEInfo(name=source, type="mcp-server"),
                )
                counts = storage.persist_engrams([engram], request_id=request_id)
                return api_response(True, 200, "Session stored in IDEGraph", {
                    "engram_id": engram.id,
                    "session_id": session_id_val,
                    "message_count": len(messages),
                    "storage": counts,
                }, request_id, insight="idegraph_store_session")

            else:
                return api_response(False, 400,
                    f"Unknown action: {action}. Use: search, get, list, ingest, refresh, health, stats, compact, workspace, harvest, store_session",
                    None, request_id, "IDEGRAPH_006")

        except Exception as e:
            return api_response(False, 500, f"idegraph failed: {e}", None, request_id, "IDEGRAPH_500")
        finally:
            try:
                orchestrator.db.close()
            except Exception:
                pass


def _handle_get(request_id: str, search, memory_id: str, summary_mode: bool = False) -> Dict[str, Any]:
    """Get single memory by ID with standardized response."""
    engram = search.get_by_id(memory_id)
    if engram is None:
        return api_response(False, 404, f"Memory not found: {memory_id}", None, request_id, "IDEGRAPH_404")
    if summary_mode:
        record = engram.to_summary_record(request_id=request_id, version="1.0.0")
    else:
        record = engram.to_export_record(request_id=request_id, version="1.0.0")
    return api_response(True, 200, "Memory retrieved" + (" (summary)" if summary_mode else ""), record, request_id, insight="idegraph_get")


def _format_engram(e) -> str:
    """Format an Engram to text for compaction."""
    parts = []
    for m in e.messages[:30]:
        parts.append(f"### {m.role.upper()}")
        content = (m.content or "")[:2000]
        parts.append(content)
    if len(e.messages) > 30:
        parts.append(f"... ({len(e.messages) - 30} more)")
    return "\n".join(parts)


def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    _build_tools(mcp, orchestrator_factory)
