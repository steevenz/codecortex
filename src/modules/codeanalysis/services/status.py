"""
Class Status – Single Responsibility: Code metrics + VCS status.

:project: CodeCortex
:package: Modules.Codeanalysis.Services.Status
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeAnalysis-v1.0
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from src.core.database import DatabaseManager
from src.core.logging import get_logger
from src.modules.codeanalysis.core.dtos import (
    StatusRequest, StatusResult, MetricsInfo, VcsInfo, GraphStatsInfo,
)

logger = get_logger("CodeCortex.CodeAnalysis.StatusService")

class Status:
    """
    Code metrics + VCS status aggregation.
    DI: all dependencies injected via constructor.
    """

    def __init__(self, db: DatabaseManager):
        self._db = db

    def get_status(self, request: StatusRequest) -> StatusResult:
        target = Path(request.path)
        if not target.exists():
            raise FileNotFoundError(f"Path does not exist: {request.path}")

        repo_id = request.repo_id or self._resolve_repo_id(request.path)

        metrics = None
        if request.include_metrics:
            if repo_id:
                metrics = self._get_metrics_from_db(repo_id)
                self._populate_index_cache(repo_id, metrics, symbols={} if not request.include_symbols else {})
            else:
                metrics = self._get_metrics_fallback(target)

        vcs = None
        if request.include_vcs:
            vcs = self._get_vcs_info(target)

        symbols = {}
        if request.include_symbols:
            symbols = self._get_symbol_stats(repo_id)

        graph_stats = self._get_graph_stats(repo_id) if repo_id else GraphStatsInfo()

        return StatusResult(
            target=request.path,
            repo_id=repo_id,
            summary=metrics,
            symbols=symbols,
            graph_stats=graph_stats,
            vcs=vcs,
        )

    def _resolve_repo_id(self, path: str) -> Optional[str]:
        with self._db.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM repositories WHERE root_path = ? LIMIT 1", (path,)
            ).fetchone()
            return row["id"] if row else None

    def _get_metrics_from_db(self, repo_id: str) -> MetricsInfo:
        with self._db.get_connection() as conn:
            file_row = conn.execute(
                """
                SELECT COUNT(*) AS files, COALESCE(SUM(size_bytes), 0) AS total_size
                FROM files
                WHERE repository_id = ? AND COALESCE(is_deleted, 0) = 0
                """,
                (repo_id,),
            ).fetchone()
            dir_row = conn.execute(
                "SELECT COUNT(*) AS directories FROM directories WHERE repository_id = ?",
                (repo_id,),
            ).fetchone()
            symbol_row = conn.execute(
                "SELECT COUNT(*) AS symbols FROM symbols WHERE repository_id = ?",
                (repo_id,),
            ).fetchone()

        files = file_row["files"] or 0
        directories = dir_row["directories"] or 0
        code_lines = symbol_row["symbols"] or 0
        return MetricsInfo(
            files=files,
            directories=directories,
            total_lines=files,
            code_lines=code_lines,
            comment_lines=0,
            blank_lines=0,
            comment_ratio=0.0,
            languages={},
        )

    def _get_metrics_fallback(self, target: Path) -> MetricsInfo:
        total_lines = 0
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        files_count = 0
        languages = {}

        for fp in target.rglob("*"):
            if fp.is_file():
                try:
                    text = fp.read_text(encoding="utf-8", errors="replace")
                    total_lines += len(text.splitlines())
                    files_count += 1
                    ext = fp.suffix
                    languages[ext] = languages.get(ext, 0) + 1
                except Exception:
                    pass

        return MetricsInfo(
            files=files_count,
            total_lines=total_lines,
            code_lines=total_lines - blank_lines - comment_lines,
            languages=languages,
        )

    def _get_vcs_info(self, target: Path) -> VcsInfo:
        info = VcsInfo()
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain', '--branch'],
                cwd=str(target), capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                info.type = "git"
                lines = result.stdout.strip().split('\n')
                if lines and lines[0].startswith('##'):
                    parts = lines[0][2:].split('...')
                    info.branch = parts[0].strip() if parts else None
                status_lines = lines[1:] if len(lines) > 1 else []
                info.uncommitted_changes = sum(1 for l in status_lines if l and l[0] in ('M', 'A', 'D'))
                info.untracked_files = sum(1 for l in status_lines if l and l.startswith('??'))

                log_result = subprocess.run(
                    ['git', 'log', '-1', '--format=%H %ai'],
                    cwd=str(target), capture_output=True, text=True, timeout=10
                )
                if log_result.returncode == 0 and log_result.stdout.strip():
                    parts = log_result.stdout.strip().split(' ', 1)
                    info.commit = parts[0][:8]
                    info.last_commit_date = parts[1] if len(parts) > 1 else None
        except Exception:
            pass
        return info

    def _get_symbol_stats(self, repo_id: Optional[str]) -> Dict[str, int]:
        with self._db.get_connection() as conn:
            sql = "SELECT symbol_type, COUNT(*) FROM symbols"
            params = []
            if repo_id:
                sql += " WHERE repository_id = ?"
                params.append(repo_id)
            sql += " GROUP BY symbol_type"
            return {r[0]: r[1] for r in conn.execute(sql, params).fetchall()}

    def _get_graph_stats(self, repo_id: str) -> GraphStatsInfo:
        with self._db.get_connection() as conn:
            nodes = conn.execute(
                "SELECT COUNT(*) FROM symbols WHERE repository_id = ?",
                (repo_id,),
            ).fetchone()[0]
            try:
                edges = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM edges
                    JOIN symbols s1 ON edges.from_symbol_id = s1.id
                    WHERE s1.repository_id = ?
                    """,
                    (repo_id,),
                ).fetchone()[0]
            except Exception:
                edges = 0

        density = round(edges / (nodes * (nodes - 1)), 4) if nodes > 1 else 0.0
        return GraphStatsInfo(nodes=nodes, edges=edges, density=density, components=1)

    def _populate_index_cache(self, repo_id: str, metrics: MetricsInfo,
                              symbols: Dict[str, int]) -> None:
        try:
            from src.core.database.index_cache import IndexCache
            cache = IndexCache(self._db)
            stats = {
                "files": metrics.files,
                "directories": metrics.directories,
                "total_lines": metrics.total_lines,
                "code_lines": metrics.code_lines,
                "comment_ratio": metrics.comment_ratio,
                "languages": metrics.languages,
                "symbols": symbols,
            }
            cache.set_stats(repo_id, stats)
        except Exception:
            pass
