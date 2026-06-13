"""
Vector Embeddings & Semantic Search using sentence-transformers.
Features:
- Lazy model loading (singleton, loaded on first use)
- Code-aware chunking (functions, classes as separate chunks)
- SQLite storage (embeddings as numpy BLOBs)
- Cosine similarity search in-memory
- FALLBACK: if model unavailable, returns empty results gracefully.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Embeddings
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""

import logging
import sqlite3
import json
import pickle
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger("CodeCortex.CodeIndex.Embeddings")

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimension

_model_instance = None

def _get_model():
    """Lazy-load the sentence-transformers model (singleton)."""
    global _model_instance
    if _model_instance is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: all-MiniLM-L6-v2...")
            _model_instance = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            return None
    return _model_instance

def generate_embedding(text: str) -> Optional[np.ndarray]:
    """Generate embedding vector for a text string."""
    model = _get_model()
    if model is None:
        return None
    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two normalized vectors."""
    return float(np.dot(a, b))

def chunk_code(file_path: str, content: str) -> List[Dict[str, Any]]:
    """
    Split code into semantic chunks for embedding.
    Each function, class, and top-level code block becomes a chunk.
    """
    chunks = []
    lines = content.split("\n")
    current_chunk = []
    current_start = 1

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Detect function/class definition start
        if stripped.startswith(("def ", "class ", "async def ", "@")):
            if current_chunk and len("\n".join(current_chunk)) > 20:
                chunks.append({
                    "file_path": file_path,
                    "start_line": current_start,
                    "end_line": i - 1,
                    "content": "\n".join(current_chunk),
                })
            current_chunk = [line]
            current_start = i
        else:
            current_chunk.append(line)

    if current_chunk and len("\n".join(current_chunk)) > 20:
        chunks.append({
            "file_path": file_path,
            "start_line": current_start,
            "end_line": len(lines),
            "content": "\n".join(current_chunk),
        })

    return chunks

class EmbeddingStore:
    """
    Manages embedding storage and retrieval using SQLite.

    Table: embeddings
    - id: TEXT PRIMARY KEY
    - file_path: TEXT
    - chunk_index: INTEGER
    - start_line: INTEGER
    - end_line: INTEGER
    - content: TEXT
    - embedding: BLOB (pickled numpy array)
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    start_line INTEGER,
                    end_line INTEGER,
                    content TEXT,
                    embedding BLOB
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_file ON embeddings(file_path)")
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    def store(self, file_path: str, chunks: List[Dict], repo_id: str):
        """Store embeddings for a file's chunks."""
        conn = sqlite3.connect(self.db_path)
        import uuid
        for i, chunk in enumerate(chunks):
            emb = chunk.get("embedding")
            emb_blob = pickle.dumps(emb) if emb is not None else None
            conn.execute(
                "INSERT OR REPLACE INTO embeddings (id, file_path, chunk_index, start_line, end_line, content, embedding) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"{repo_id}_{file_path}_{i}", file_path, i,
                 chunk.get("start_line"), chunk.get("end_line"),
                 chunk.get("content"), emb_blob)
            )
        conn.commit()
        conn.close()

    def clear_file(self, file_path: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM embeddings WHERE file_path = ?", (file_path,))
        conn.commit()
        conn.close()

    def clear_repo(self, repo_id: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM embeddings WHERE id LIKE ?", (f"{repo_id}_%",))
        conn.commit()
        conn.close()

    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Dict]:
        """
        Search for similar chunks using cosine similarity.
        Loads all embeddings into memory for search.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT file_path, chunk_index, start_line, end_line, content, embedding FROM embeddings WHERE embedding IS NOT NULL"
        )
        results = []
        for row in cursor:
            if row[5] is None:
                continue
            stored_emb = pickle.loads(row[5])
            sim = cosine_similarity(query_embedding, stored_emb)
            results.append({
                "file_path": row[0],
                "chunk_index": row[1],
                "start_line": row[2],
                "end_line": row[3],
                "content": row[4],
                "similarity": round(float(sim), 4),
            })
        conn.close()

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    @property
    def count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
        conn.close()
        return row[0] if row else 0

    def close(self):
        pass

def index_file_embeddings(file_path: str, content: str, db_path: str, repo_id: str) -> int:
    """
    Generate and store embeddings for a file. Returns chunk count.
    """
    chunks = chunk_code(file_path, content)
    if not chunks:
        return 0

    for chunk in chunks:
        emb = generate_embedding(chunk["content"])
        chunk["embedding"] = emb

    store = EmbeddingStore(db_path)
    store.store(file_path, chunks, repo_id)
    return len(chunks)

def semantic_search(query: str, db_path: str, top_k: int = 10) -> List[Dict]:
    """
    Search codebase using semantic similarity.
    Returns list of {file_path, content, similarity, ...}
    """
    query_emb = generate_embedding(query)
    if query_emb is None:
        return []

    store = EmbeddingStore(db_path)
    return store.search(query_emb, top_k=top_k)
