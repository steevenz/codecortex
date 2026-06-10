"""
Golden Knowledge Store — persists architectural principles, coding conventions,
important invariants, domain assumptions, and critical flows.

Provides structured context for AI coders: "this project follows DDD",
"all public functions MUST have type hints", "User must own Organization".

:project: CodeCortex
:package: Modules.Codegraph.Core.Golden_knowledge
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CodeCortex.CodeGraph.GoldenKnowledge")

KNOWLEDGE_TYPES = {
    "principle": "Core architectural principle",
    "convention": "Coding convention / standard",
    "invariant": "Important invariant / rule",
    "assumption": "Domain assumption",
    "flow": "Critical execution flow",
    "decision": "Architectural decision",
}


class GoldenKnowledge:
    """A single golden knowledge entry."""

    def __init__(
        self,
        entry_type: str,
        content: str,
        source: str = "",
        applies_to: Optional[List[str]] = None,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
    ):
        self.entry_type = entry_type
        self.content = content
        self.source = source
        self.applies_to = applies_to or []
        self.confidence = min(1.0, max(0.0, confidence))
        self.tags = tags or []
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.entry_type,
            "type_label": KNOWLEDGE_TYPES.get(self.entry_type, self.entry_type),
            "content": self.content,
            "source": self.source,
            "applies_to": self.applies_to,
            "confidence": self.confidence,
            "tags": self.tags,
        }


class GoldenKnowledgeStore:
    """Persistent store for golden knowledge extracted from codebases.

    Sources:
    - ADR documents (architectural decisions → principles)
    - Coding standard docs (conventions)
    - Code analysis results (invariants, flows)
    - PRD requirements (domain assumptions)

    Usage:
        store = GoldenKnowledgeStore(db)
        store.store_from_adr("/path/to/adr.md")
        ctx = store.get_context_for_task("refactor payment service")
    """

    def __init__(self, db):
        self.db = db
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS golden_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT DEFAULT '',
                applies_to TEXT DEFAULT '[]',
                confidence REAL DEFAULT 1.0,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self.db.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_gk_type ON golden_knowledge(entry_type)"
        )
        self.db.conn.commit()

    def store(self, entry: GoldenKnowledge) -> int:
        """Store a golden knowledge entry. Returns entry ID."""
        cursor = self.db.conn.execute(
            """INSERT INTO golden_knowledge
               (entry_type, content, source, applies_to, confidence, tags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.entry_type, entry.content, entry.source,
                str(entry.applies_to), entry.confidence,
                str(entry.tags), entry.created_at, entry.created_at,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def store_from_adr(self, file_path: str) -> List[int]:
        """Extract and store knowledge from an ADR document."""
        ids = []
        path = Path(file_path)
        if not path.exists():
            return ids

        from src.modules.codeanalysis.core.documentation import DocumentParser
        artifact = DocumentParser.parse_file(str(path))

        for decision in artifact.decisions:
            if decision.decision:
                entry = GoldenKnowledge(
                    entry_type="decision",
                    content=decision.decision[:500],
                    source=file_path,
                    applies_to=artifact.referenced_files[:10],
                    confidence=0.8,
                    tags=["adr"],
                )
                ids.append(self.store(entry))

        return ids

    def get_by_type(self, entry_type: str) -> List[Dict[str, Any]]:
        """Get all entries of a specific type."""
        rows = self.db.conn.execute(
            "SELECT * FROM golden_knowledge WHERE entry_type = ? ORDER BY confidence DESC",
            (entry_type,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_relevant(self, context: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get entries relevant to a context string (keyword matching)."""
        keywords = set(re.sub(r"[^\w\s]", "", context.lower()).split())
        keywords = {k for k in keywords if len(k) > 3}

        if not keywords:
            return self._all(limit)

        all_entries = self._all(100)
        scored = []
        for entry in all_entries:
            content_lower = (entry["content"] + " " + " ".join(entry.get("tags", []))).lower()
            applies = " ".join(entry.get("applies_to", [])).lower()
            score = sum(1 for k in keywords if k in content_lower or k in applies)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    def get_context_for_task(self, task: str) -> str:
        """Build a context string for an AI coder task.

        Returns a human-readable summary of relevant golden knowledge.
        """
        relevant = self.get_relevant(task)
        if not relevant:
            return ""

        lines = ["## Golden Knowledge Context\n"]
        for entry in relevant:
            tlabel = KNOWLEDGE_TYPES.get(entry["type"], entry["type"])
            confidence = "✓" if entry["confidence"] >= 0.8 else "~"
            lines.append(f"- [{confidence}] **{tlabel}**: {entry['content'][:200]}")
            if entry.get("source"):
                lines[-1] += f" *({entry['source']})*"

        return "\n".join(lines)

    def extract_from_repo(self, repo_path: str) -> Dict[str, Any]:
        """Auto-extract golden knowledge from a repository.

        Sources:
        1. ADR files in docs/adr/
        2. Coding standard files
        3. Analysis results (entry points, architecture)
        """
        root = Path(repo_path)
        stored = {"principles": 0, "conventions": 0, "decisions": 0}

        # 1. ADR files
        for adr_path in root.rglob("*adr*"):
            if adr_path.is_file() and adr_path.suffix in (".md", ".rst"):
                ids = self.store_from_adr(str(adr_path))
                stored["decisions"] += len(ids)

        # 2. Standard/convention files
        for std_pattern in ("*standard*", "*convention*", "*guideline*"):
            for fp in root.rglob(std_pattern):
                if fp.is_file() and fp.suffix in (".md", ".rst", ".txt"):
                    entry = GoldenKnowledge(
                        entry_type="convention",
                        content=f"Coding standard: {fp.stem.replace('-', ' ').title()}",
                        source=str(fp),
                        confidence=0.7,
                        tags=["auto_extracted"],
                    )
                    self.store(entry)
                    stored["conventions"] += 1

        logger.info(f"Golden knowledge extracted: {stored}")
        return stored

    def summary(self) -> Dict[str, Any]:
        """Get summary of all stored golden knowledge."""
        rows = self.db.conn.execute(
            "SELECT entry_type, COUNT(*) as count FROM golden_knowledge GROUP BY entry_type"
        ).fetchall()
        by_type = {r["entry_type"]: r["count"] for r in rows}
        total = sum(by_type.values()) if by_type else 0

        return {
            "total_entries": total,
            "by_type": by_type,
            "types": KNOWLEDGE_TYPES,
        }

    def _all(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self.db.conn.execute(
            "SELECT * FROM golden_knowledge ORDER BY confidence DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        import ast
        return {
            "id": row["id"],
            "type": row["entry_type"],
            "content": row["content"],
            "source": row["source"],
            "applies_to": ast.literal_eval(row["applies_to"]) if row["applies_to"] else [],
            "confidence": row["confidence"],
            "tags": ast.literal_eval(row["tags"]) if row["tags"] else [],
            "created_at": row["created_at"],
        }
