"""
Search – Multi-layer code search: FTS text (always) + optional semantic + graph enrichment.
All results cached via IndexCache with sync markers.

:project: CodeCortex
:package: Modules.Codeanalysis.Services.Search
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeAnalysis-v1.0
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from src.core.database import DatabaseManager
from src.core.logging import get_logger
from src.modules.codeanalysis.core.dtos import SearchRequest, SearchResult, SearchMatch

logger = get_logger("CodeCortex.CodeAnalysis.Search")

MAX_LIMIT = 200

class Search:
    """Multi-layer code search with optional semantic and graph enrichment.

    Flow:
        1. FTS5 text search (always, fastest)
        2. Semantic enrichment (optional, embedding similarity)
        3. Graph enrichment (optional, relationships per match)
    Results cached via IndexCache.index_query_cache.
    """

    def __init__(self, db: DatabaseManager):
        self.db = db

    def search(
        self,
        request: SearchRequest,
        semantic: bool = False,
        graph: bool = False,
        graph_relations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute multi-layer search with optional enrichment.

        Returns enriched dict with matches, semantic, relationships, and metadata.
        """
        if not request.query:
            raise ValueError("query is required")

        limit = min(max(1, request.limit), MAX_LIMIT)
        repo_id = request.repo_id
        search_type = request.search_type
        result: Dict[str, Any] = {"query": request.query, "repo_id": repo_id}

        # Build cache key
        from src.core.database.index_cache import IndexCache
        cache = IndexCache(self.db)
        params = json.dumps([search_type, semantic, graph, graph_relations or []])
        query_hash = cache.hash_query(repo_id or "global", request.query, "search", params)

        # Check cache
        cached = cache.get_query(repo_id or "global", query_hash)
        if cached:
            cached["from_cache"] = True
            self._add_sync_meta(cached, cache, repo_id)
            return cached

        # ── Layer 1: Execute search based on type ────────────────
        if search_type == "regex":
            matches = self._regex_search(request.query, limit, repo_id)
        elif search_type == "symbol":
            matches = self._symbol_search(request.query, limit, repo_id)
        else:
            # Default: FTS5 text search (multi, semantic, graph modes)
            matches = self._fts_search(request.query, limit, repo_id)

        result["matches"] = matches
        result["total_matches"] = len(matches)
        result["search_type"] = search_type

        # ── Layer 2: Semantic enrichment (optional) ────────────
        if semantic and search_type in ("multi", "semantic"):
            try:
                semantic_hits = self._semantic_enrich(request.query, limit, repo_id)
                result["semantic"] = semantic_hits
                result["total_semantic"] = len(semantic_hits)
            except Exception as e:
                logger.warning(f"Semantic enrichment failed: {e}")
                result["semantic"] = []
                result["total_semantic"] = 0

        # ── Layer 3: Graph enrichment (optional) ───────────────
        if graph and matches and search_type in ("multi", "graph"):
            try:
                relations = graph_relations or ["calls", "inherits", "imports"]
                rels = self._graph_enrich([m["symbol"] for m in matches[:5]], relations, repo_id)
                result["relationships"] = rels
                result["total_relationships"] = len(rels)
            except Exception as e:
                logger.warning(f"Graph enrichment failed: {e}")
                result["relationships"] = []
                result["total_relationships"] = 0

        # Add sync metadata
        self._add_sync_meta(result, cache, repo_id)

        # Cache result
        result["from_cache"] = False
        cache.set_query(repo_id or "global", query_hash, result, ttl_seconds=300)
        return result

    def _symbol_search(
        self, query: str, limit: int, repo_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Symbol name exact/prefix search for symbol type."""
        conn = self.db.conn
        params: list[Any] = [query, limit]
        cond = "WHERE s.name = ?"

        if repo_id:
            cond = "WHERE s.name = ? AND s.repository_id = ?"
            params = [query, repo_id, limit]

        rows = conn.execute(
            f"""SELECT s.name, s.symbol_type, s.start_line, s.signature, s.docstring,
                       f.relative_path, s.id
                FROM symbols s LEFT JOIN files f ON s.file_id = f.id
                {cond}
                ORDER BY s.name LIMIT ?""",
            params,
        ).fetchall()

        return [
            {
                "symbol": r[0], "kind": r[1], "line": r[2],
                "signature": r[3] or "", "docstring": (r[4] or "")[:200],
                "file": r[5] or "", "id": r[6],
            }
            for r in rows
        ]

    def _regex_search(
        self, query: str, limit: int, repo_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Regex search on symbol names with validation."""
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error as e:
            logger.warning(f"Invalid regex pattern: {query} - {e}")
            return []

        conn = self.db.conn
        type_filter = ""
        params: list[Any] = [limit]

        if repo_id:
            type_filter = "WHERE s.repository_id = ?"
            params.insert(0, repo_id)

        rows = conn.execute(
            f"""SELECT s.name, s.symbol_type, s.start_line, s.signature, s.docstring,
                       f.relative_path, s.id
                FROM symbols s LEFT JOIN files f ON s.file_id = f.id
                {type_filter}
                ORDER BY s.name""",
            params[:-1] if repo_id else [],
        ).fetchall()

        matches = []
        for r in rows:
            if pattern.search(r[0]):
                matches.append({
                    "symbol": r[0], "kind": r[1], "line": r[2],
                    "signature": r[3] or "", "docstring": (r[4] or "")[:200],
                    "file": r[5] or "", "id": r[6],
                })
                if len(matches) >= limit:
                    break

        return matches

    def _fts_search(
        self, query: str, limit: int, repo_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """FTS5 full-text search on symbol names and signatures."""
        try:
            conn = self.db.conn
            # Try FTS5 first
            type_filter = ""
            params: list[Any] = [query, limit]
            if repo_id:
                type_filter = "AND s.repository_id = ?"
                params.insert(1, repo_id)

            rows = conn.execute(
                f"""SELECT s.name, s.symbol_type, s.start_line, s.signature, s.docstring,
                           f.relative_path, s.id
                    FROM symbol_fts ft
                    JOIN symbols s ON s.rowid = ft.rowid
                    LEFT JOIN files f ON s.file_id = f.id
                    WHERE symbol_fts MATCH ? {type_filter}
                    ORDER BY rank LIMIT ?""",
                params,
            ).fetchall()
        except Exception:
            # Fallback to LIKE search
            like = f"%{query}%"
            params_like: list[Any] = [like, limit]
            cond = ""
            if repo_id:
                cond = "AND s.repository_id = ?"
                params_like.insert(1, repo_id)
            rows = self.db.conn.execute(
                f"""SELECT s.name, s.symbol_type, s.start_line, s.signature, s.docstring,
                           f.relative_path, s.id
                    FROM symbols s LEFT JOIN files f ON s.file_id = f.id
                    WHERE s.name LIKE ? {cond}
                    ORDER BY s.name LIMIT ?""",
                params_like,
            ).fetchall()

        return [
            {
                "symbol": r[0], "kind": r[1], "line": r[2],
                "signature": r[3] or "", "docstring": (r[4] or "")[:200],
                "file": r[5] or "", "id": r[6],
            }
            for r in rows
        ]

    def _semantic_enrich(
        self, query: str, limit: int, repo_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Semantic embedding search for related symbols."""
        from src.core.database.index_cache import IndexCache
        cache = IndexCache(self.db)

        # Generate query embedding
        try:
            from src.modules.codeindex.parsers.embeddings import _get_model
            model = _get_model()
            q_emb = model.encode([query])[0].astype("float32").tobytes()
        except Exception:
            return []

        results = cache.search_embeddings(repo_id or "global", q_emb, top_k=limit)
        return [
            {"file": r["file_path"], "chunk_index": r["chunk_index"],
             "content": r["content"], "score": r["score"]}
            for r in results
        ]

    def _graph_enrich(
        self, symbols: List[str], relations: List[str], repo_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Find graph relationships for a list of symbols."""
        conn = self.db.conn
        results = []
        seen: set[str] = set()

        for sym in symbols:
            for rel in relations:
                rows = conn.execute(
                    """SELECT s1.name, s2.name, e.relation_type, e.weight
                       FROM edges e
                       JOIN symbols s1 ON e.source_id = s1.id
                       JOIN symbols s2 ON e.target_id = s2.id
                       WHERE s1.name = ? AND e.relation_type = ?
                       ORDER BY e.weight DESC LIMIT 10""",
                    (sym, rel),
                ).fetchall()

                for r in rows:
                    key = f"{r[0]}:{r[2]}:{r[1]}"
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "source": r[0], "target": r[1],
                            "relation": r[2], "weight": r[3],
                        })

        return results

    def _add_sync_meta(
        self, result: Dict[str, Any], cache: Any, repo_id: Optional[str],
    ) -> None:
        """Add sync_at metadata to result."""
        if repo_id:
            try:
                stats = cache.get_stats(repo_id)
                if stats and stats.get("synced_at"):
                    result["meta"] = {
                        "repo_id": repo_id,
                        "synced_at": stats["synced_at"],
                        "total_symbols": stats.get("total_symbols", 0),
                        "total_edges": stats.get("total_edges", 0),
                    }
                    return
            except Exception:
                pass
        result["meta"] = {"repo_id": repo_id or "global"}
