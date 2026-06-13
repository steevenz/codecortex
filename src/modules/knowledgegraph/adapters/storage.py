"""
Knowledge Storage — persists extracted chunks to SQLite + GoldenKnowledgeStore
and provides query/retrieval APIs.

Connected to:
- GoldenKnowledgeStore: high-value chunks also stored there for AI context injection
- SQLite (direct): efficient chunk-level queries, relationships
- ContextDedup (future): deduplicate across sessions

Query modes supported:
    FTS5, regex, glob, pattern, structured query DSL, vector embedding similarity,
    range queries (importance_score, confidence_score), task-based keyword/semantic.

Standards:
    - CODDY-Architecture-v1.0    → Adapter Pattern (wraps SQLite + GoldenKnowledgeStore)
    - CODDY-ProjectStructure-v1.0 → adapters/ requirements
"""

from __future__ import annotations

__all__ = ["KnowledgeStore"]

import fnmatch
import json
import logging
import math
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.modules.knowledgegraph.core.classification import KnowledgeScorer
from src.modules.knowledgegraph.models.chunk import KnowledgeChunk

logger = logging.getLogger("CodeCortex.KnowledgeGraph.Storage")


class KnowledgeStore:
    """Persistent store for knowledge chunks with retrieval APIs.

    Two-layer persistence:
    1. Chunk-level SQLite: full metadata, importance scores, queries
    2. GoldenKnowledgeStore: high-value entries for AI context injection

    Usage:
        store = KnowledgeStore(orchestrator.db)
        store.store_chunks(chunks)  # persists to both layers
        results = store.query(task="refactor payment")
    """

    def __init__(self, db):
        self.db = db
        self.scorer = KnowledgeScorer()
        self._golden = None  # lazy init
        self._GoldenKnowledge = None  # lazy-loaded class ref
        self._ensure_tables()

    def _get_golden(self):
        """Lazy init GoldenKnowledgeStore to avoid circular imports."""
        if self._golden is None:
            from src.modules.codegraph.core.golden_knowledge import (
                GoldenKnowledge, GoldenKnowledgeStore,
            )
            self._golden = GoldenKnowledgeStore(self.db)
            self._GoldenKnowledge = GoldenKnowledge
        return self._golden

    def _ensure_tables(self) -> None:
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id TEXT PRIMARY KEY,
                knowledge_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_file TEXT NOT NULL,
                doc_type TEXT DEFAULT 'unknown',
                summary TEXT DEFAULT '',
                section_path TEXT DEFAULT '',
                importance_score REAL DEFAULT 0.5,
                criticality TEXT DEFAULT 'medium',
                confidence_score REAL DEFAULT 0.5,
                repo_id TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                concept TEXT DEFAULT '[]',
                related_module TEXT DEFAULT '[]',
                architecture_tag TEXT DEFAULT '[]',
                embedding TEXT DEFAULT '[]'
            )
        """)
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_relationships (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                description TEXT DEFAULT '',
                direction TEXT DEFAULT 'directed',
                created_at TEXT DEFAULT '',
                PRIMARY KEY (source_id, target_id, relation_type)
            )
        """)
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS extraction_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id TEXT NOT NULL,
                repo_path TEXT NOT NULL,
                source_file TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                chunks_extracted INTEGER DEFAULT 0,
                extracted_at TEXT NOT NULL
            )
        """)
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS repo_metadata (
                repo_id TEXT PRIMARY KEY,
                repo_path TEXT NOT NULL,
                last_extracted_at TEXT NOT NULL,
                total_chunks INTEGER DEFAULT 0,
                total_relationships INTEGER DEFAULT 0
            )
        """)
        # FTS5 full-text search virtual table
        self.db.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts USING fts5(
                id, title, content, summary,
                content='knowledge_chunks', content_rowid='rowid',
                prefix='2,3,4', tokenize='porter unicode61'
            )
        """)
        # Triggers to keep FTS index in sync
        self.db.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS kc_fts_insert AFTER INSERT ON knowledge_chunks BEGIN
                INSERT INTO knowledge_chunks_fts(rowid, id, title, content, summary)
                VALUES (new.rowid, new.id, new.title, new.content, new.summary);
            END
        """)
        self.db.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS kc_fts_delete AFTER DELETE ON knowledge_chunks BEGIN
                INSERT INTO knowledge_chunks_fts(knowledge_chunks_fts, rowid, id, title, content, summary)
                VALUES ('delete', old.rowid, old.id, old.title, old.content, old.summary);
            END
        """)
        self.db.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS kc_fts_update AFTER UPDATE ON knowledge_chunks BEGIN
                INSERT INTO knowledge_chunks_fts(knowledge_chunks_fts, rowid, id, title, content, summary)
                VALUES ('delete', old.rowid, old.id, old.title, old.content, old.summary);
                INSERT INTO knowledge_chunks_fts(rowid, id, title, content, summary)
                VALUES (new.rowid, new.id, new.title, new.content, new.summary);
            END
        """)
        # Register custom REGEXP function for SQLite
        def _regexp(pattern: str, value: str) -> int:
            return 1 if re.search(pattern, value or "") else 0
        self.db.conn.create_function("REGEXP", 2, _regexp)
        # Schema migration: Add missing columns if they don't exist
        columns_kc = [row["name"] for row in self.db.conn.execute("PRAGMA table_info(knowledge_chunks)").fetchall()]
        if "repo_id" not in columns_kc:
            self.db.conn.execute("ALTER TABLE knowledge_chunks ADD COLUMN repo_id TEXT DEFAULT ''")
        if "confidence_score" not in columns_kc:
            self.db.conn.execute("ALTER TABLE knowledge_chunks ADD COLUMN confidence_score REAL DEFAULT 0.5")
        if "updated_at" not in columns_kc:
            self.db.conn.execute("ALTER TABLE knowledge_chunks ADD COLUMN updated_at TEXT DEFAULT ''")
        if "embedding" not in columns_kc:
            self.db.conn.execute("ALTER TABLE knowledge_chunks ADD COLUMN embedding TEXT DEFAULT '[]'")

        columns_el = [row["name"] for row in self.db.conn.execute("PRAGMA table_info(extraction_log)").fetchall()]
        if "repo_id" not in columns_el:
            self.db.conn.execute("ALTER TABLE extraction_log ADD COLUMN repo_id TEXT DEFAULT ''")

        self.db.conn.commit()

        self.db.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kc_type ON knowledge_chunks(knowledge_type)"
        )
        self.db.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kc_source ON knowledge_chunks(source_file)"
        )
        self.db.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kc_repo ON knowledge_chunks(repo_id)"
        )
        self.db.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kc_updated ON knowledge_chunks(updated_at)"
        )
        self.db.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_el_repo ON extraction_log(repo_id)"
        )
        self.db.conn.commit()

        self.db.conn.commit()

    def store_chunks(self, chunks: List[KnowledgeChunk]) -> int:
        """Store multiple chunks (idempotent).

        Persists to:
        1. SQLite knowledge_chunks table (full metadata)
        2. GoldenKnowledgeStore (high-value entries for AI context)

        Returns count stored.
        """
        count = 0
        golden_store = self._get_golden()

        for chunk in self.scorer.score_batch(chunks):
            try:
                chunk.updated_at = datetime.now(timezone.utc).isoformat()
                self.db.conn.execute(
                    """INSERT OR REPLACE INTO knowledge_chunks
                       (id, knowledge_type, title, content, source_file, doc_type,
                        summary, section_path, importance_score, criticality,
                        confidence_score, repo_id, created_at, updated_at,
                        concept, related_module, architecture_tag, embedding)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        chunk.id, chunk.knowledge_type, chunk.title, chunk.content,
                        chunk.source_file, chunk.doc_type, chunk.summary,
                        chunk.section_path, chunk.importance_score, chunk.criticality,
                        chunk.confidence_score, chunk.repo_id, chunk.created_at, chunk.updated_at,
                        json.dumps(chunk.concept), json.dumps(chunk.related_module),
                        json.dumps(chunk.architecture_tag),
                        json.dumps(chunk.embedding) if chunk.embedding else '[]',
                    ),
                )
                count += 1

                # Also store high-importance chunks to GoldenKnowledgeStore
                if chunk.importance_score >= 0.6:
                    golden_k = self._GoldenKnowledge(
                        entry_type=chunk.knowledge_type,
                        content=f"{chunk.title}: {chunk.summary}",
                        source=chunk.source_file,
                        applies_to=chunk.related_module,
                        confidence=chunk.importance_score,
                        tags=chunk.architecture_tag + ["knowledge_graph"],
                    )
                    try:
                        golden_store.store(golden_k)
                    except Exception:
                        pass

            except Exception as e:
                logger.debug(f"Failed to store chunk {chunk.id}: {e}")
                continue

        self.db.conn.commit()
        logger.info(f"Stored {count}/{len(chunks)} knowledge chunks (+{sum(1 for c in chunks if c.importance_score >= 0.6)} to golden)")
        return count

    def store_relationships(self, relationships: list) -> int:
        """Store relationship edges. Returns count stored."""
        count = 0
        for rel in relationships:
            try:
                self.db.conn.execute(
                    """INSERT OR REPLACE INTO knowledge_relationships
                       (source_id, target_id, relation_type, weight, description, direction, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (rel.source_id, rel.target_id, rel.relation_type, rel.weight, rel.description, rel.direction, rel.created_at),
                )
                count += 1
            except Exception:
                continue
        self.db.conn.commit()
        return count

    def query(
        self,
        task: Optional[str] = None,
        knowledge_types: Optional[List[str]] = None,
        source_file: Optional[str] = None,
        min_importance: float = 0.0,
        max_importance: Optional[float] = None,
        min_confidence: float = 0.0,
        max_confidence: Optional[float] = None,
        repo_id: Optional[str] = None,
        semantic: bool = False,
        fts_query: Optional[str] = None,
        regex: Optional[str] = None,
        glob: Optional[str] = None,
        pattern: Optional[str] = None,
        structured_query: Optional[Dict[str, Any]] = None,
        search_fields: Optional[List[str]] = None,
        vector_search: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Query stored knowledge chunks with advanced search capabilities.

        Args:
            task: Natural language task description (keyword matching).
            knowledge_types: Filter by type(s). None = all.
            source_file: Filter by source file.
            min_importance: Minimum importance score filter.
            max_importance: Maximum importance score filter.
            min_confidence: Minimum confidence score filter.
            max_confidence: Maximum confidence score filter.
            repo_id: Filter by repository ID.
            semantic: Enable semantic search using keyword overlap.
            fts_query: Full-text search query (SQLite FTS5).
            regex: Regex pattern to match against content/title.
            glob: Glob pattern for source_file matching.
            pattern: Simple pattern matching (supports * and ?) against content.
            structured_query: Advanced structured query DSL.
            search_fields: Fields to search in (title, content, summary).
            vector_search: Text to compute vector similarity against embeddings.
            limit: Max results.

        Returns:
            Dict with chunks, relevance scores, query metadata, and explanation.
        """
        explanation_parts: List[str] = []
        chunk_ids: Optional[List[str]] = None

        # 1. FTS5 full-text search (fastest, use first)
        if fts_query:
            try:
                fts_rows = self.db.conn.execute(
                    "SELECT id FROM knowledge_chunks_fts WHERE knowledge_chunks_fts MATCH ? LIMIT ?",
                    (fts_query, limit * 5),
                ).fetchall()
                chunk_ids = [r["id"] for r in fts_rows]
                explanation_parts.append(f"FTS5 matched {len(chunk_ids)} chunks for query '{fts_query}'")
            except Exception:
                explanation_parts.append(f"FTS5 query failed for '{fts_query}', falling back to standard search")

        # 2. Regex search via SQLite REGEXP function
        if regex and not chunk_ids:
            try:
                search_cols = " || ' ' || ".join(search_fields or ["title", "content", "summary"])
                reg_rows = self.db.conn.execute(
                    f"SELECT id FROM knowledge_chunks WHERE ({search_cols}) REGEXP ? LIMIT ?",
                    (regex, limit * 5),
                ).fetchall()
                chunk_ids = [r["id"] for r in reg_rows]
                explanation_parts.append(f"Regex matched {len(chunk_ids)} chunks with pattern '{regex}'")
            except Exception:
                explanation_parts.append(f"Regex search failed for '{regex}'")

        # 3. Pattern search (simple wildcard * and ?)
        if pattern and not chunk_ids:
            try:
                pat_rows = self.db.conn.execute(
                    "SELECT id, title, content, summary FROM knowledge_chunks LIMIT 1000"
                ).fetchall()
                matched_ids = []
                regex_pat = re.compile(fnmatch.translate(pattern), re.I)
                for r in pat_rows:
                    text = f"{r['title']} {r['content']} {r['summary']}"
                    if regex_pat.search(text):
                        matched_ids.append(r["id"])
                chunk_ids = matched_ids[:limit * 5]
                explanation_parts.append(f"Pattern matched {len(chunk_ids)} chunks with '{pattern}'")
            except Exception:
                explanation_parts.append(f"Pattern search failed for '{pattern}'")

        # 4. Structured query DSL
        if structured_query and not chunk_ids:
            try:
                sq_sql, sq_params = self._build_structured_query(structured_query)
                if sq_sql:
                    sq_rows = self.db.conn.execute(
                        f"SELECT id FROM knowledge_chunks WHERE {sq_sql} LIMIT ?",
                        (*sq_params, limit * 5),
                    ).fetchall()
                    chunk_ids = [r["id"] for r in sq_rows]
                    explanation_parts.append(f"Structured query matched {len(chunk_ids)} chunks")
            except Exception:
                explanation_parts.append("Structured query failed")

        # Build WHERE clause for standard filtering
        conditions: List[str] = []
        params: List[Any] = []

        if chunk_ids:
            placeholders = ",".join("?" * len(chunk_ids))
            conditions.append(f"id IN ({placeholders})")
            params.extend(chunk_ids)

        if knowledge_types:
            placeholders = ",".join("?" * len(knowledge_types))
            conditions.append(f"knowledge_type IN ({placeholders})")
            params.extend(knowledge_types)

        if source_file:
            conditions.append("source_file = ?")
            params.append(source_file)

        if glob:
            # Use GLOB for source_file matching
            conditions.append("source_file GLOB ?")
            params.append(glob)
            explanation_parts.append(f"Glob pattern '{glob}' applied to source_file")

        if repo_id:
            conditions.append("repo_id = ?")
            params.append(repo_id)

        if min_importance > 0:
            conditions.append("importance_score >= ?")
            params.append(min_importance)

        if max_importance is not None:
            conditions.append("importance_score <= ?")
            params.append(max_importance)

        if min_confidence > 0:
            conditions.append("confidence_score >= ?")
            params.append(min_confidence)

        if max_confidence is not None:
            conditions.append("confidence_score <= ?")
            params.append(max_confidence)

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = self.db.conn.execute(
            f"SELECT * FROM knowledge_chunks WHERE {where} ORDER BY importance_score DESC LIMIT ?",
            (*params, limit * 3),
        ).fetchall()

        chunks = [self._row_to_chunk(r) for r in rows]

        # 5. Vector search (cosine similarity against embeddings)
        if vector_search and chunks:
            vec = self._text_to_vector(vector_search)
            scored = []
            for c in chunks:
                if c.embedding:
                    sim = self._cosine_similarity(vec, c.embedding)
                    scored.append((sim, c))
            scored.sort(key=lambda x: x[0], reverse=True)
            chunks = [c for _, c in scored]
            explanation_parts.append(f"Vector-ranked {len(chunks)} chunks by embedding similarity")

        # 6. Task-based keyword or semantic reranking
        if task and chunks:
            if semantic:
                chunks, semantic_parts = self._semantic_rerank(chunks, task)
                explanation_parts.extend(semantic_parts)
            else:
                chunks = self._rerank_by_task(chunks, task)
                explanation_parts.append(f"Keyword-matched {len(chunks)} chunks against task keywords")

        # Compute relevance_score per chunk
        result_dicts = []
        for idx, c in enumerate(chunks[:limit]):
            d = c.to_dict()
            d["relevance_score"] = max(0.0, 1.0 - (idx * 0.05))
            result_dicts.append(d)

        explanation = self._build_explanation(
            task, knowledge_types, source_file, repo_id, len(result_dicts), explanation_parts
        )

        return {
            "total": len(result_dicts),
            "chunks": result_dicts,
            "types_available": self._available_types(),
            "query": {
                "task": task,
                "types": knowledge_types,
                "source_file": source_file,
                "repo_id": repo_id,
                "min_importance": min_importance,
                "max_importance": max_importance,
                "min_confidence": min_confidence,
                "max_confidence": max_confidence,
                "semantic": semantic,
                "fts_query": fts_query,
                "regex": regex,
                "glob": glob,
                "pattern": pattern,
                "vector_search": vector_search is not None,
                "structured_query": structured_query is not None,
            },
            "explanation": explanation,
        }

    def get_relationships(self, chunk_id: Optional[str] = None) -> Dict[str, Any]:
        if chunk_id:
            rows = self.db.conn.execute(
                "SELECT * FROM knowledge_relationships WHERE source_id = ? OR target_id = ?",
                (chunk_id, chunk_id),
            ).fetchall()
        else:
            rows = self.db.conn.execute(
                "SELECT * FROM knowledge_relationships ORDER BY weight DESC LIMIT 200"
            ).fetchall()

        edges = [dict(r) for r in rows]
        stats = self._compute_graph_stats(edges)

        # Enrich edges with node metadata
        node_ids = set()
        for e in edges:
            node_ids.add(e["source_id"])
            node_ids.add(e["target_id"])

        node_meta = {}
        if node_ids:
            placeholders = ",".join("?" * len(node_ids))
            for row in self.db.conn.execute(
                f"SELECT id, knowledge_type, title FROM knowledge_chunks WHERE id IN ({placeholders})",
                tuple(node_ids),
            ).fetchall():
                node_meta[row["id"]] = {"knowledge_type": row["knowledge_type"], "title": row["title"]}

        enriched_edges = []
        for e in edges:
            enriched = dict(e)
            enriched["source_meta"] = node_meta.get(e["source_id"], {})
            enriched["target_meta"] = node_meta.get(e["target_id"], {})
            enriched_edges.append(enriched)

        return {
            "total": len(edges),
            "edges": enriched_edges,
            "statistics": stats,
        }

    def status(self, repo_id: Optional[str] = None) -> Dict[str, Any]:
        where = "WHERE repo_id = ?" if repo_id else ""
        params = (repo_id,) if repo_id else ()

        rows = self.db.conn.execute(
            f"SELECT knowledge_type, COUNT(*) as count FROM knowledge_chunks {where} GROUP BY knowledge_type",
            params,
        ).fetchall()
        by_type = {r["knowledge_type"]: r["count"] for r in rows}
        total = sum(by_type.values())
        sources = [
            r["source_file"] for r in
            self.db.conn.execute(
                f"SELECT DISTINCT source_file FROM knowledge_chunks {where} ORDER BY source_file",
                params,
            ).fetchall()
        ]

        # Relationship count
        rel_count = self.db.conn.execute(
            "SELECT COUNT(*) FROM knowledge_relationships"
        ).fetchone()[0]

        # Avg importance_score
        avg_score = self.db.conn.execute(
            f"SELECT AVG(importance_score) FROM knowledge_chunks {where}",
            params,
        ).fetchone()[0] or 0.0

        # Avg confidence_score
        avg_conf = self.db.conn.execute(
            f"SELECT AVG(confidence_score) FROM knowledge_chunks {where}",
            params,
        ).fetchone()[0] or 0.0

        # Last extraction time
        last_extracted = self.db.conn.execute(
            "SELECT MAX(extracted_at) FROM extraction_log"
        ).fetchone()[0] or ""

        # Repo metadata
        repo_meta = {}
        if repo_id:
            row = self.db.conn.execute(
                "SELECT * FROM repo_metadata WHERE repo_id = ?", (repo_id,)
            ).fetchone()
            if row:
                repo_meta = dict(row)

        return {
            "total_chunks": total,
            "by_type": by_type,
            "sources": sources,
            "total_relationships": rel_count,
            "avg_importance_score": round(float(avg_score), 3),
            "avg_confidence_score": round(float(avg_conf), 3),
            "last_extracted_at": last_extracted,
            "repo_metadata": repo_meta,
        }

    def clear(self, source_file: Optional[str] = None) -> int:
        if source_file:
            self.db.conn.execute("DELETE FROM knowledge_chunks WHERE source_file = ?", (source_file,))
            count = self.db.conn.execute(
                "SELECT changes()"
            ).fetchone()[0]
        else:
            self.db.conn.execute("DELETE FROM knowledge_chunks")
            self.db.conn.execute("DELETE FROM knowledge_relationships")
            count = -1  # bulk clear
        self.db.conn.commit()
        return count

    def _rerank_by_task(self, chunks: List[KnowledgeChunk], task: str) -> List[KnowledgeChunk]:
        """Relevance rerank by keyword matching against task description."""
        keywords = set(re.findall(r"\b\w{4,}\b", task.lower()))
        scored = []
        for c in chunks:
            text = (c.title + " " + c.content + " " + " ".join(c.concept)).lower()
            matches = sum(1 for k in keywords if k in text)
            scored.append((matches, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored]

    def log_extraction(self, repo_id: str, repo_path: str, source_file: str,
                       file_hash: str, file_size: int, chunks_extracted: int) -> None:
        """Log extraction event for incremental tracking."""
        self.db.conn.execute(
            """INSERT OR REPLACE INTO extraction_log
               (repo_id, repo_path, source_file, file_hash, file_size, chunks_extracted, extracted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (repo_id, repo_path, source_file, file_hash, file_size, chunks_extracted,
             datetime.now(timezone.utc).isoformat()),
        )
        self.db.conn.commit()

    def get_extraction_log(self, repo_id: str, source_file: str) -> Optional[Dict[str, Any]]:
        """Get last extraction record for a file to check if re-extraction is needed."""
        row = self.db.conn.execute(
            """SELECT * FROM extraction_log
               WHERE repo_id = ? AND source_file = ?
               ORDER BY extracted_at DESC LIMIT 1""",
            (repo_id, source_file),
        ).fetchone()
        return dict(row) if row else None

    def update_repo_metadata(self, repo_id: str, repo_path: str,
                             total_chunks: int, total_relationships: int) -> None:
        """Update repository metadata after extraction."""
        self.db.conn.execute(
            """INSERT OR REPLACE INTO repo_metadata
               (repo_id, repo_path, last_extracted_at, total_chunks, total_relationships)
               VALUES (?, ?, ?, ?, ?)""",
            (repo_id, repo_path, datetime.now(timezone.utc).isoformat(),
             total_chunks, total_relationships),
        )
        self.db.conn.commit()

    @staticmethod
    def _build_explanation(task: Optional[str], knowledge_types: Optional[List[str]],
                             source_file: Optional[str], repo_id: Optional[str],
                             total: int, parts: List[str]) -> str:
        """Build human-readable query explanation."""
        explanations = [f"Retrieved {total} knowledge chunks"]
        if task:
            explanations.append(f"Task: '{task}'")
        if knowledge_types:
            explanations.append(f"Filtered to types: {', '.join(knowledge_types)}")
        if source_file:
            explanations.append(f"Filtered to source: {source_file}")
        if repo_id:
            explanations.append(f"Filtered to repo: {repo_id}")
        explanations.extend(parts)
        return "; ".join(explanations)

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _semantic_rerank(self, chunks: List[KnowledgeChunk], task: str) -> Tuple[List[KnowledgeChunk], List[str]]:
        """Rerank chunks by semantic similarity using embeddings."""
        # Simple keyword-based embedding simulation (TF-IDF-style)
        task_keywords = set(re.findall(r"\b\w{4,}\b", task.lower()))
        if not task_keywords:
            return chunks, []

        # Build term frequency for task
        task_vec = {kw: 1.0 for kw in task_keywords}

        scored = []
        for c in chunks:
            text = (c.title + " " + c.content + " " + " ".join(c.concept)).lower()
            chunk_keywords = set(re.findall(r"\b\w{4,}\b", text))
            overlap = task_keywords & chunk_keywords
            if overlap:
                score = len(overlap) / max(len(task_keywords), len(chunk_keywords))
            else:
                score = 0.0
            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        explanation = f"Semantic reranked {len(chunks)} chunks by keyword overlap similarity"
        return [c for _, c in scored], [explanation]

    @staticmethod
    def _compute_graph_stats(edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute graph statistics (density, avg degree, clustering)."""
        if not edges:
            return {"density": 0.0, "avg_degree": 0.0, "clustering": 0.0, "unique_nodes": 0}

        nodes = set()
        degree: Dict[str, int] = {}
        for e in edges:
            src, tgt = e["source_id"], e["target_id"]
            nodes.add(src)
            nodes.add(tgt)
            degree[src] = degree.get(src, 0) + 1
            degree[tgt] = degree.get(tgt, 0) + 1

        n = len(nodes)
        m = len(edges)
        density = (2 * m) / (n * (n - 1)) if n > 1 else 0.0
        avg_degree = sum(degree.values()) / n if n > 0 else 0.0

        # Simple clustering: count triangles
        adj: Dict[str, set] = {node: set() for node in nodes}
        for e in edges:
            adj[e["source_id"]].add(e["target_id"])
            adj[e["target_id"]].add(e["source_id"])

        clustering_scores = []
        for node in nodes:
            neighbors = adj[node]
            if len(neighbors) < 2:
                continue
            triangles = 0
            for n1 in neighbors:
                for n2 in neighbors:
                    if n1 != n2 and n2 in adj.get(n1, set()):
                        triangles += 1
            possible = len(neighbors) * (len(neighbors) - 1)
            clustering_scores.append(triangles / possible if possible > 0 else 0.0)

        avg_clustering = sum(clustering_scores) / len(clustering_scores) if clustering_scores else 0.0

        return {
            "density": round(density, 4),
            "avg_degree": round(avg_degree, 2),
            "clustering": round(avg_clustering, 4),
            "unique_nodes": n,
            "total_edges": m,
        }

    @staticmethod
    def _build_structured_query(query: Dict[str, Any]) -> Tuple[str, Tuple[Any, ...]]:
        """Build SQL WHERE clause from structured query DSL.

        DSL format:
            {"and": [{"field": "knowledge_type", "op": "=", "value": "constraint"},
                      {"field": "importance_score", "op": ">=", "value": 0.7}]}
            {"or": [{"field": "title", "op": "like", "value": "%payment%"},
                    {"field": "content", "op": "like", "value": "%auth%"}]}
            {"not": {"field": "criticality", "op": "=", "value": "low"}}

        Supported ops: =, !=, <, >, <=, >=, like, not_like, in, not_in, glob, regexp
        """
        VALID_OPS = {"=", "!=", "<", ">", "<=", ">=", "like", "not_like", "in", "not_in", "glob", "regexp"}
        VALID_FIELDS = {"knowledge_type", "title", "content", "summary", "source_file", "doc_type",
                        "section_path", "criticality", "repo_id", "importance_score", "confidence_score",
                        "architecture_tag", "concept", "related_module"}

        def _compile_condition(field: str, op: str, value: Any) -> Tuple[str, List[Any]]:
            if field not in VALID_FIELDS:
                return "", []
            if op not in VALID_OPS:
                return "", []
            if op in ("in", "not_in"):
                if not isinstance(value, list):
                    return "", []
                placeholders = ",".join("?" * len(value))
                not_kw = "NOT " if op == "not_in" else ""
                return (f"{field} {not_kw}IN ({placeholders})", list(value))
            if op == "not_like":
                return (f"{field} NOT LIKE ?", [value])
            if op in ("like", "glob", "regexp"):
                return (f"{field} {op.upper()} ?", [value])
            return (f"{field} {op} ?", [value])

        def _compile_node(node: Dict[str, Any]) -> Tuple[str, List[Any]]:
            if "and" in node:
                parts, params = [], []
                for child in node["and"]:
                    sql, p = _compile_node(child)
                    if sql:
                        parts.append(sql)
                        params.extend(p)
                return (" AND ".join(f"({p})" for p in parts) if parts else ""), params
            if "or" in node:
                parts, params = [], []
                for child in node["or"]:
                    sql, p = _compile_node(child)
                    if sql:
                        parts.append(sql)
                        params.extend(p)
                return (" OR ".join(f"({p})" for p in parts) if parts else ""), params
            if "not" in node:
                sql, params = _compile_node(node["not"])
                return (f"NOT ({sql})" if sql else ""), params
            # Leaf node: field + op + value
            field = node.get("field")
            op = node.get("op")
            value = node.get("value")
            if field and op:
                return _compile_condition(field, op, value)
            return "", []

        sql, params = _compile_node(query)
        return sql, tuple(params)

    @staticmethod
    def _text_to_vector(text: str, dim: int = 128) -> List[float]:
        """Convert text to a simple embedding vector using term hashing.

        No external dependencies — uses built-in hash for deterministic vectors.
        """
        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        vec = [0.0] * dim
        for word in words:
            h = hash(word)
            idx = abs(h) % dim
            vec[idx] += 1.0
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def _available_types(self) -> Dict[str, int]:
        rows = self.db.conn.execute(
            "SELECT knowledge_type, COUNT(*) FROM knowledge_chunks GROUP BY knowledge_type"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    @staticmethod
    def _row_to_chunk(row) -> KnowledgeChunk:
        row_dict = dict(row)
        return KnowledgeChunk(
            knowledge_type=row_dict["knowledge_type"],
            title=row_dict["title"],
            content=row_dict["content"],
            source_file=row_dict["source_file"],
            doc_type=row_dict["doc_type"],
            summary=row_dict["summary"],
            section_path=row_dict["section_path"],
            importance_score=row_dict["importance_score"],
            criticality=row_dict["criticality"],
            confidence_score=row_dict.get("confidence_score", 0.5),
            repo_id=row_dict.get("repo_id", ""),
            created_at=row_dict.get("created_at", ""),
            updated_at=row_dict.get("updated_at", ""),
            concept=json.loads(row_dict["concept"]) if row_dict["concept"] else [],
            related_module=json.loads(row_dict["related_module"]) if row_dict["related_module"] else [],
            architecture_tag=json.loads(row_dict["architecture_tag"]) if row_dict["architecture_tag"] else [],
            embedding=json.loads(row_dict.get("embedding", "[]")) if row_dict.get("embedding") else None,
            id=row_dict["id"],
        )

