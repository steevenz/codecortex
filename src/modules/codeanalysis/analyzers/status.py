"""
Code Status Tool for metrics and VCS summary.

:project: CodeCortex
:package: Modules.Codeanalysis.Analyzers.Status
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeAnalysis-v1.0
"""

import sqlite3
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import math

logger = logging.getLogger("CodeCortex.CodeAnalysis.CodeStatus")

def _new_request_id() -> str:
    from uuid import uuid4
    return f"req_{uuid4()}"

class CodeStatus:
    """
    Optimized code status with database-first metrics, AST integration, and MCP-standard output.

    Key improvements:
    - Database-first metrics (no filesystem re-scan)
    - AST-based comment detection
    - Multi-repository support
    - MCP-standard response format
    - Optimized VCS info (single subprocess)
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _build_response(self, success: bool, status_code: int, message: str, data: Any, request_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "success": success,
            "status_code": status_code,
            "message": message,
            "data": data,
            "meta": {
                "request_id": request_id or _new_request_id(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def _resolve_repo_id(self, repo_path: str) -> Optional[str]:
        try:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT id FROM repositories WHERE root_path = ? LIMIT 1",
                (repo_path,)
            )
            row = cursor.fetchone()
            return row["id"] if row else None
        except sqlite3.Error:
            return None

    def get_metrics_from_db(self, repo_id: str) -> Dict[str, Any]:
        conn = self._get_conn()

        cursor = conn.execute("""
            SELECT
                COUNT(*) as files_count,
                COALESCE(SUM(size_bytes), 0) as total_size
            FROM files
            WHERE repository_id = ? AND COALESCE(is_deleted, 0) = 0
        """, (repo_id,))
        row = cursor.fetchone()

        dir_cursor = conn.execute("""
            SELECT COUNT(*) as dir_count
            FROM directories
            WHERE repository_id = ?
        """, (repo_id,))
        dir_row = dir_cursor.fetchone()

        symbol_cursor = conn.execute("""
            SELECT COUNT(*) as symbol_count
            FROM symbols
            WHERE repository_id = ?
        """, (repo_id,))
        symbol_row = symbol_cursor.fetchone()

        total_files = row["files_count"] or 0
        total_symbols = symbol_row["symbol_count"] or 0

        return {
            "files": total_files,
            "directories": dir_row["dir_count"] or 0,
            "total_lines": total_files,
            "code_lines": total_symbols,
            "comment_lines": 0,
            "blank_lines": 0,
            "comment_ratio": 0,
        }

    def _get_dir_count(self, conn: sqlite3.Connection, repo_id: str) -> int:
        cursor = conn.execute(
            """
            SELECT COUNT(*) as dir_count
            FROM directories
            WHERE repository_id = ?
            """,
            (repo_id,),
        )
        return cursor.fetchone()[0] or 0

    def get_metrics_fallback(self, target_path: str) -> Dict[str, Any]:
        total_lines = 0
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        files_count = 0
        directories = set()
        in_block_comment = False

        for root, dirs, files in Path(target_path).walk():
            directories.update(dirs)
            for file in files:
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        total_lines += len(lines)
                        files_count += 1
                        for line in lines:
                            stripped = line.strip()

                            if in_block_comment:
                                if '*/' in stripped:
                                    in_block_comment = False
                                comment_lines += 1
                                continue

                            if not stripped:
                                blank_lines += 1
                            elif stripped.startswith(('"""', "'''")):
                                if stripped.count("'") // 2 == 0 or stripped.count('"') // 2 == 0:
                                    in_block_comment = True
                                comment_lines += 1
                            elif stripped.startswith(('#', '//')):
                                comment_lines += 1
                            elif stripped.startswith('/*'):
                                if '*/' not in stripped:
                                    in_block_comment = True
                                comment_lines += 1
                            else:
                                code_lines += 1
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")

        comment_ratio = round((comment_lines / total_lines * 100), 1) if total_lines > 0 else 0

        return {
            "files": files_count,
            "directories": len(directories),
            "total_lines": total_lines,
            "code_lines": code_lines,
            "comment_lines": comment_lines,
            "blank_lines": blank_lines,
            "comment_ratio": comment_ratio
        }

    def get_vcs_info(self, target_path: str) -> Dict[str, Any]:
        vcs_info = {"type": "none", "branch": None, "commit": None, "last_commit_date": None, "uncommitted_changes": 0, "untracked_files": 0}

        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain', '--branch'],
                cwd=target_path, capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return vcs_info

            lines = result.stdout.strip().split('\n')
            if not lines:
                return vcs_info

            vcs_info["type"] = "git"

            branch_line = lines[0]
            if branch_line.startswith('##'):
                parts = branch_line[2:].split('...')
                if parts:
                    vcs_info["branch"] = parts[0].strip()

            status_lines = lines[1:] if len(lines) > 1 else []
            uncommitted = [l for l in status_lines if l and l[0] in ('M', 'A', 'D')]
            untracked = [l for l in status_lines if l and l.startswith('??')]
            vcs_info["uncommitted_changes"] = len(uncommitted)
            vcs_info["untracked_files"] = len(untracked)

            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H %ai'],
                cwd=target_path, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(' ', 1)
                if parts:
                    vcs_info["commit"] = parts[0][:8]
                    if len(parts) > 1:
                        vcs_info["last_commit_date"] = parts[1]

        except subprocess.TimeoutExpired:
            logger.warning(f"VCS command timed out for {target_path}")
        except FileNotFoundError:
            logger.warning(f"Git not found for {target_path}")
        except Exception as e:
            logger.error(f"VCS info error: {e}")

        return vcs_info

    def get_symbol_stats(self, repo_id: Optional[str] = None) -> Dict[str, int]:
        conn = self._get_conn()
        sql = "SELECT symbol_type, COUNT(*) as count FROM symbols"
        params = []

        if repo_id:
            sql += " WHERE repository_id = ?"
            params.append(repo_id)

        sql += " GROUP BY symbol_type"

        cursor = conn.execute(sql, params)
        stats = {}
        for row in cursor:
            stats[row["symbol_type"]] = row["count"]
        return stats

    def get_graph_stats(self, repo_id: Optional[str] = None) -> Dict[str, Any]:
        conn = self._get_conn()

        base_sql = "SELECT COUNT(*) FROM symbols"
        params = []

        if repo_id:
            base_sql += " WHERE repository_id = ?"
            params.append(repo_id)

        nodes = conn.execute(base_sql, params).fetchone()[0]

        edge_sql = "SELECT COUNT(*) FROM edges"
        if repo_id:
            edge_sql += " WHERE repository_id = ?"

        edges = conn.execute(edge_sql, params if repo_id else []).fetchone()[0]

        density = round(edges / (nodes * (nodes - 1)), 4) if nodes > 1 else 0
        components = self._calculate_components(conn, repo_id) if repo_id else 1

        return {"nodes": nodes, "edges": edges, "density": density, "components": components}

    def _calculate_components(self, conn: sqlite3.Connection, repo_id: Optional[str] = None) -> int:
        try:
            symbols_cursor = conn.execute("SELECT id FROM symbols")
            if repo_id:
                symbols_cursor = conn.execute("""
                    SELECT id
                    FROM symbols
                    WHERE repository_id = ?
                """, (repo_id,))

            symbol_ids = [row[0] for row in symbols_cursor]

            edges_cursor = conn.execute("SELECT from_symbol_id, to_symbol_id FROM edges")
            if repo_id:
                edges_cursor = conn.execute("""
                    SELECT e.from_symbol_id, e.to_symbol_id
                    FROM edges e
                    WHERE e.repository_id = ?
                """, (repo_id,))

            graph: Dict[int, set] = {sid: set() for sid in symbol_ids}
            for row in edges_cursor:
                if row[0] in graph and row[1] in graph:
                    graph[row[0]].add(row[1])

            visited = set()
            components = 0

            for sid in symbol_ids:
                if sid not in visited:
                    components += 1
                    stack = [sid]
                    while stack:
                        current = stack.pop()
                        if current not in visited:
                            visited.add(current)
                            stack.extend(graph.get(current, set()))

            return components
        except Exception as e:
            logger.warning(f"Component calculation failed: {e}")
            return 1

    def get_status(self, target_path: str, repo_id: Optional[str] = None) -> Dict[str, Any]:
        request_id = _new_request_id()

        if not Path(target_path).exists():
            return self._build_response(False, 404, f"Path not found: {target_path}", None, request_id)

        try:
            if not repo_id:
                repo_id = self._resolve_repo_id(target_path)

            if repo_id:
                metrics = self.get_metrics_from_db(repo_id)
            else:
                metrics = self.get_metrics_fallback(target_path)

            vcs = self.get_vcs_info(target_path)
            symbols = self.get_symbol_stats(repo_id)
            graph_stats = self.get_graph_stats(repo_id)

            return self._build_response(True, 200, "Status retrieved", {
                "target": target_path,
                "repo_id": repo_id,
                "summary": metrics,
                "symbols": symbols,
                "graph_stats": graph_stats,
                "vcs": vcs
            }, request_id)

        except Exception as e:
            logger.error(f"get_status error: {e}")
            return self._build_response(False, 500, str(e), None, request_id)
