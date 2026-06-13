"""
Code Search Tool for symbol, semantic, and graph queries.

:project: CodeCortex
:package: Modules.Codeanalysis.Analyzers.Searcher
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeAnalysis-v1.0
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
import re

logger = logging.getLogger("CodeCortex.CodeAnalysis.CodeSearcher")

def _new_request_id() -> str:
    from uuid import uuid4
    return f"req_{uuid4()}"

class CodeSearcher:
    """
    Optimized code searcher with CTE queries, FTS support, and MCP-standard output.

    Key improvements:
    - CTE recursive query for efficient graph traversal
    - FTS5 support for fast text search
    - Cursor-based pagination
    - MCP-standard response format
    - Input validation and error handling
    """

    MAX_DEPTH = 3
    MAX_LIMIT = 200
    DEFAULT_LIMIT = 50

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

    def _validate_db(self) -> bool:
        try:
            conn = self._get_conn()
            conn.execute("SELECT 1 FROM symbols LIMIT 1")
            return True
        except sqlite3.OperationalError:
            return False

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

    def symbol_search(self, query: str, cursor: Optional[int] = None, limit: int = DEFAULT_LIMIT, repo_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Search symbols with cursor-based pagination.

        @param query: Search query string (required)
        @param cursor: Cursor for pagination (optional)
        @param limit: Maximum results (default 50, max 200)
        @param repo_id: Filter by repository ID (optional)
        @return: MCP-standard response with items and next_cursor
        """
        request_id = _new_request_id()

        if not query:
            return self._build_response(False, 400, "query is required", None, request_id)

        limit = min(max(1, limit), self.MAX_LIMIT)

        try:
            conn = self._get_conn()
            sql = """
                SELECT s.id, s.name, s.symbol_type, f.relative_path, s.start_line, s.signature, s.docstring, f.repo_id
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                WHERE s.name LIKE ? AND s.id > ?
            """
            params = [f"%{query}%", cursor or 0]

            if repo_id:
                sql += " AND f.repo_id = ?"
                params.append(repo_id)

            sql += " ORDER BY s.id LIMIT ?"
            params.append(limit + 1)

            cursor_obj = conn.execute(sql, params)
            rows = cursor_obj.fetchall()

            has_next = len(rows) > limit
            if has_next:
                rows = rows[:-1]

            items = []
            for row in rows:
                items.append({
                    "symbol_id": row["id"],
                    "symbol": row["name"],
                    "kind": row["symbol_type"],
                    "file": row["relative_path"],
                    "repo_id": row["repo_id"],
                    "line": row["start_line"],
                    "signature": row["signature"] or "",
                    "docstring": row["docstring"] or ""
                })

            next_cursor = items[-1]["symbol_id"] if has_next else None

            return self._build_response(True, 200, f"Found {len(items)} symbols", {
                "items": items,
                "next_cursor": next_cursor,
                "total": len(items)
            }, request_id)

        except sqlite3.Error as e:
            logger.error(f"symbol_search error: {e}")
            return self._build_response(False, 500, f"Database error: {str(e)}", None, request_id)

    def graph_query(self, start_symbol: str, relation: str = "calls", depth: int = 1) -> Dict[str, Any]:
        """
        Query call graph using CTE recursive query (safe from SQL injection).

        @param start_symbol: Starting symbol name (required)
        @param relation: Relation type (default: "calls")
        @param depth: Maximum depth (max 3, default 1)
        @return: MCP-standard response with grouped relations by depth
        """
        request_id = _new_request_id()

        if not start_symbol:
            return self._build_response(False, 400, "start_symbol is required", None, request_id)

        if depth > self.MAX_DEPTH:
            return self._build_response(False, 400, f"depth maksimal {self.MAX_DEPTH}", None, request_id)

        try:
            conn = self._get_conn()

            # Validate start_symbol exists
            check = conn.execute("SELECT id FROM symbols WHERE name = ?", (start_symbol,)).fetchone()
            if not check:
                return self._build_response(False, 404, f"Symbol '{start_symbol}' tidak ditemukan", None, request_id)

            # CTE recursive query
            query = """
                WITH RECURSIVE graph(depth, symbol_name, file_path, line, symbol_id, target_name) AS (
                    SELECT 1, s1.name, f.relative_path, s1.start_line, s1.id, s2.name
                    FROM edges e
                    JOIN symbols s1 ON e.from_symbol_id = s1.id
                    JOIN symbols s2 ON e.to_symbol_id = s2.id
                    JOIN files f ON s2.file_id = f.id
                    WHERE s1.name = ? AND e.relation = ?
                    UNION ALL
                    SELECT g.depth + 1, s1.name, f.relative_path, s1.start_line, s1.id, s2.name
                    FROM graph g
                    JOIN edges e ON g.symbol_id = e.from_symbol_id
                    JOIN symbols s1 ON e.from_symbol_id = s1.id
                    JOIN symbols s2 ON e.to_symbol_id = s2.id
                    JOIN files f ON s2.file_id = f.id
                    WHERE g.depth < ? AND e.relation = ?
                )
                SELECT depth, symbol_name, file_path, line, symbol_id, target_name
                FROM graph
                ORDER BY depth, symbol_name
            """

            cursor = conn.execute(query, (start_symbol, relation, depth, relation))
            rows = cursor.fetchall()

            # Group by depth
            relations_by_depth: Dict[int, List[Dict]] = {}
            for row in rows:
                d = row["depth"]
                if d not in relations_by_depth:
                    relations_by_depth[d] = []
                relations_by_depth[d].append({
                    "source": start_symbol,
                    "target": row["target_name"],
                    "file": row["file_path"],
                    "line": row["line"]
                })

            return self._build_response(True, 200, f"Graph query returned {len(rows)} edges", {
                "start_symbol": start_symbol,
                "relation": relation,
                "max_depth": depth,
                "relations": relations_by_depth
            }, request_id)

        except sqlite3.Error as e:
            logger.error(f"graph_query error: {e}")
            return self._build_response(False, 500, f"Database error: {str(e)}", None, request_id)

    def regex_search(self, pattern: str, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
        """
        Search using regex pattern with FTS fallback.

        @param pattern: Regex pattern (required)
        @param limit: Maximum results (default 50, max 200)
        @return: MCP-standard response with matching symbols
        """
        request_id = _new_request_id()

        if not pattern:
            return self._build_response(False, 400, "pattern is required", None, request_id)

        limit = min(max(1, limit), self.MAX_LIMIT)

        try:
            conn = self._get_conn()

            # Try FTS first if available
            try:
                conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='symbols_fts'")
                fts_check = conn.fetchone()
                if fts_check:
                    cursor = conn.execute(
                        "SELECT symbol_id, name, symbol_type, file_path, line_start FROM symbols_fts WHERE name MATCH ? LIMIT ?",
                        (pattern, limit)
                    )
                    rows = cursor.fetchall()
                    items = [{
                        "symbol": row["name"],
                        "kind": row["kind"],
                        "file": row["file_path"],
                        "line": row["line_start"]
                    } for row in rows]
                    return self._build_response(True, 200, f"Found {len(items)} symbols (FTS)", {
                        "items": items,
                        "total": len(items)
                    }, request_id)
            except sqlite3.Error:
                pass  # FTS not available, fallback to manual regex

            # Manual regex fallback with batch processing
            cursor = conn.execute(
                "SELECT s.name, s.symbol_type, f.relative_path, s.start_line FROM symbols s JOIN files f ON s.file_id = f.id"
            )

            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                return self._build_response(False, 400, f"Invalid regex pattern: {str(e)}", None, request_id)

            items = []
            for row in cursor:
                if regex.search(row["name"]):
                    items.append({
                        "symbol": row["name"],
                        "kind": row["symbol_type"],
                        "file": row["relative_path"],
                        "line": row["start_line"]
                    })
                    if len(items) >= limit:
                        break

            return self._build_response(True, 200, f"Found {len(items)} symbols", {
                "items": items,
                "total": len(items)
            }, request_id)

        except sqlite3.Error as e:
            logger.error(f"regex_search error: {e}")
            return self._build_response(False, 500, f"Database error: {str(e)}", None, request_id)

    def semantic_search(self, query_embedding: List[float], limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
        """
        Semantic search using vector embedding (cosine similarity).

        @param query_embedding: Query embedding vector
        @param limit: Maximum results (default 50)
        @return: MCP-standard response with similarity scores
        """
        request_id = _new_request_id()

        if not query_embedding:
            return self._build_response(False, 400, "query_embedding is required", None, request_id)

        try:
            conn = self._get_conn()

            # Check if embeddings table exists
            try:
                conn.execute("SELECT 1 FROM embeddings LIMIT 1")
            except sqlite3.OperationalError:
                return self._build_response(False, 500, "Embeddings table not available. Run code analysis first.", None, request_id)

            cursor = conn.execute("SELECT symbol_id, embedding FROM embeddings")
            rows = cursor.fetchall()

            import math
            def cosine_similarity(a: List[float], b: List[float]) -> float:
                dot = sum(x * y for x, y in zip(a, b))
                mag_a = math.sqrt(sum(x * x for x in a))
                mag_b = math.sqrt(sum(x * x for x in b))
                return dot / (mag_a * mag_b) if mag_a and mag_b else 0

            similarities = []
            for row in rows:
                try:
                    emb = [float(x) for x in row["embedding"].split(",")] if isinstance(row["embedding"], str) else row["embedding"]
                    score = cosine_similarity(query_embedding, emb)
                    similarities.append((row["symbol_id"], score))
                except (ValueError, TypeError):
                    continue

            similarities.sort(key=lambda x: x[1], reverse=True)
            top_results = similarities[:limit]

            items = []
            for symbol_id, score in top_results:
                sym_cursor = conn.execute("SELECT s.name, s.symbol_type, f.relative_path, s.start_line FROM symbols s JOIN files f ON s.file_id = f.id WHERE s.id = ?", (symbol_id,))
                sym_row = sym_cursor.fetchone()
                if sym_row:
                    items.append({
                        "symbol": sym_row["name"],
                        "kind": sym_row["symbol_type"],
                        "file": sym_row["relative_path"],
                        "line": sym_row["start_line"],
                        "similarity": round(score, 4)
                    })

            return self._build_response(True, 200, f"Found {len(items)} similar symbols", {
                "items": items,
                "total": len(items)
            }, request_id)

        except sqlite3.Error as e:
            logger.error(f"semantic_search error: {e}")
            return self._build_response(False, 500, f"Database error: {str(e)}", None, request_id)
