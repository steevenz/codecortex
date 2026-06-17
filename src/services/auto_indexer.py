"""
Auto-Indexer Service — runs repo sync, code indexing, and graph build on demand.

Triggers:
  1. First search: symbols table empty → auto-index
  2. Stale data: sync_at older than TTL → auto-update
  3. Manual: force_update/regraph/reindex params via CLI/MCP/API

TTL configuration:
  CODECORTEX_INDEX_TTL_DAYS=7 (default) — set in .env

:project: CodeCortex
:package: Services.AutoIndexer
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
"""
from __future__ import annotations
import os
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("CodeCortex.AutoIndexer")


def _get_ttl_days() -> int:
    """Get TTL from env or default 7 days."""
    raw = os.getenv("CODECORTEX_INDEX_TTL_DAYS", "7")
    try:
        return max(1, int(raw))
    except (ValueError, TypeError):
        return 7


class IndexStatus:
    """Describes the current index state for a repo path."""

    def __init__(self, indexed: bool = False, fresh: bool = False,
                 symbols_count: int = 0, last_sync: Optional[str] = None,
                 ttl_days: int = 7, needs_update: bool = False):
        self.indexed = indexed
        self.fresh = fresh
        self.symbols_count = symbols_count
        self.last_sync = last_sync
        self.ttl_days = ttl_days
        self.needs_update = needs_update

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indexed": self.indexed,
            "fresh": self.fresh,
            "symbols_count": self.symbols_count,
            "last_sync": self.last_sync,
            "ttl_days": self.ttl_days,
            "needs_update": self.needs_update,
        }


def check_index_status(db: Any, repo_path: Optional[str] = None) -> IndexStatus:
    """Check if a repo is indexed and whether data is stale."""
    ttl_days = _get_ttl_days()
    symbols_count = 0
    last_sync = None

    try:
        row = db.conn.execute("SELECT COUNT(*) FROM symbols").fetchone()
        symbols_count = row[0] if row else 0
    except Exception:
        pass

    indexed = symbols_count > 0

    # Check sync staleness
    fresh = False
    needs_update = False
    if repo_path:
        try:
            git_root = None
            try:
                import subprocess
                r = subprocess.run(
                    ["git", "-C", repo_path, "rev-parse", "--show-toplevel"],
                    capture_output=True, text=True, timeout=10,
                )
                if r.returncode == 0 and r.stdout.strip():
                    git_root = r.stdout.strip()
            except Exception:
                pass

            if git_root:
                row = db.conn.execute(
                    "SELECT sync_at FROM repositories WHERE root_path = ?",
                    (git_root,),
                ).fetchone()
                if row:
                    last_sync = row[0] if isinstance(row, dict) else row[0]
        except Exception:
            pass

        if last_sync:
            try:
                if isinstance(last_sync, str):
                    sync_dt = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
                else:
                    sync_dt = last_sync
                age_days = (datetime.now(timezone.utc) - sync_dt).days
                fresh = age_days < ttl_days
                needs_update = age_days >= ttl_days
            except Exception:
                fresh = True
        elif indexed:
            # Have symbols but no sync timestamp — assume stale
            needs_update = True

    if not repo_path and indexed:
        fresh = True  # No repo path to check staleness

    return IndexStatus(
        indexed=indexed, fresh=fresh,
        symbols_count=symbols_count, last_sync=last_sync,
        ttl_days=ttl_days, needs_update=needs_update,
    )


async def run_full_index(orchestrator: Any, repo_path: str) -> Dict[str, Any]:
    """Run full index pipeline: sync + analyze + graph build (dry_run=False)."""
    t0 = time.monotonic()
    logger.info("auto-index|starting|path=%s", repo_path)

    result: Dict[str, Any] = {"repo_path": repo_path, "steps": {}}

    try:
        # Step 1: repo sync + AST index
        analysis = await orchestrator.analyze(
            root_path=repo_path,
            dry_run=False,
            request_id=None,
        )
        repo_id = analysis.get("repository_id") or analysis.get("repo_id")
        result["steps"]["sync_and_index"] = {"status": "ok", "repo_id": repo_id}
        logger.info("auto-index|sync_index|repo=%s|ok", repo_id)

        # Step 2: graph build if repo_id exists
        if repo_id:
            try:
                graph_result = await orchestrator.graph_service.build_graph(
                    repo_id=repo_id,
                    detect_modular=True,
                    build_dependency_graph=True,
                )
                result["steps"]["graph_build"] = {"status": "ok"}
                logger.info("auto-index|graph_build|repo=%s|ok", repo_id)
            except Exception as ge:
                result["steps"]["graph_build"] = {"status": "error", "message": str(ge)[:100]}
                logger.warning("auto-index|graph_build|repo=%s|error=%s", repo_id, str(ge)[:80])

        result["success"] = True
    except Exception as e:
        logger.error("auto-index|failed|path=%s|error=%s", repo_path, str(e)[:120])
        result["success"] = False
        result["error"] = str(e)[:200]

    result["elapsed_seconds"] = round(time.monotonic() - t0, 2)
    logger.info("auto-index|complete|path=%s|elapsed=%.1fs", repo_path, result["elapsed_seconds"])
    return result
