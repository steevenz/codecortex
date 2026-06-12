"""
MCP Resources for CodeCortex — structured URIs for repo data.

:project: CodeCortex
:package: Api.Resources
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-API-v1.0
"""

from __future__ import annotations
from typing import Any, Callable
from mcp.server.fastmcp import FastMCP
from mcp.types import Annotations, Resource as MCPResource


def register_resources(mcp: FastMCP, orchestrator_factory: Callable[[], Any]) -> None:
    """
    Register MCP resources for structured data access via codecortex:// URIs.
    """

    @mcp.resource(
        uri="codecortex://repos/{repo_id}/status",
        name="Repository Status",
        description="Quick health summary of an indexed repository",
        mime_type="application/json",
        annotations=Annotations(audience=["assistant"], priority=0.8),
    )
    async def repo_status(repo_id: str) -> dict:
        """Return snapshot: file count, symbol count, last sync, stale flag."""
        orch = orchestrator_factory()
        try:
            row = orch.db.conn.execute(
                "SELECT id, root_path, sync_at, indexed_at FROM repositories WHERE id = ?",
                (repo_id,),
            ).fetchone()
            if not row:
                return {"error": "not_found", "repo_id": repo_id}
            nfiles = orch.db.conn.execute(
                "SELECT COUNT(*) FROM files WHERE repository_id=? AND deleted_at IS NULL",
                (repo_id,),
            ).fetchone()[0]
            nsyms = orch.db.conn.execute(
                "SELECT COUNT(*) FROM symbols WHERE repository_id=?", (repo_id,),
            ).fetchone()[0]
            nedges = orch.db.conn.execute(
                "SELECT COUNT(*) FROM edges WHERE repository_id=?", (repo_id,),
            ).fetchone()[0]
            return {
                "repo_id": row["id"],
                "root_path": row["root_path"],
                "sync_at": row["sync_at"],
                "indexed_at": row["indexed_at"],
                "files": nfiles,
                "symbols": nsyms,
                "dependencies": nedges,
            }
        finally:
            try:
                orch.db.close()
            except Exception:
                pass

    @mcp.resource(
        uri="codecortex://repos/{repo_id}/symbols",
        name="Repository Symbols",
        description="List all indexed symbols for a repository",
        mime_type="application/json",
        annotations=Annotations(audience=["assistant"], priority=0.7),
    )
    async def repo_symbols(repo_id: str) -> dict:
        """Return symbols grouped by type (class, function, etc.)."""
        orch = orchestrator_factory()
        try:
            rows = orch.db.conn.execute(
                "SELECT name, symbol_type, file_path, line_start, line_end, parent_id "
                "FROM symbols WHERE repository_id=? ORDER BY symbol_type, name LIMIT 1000",
                (repo_id,),
            ).fetchall()
            grouped: dict[str, list] = {}
            for r in rows:
                t = r["symbol_type"] or "unknown"
                grouped.setdefault(t, []).append({
                    "name": r["name"],
                    "file": r["file_path"],
                    "line": r["line_start"],
                    "end_line": r["line_end"],
                    "parent": r["parent_id"],
                })
            return {"repo_id": repo_id, "total": len(rows), "grouped": grouped}
        finally:
            try:
                orch.db.close()
            except Exception:
                pass

    @mcp.resource(
        uri="codecortex://repos/{repo_id}/graph",
        name="Repository Graph",
        description="Graph statistics and summary for a repository",
        mime_type="application/json",
        annotations=Annotations(audience=["assistant"], priority=0.7),
    )
    async def repo_graph(repo_id: str) -> dict:
        """Return graph stats: node count, edge count, density, top nodes."""
        orch = orchestrator_factory()
        try:
            nodes = orch.db.conn.execute(
                "SELECT COUNT(*) FROM symbols WHERE repository_id=?", (repo_id,),
            ).fetchone()[0]
            edges = orch.db.conn.execute(
                "SELECT COUNT(*) FROM edges WHERE repository_id=?", (repo_id,),
            ).fetchone()[0]
            top = orch.db.conn.execute(
                "SELECT target_id, COUNT(*) as cnt FROM edges "
                "WHERE repository_id=? GROUP BY target_id ORDER BY cnt DESC LIMIT 10",
                (repo_id,),
            ).fetchall()
            density = (2.0 * edges / (nodes * (nodes - 1))) if nodes > 1 else 0
            return {
                "repo_id": repo_id,
                "nodes": nodes,
                "edges": edges,
                "density": round(density, 6),
                "hub_candidates": [{"symbol_id": r["target_id"], "connections": r["cnt"]} for r in top],
            }
        finally:
            try:
                orch.db.close()
            except Exception:
                pass

    @mcp.resource(
        uri="codecortex://repos/{repo_id}/metrics",
        name="Repository Metrics",
        description="Code quality metrics for a repository",
        mime_type="application/json",
        annotations=Annotations(audience=["assistant"], priority=0.6),
    )
    async def repo_metrics(repo_id: str) -> dict:
        """Return code metrics: LOC, comment ratio, language breakdown."""
        orch = orchestrator_factory()
        try:
            files = orch.db.conn.execute(
                "SELECT language, COUNT(*) as cnt FROM files "
                "WHERE repository_id=? AND deleted_at IS NULL "
                "GROUP BY language ORDER BY cnt DESC",
                (repo_id,),
            ).fetchall()
            loc = orch.db.conn.execute(
                "SELECT COALESCE(SUM(lines), 0) FROM files "
                "WHERE repository_id=? AND deleted_at IS NULL",
                (repo_id,),
            ).fetchone()[0]
            return {
                "repo_id": repo_id,
                "total_loc": loc,
                "languages": {r["language"]: r["cnt"] for r in files},
            }
        finally:
            try:
                orch.db.close()
            except Exception:
                pass
