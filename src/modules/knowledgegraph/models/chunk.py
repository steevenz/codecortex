"""
KnowledgeChunk DTO — data transfer object for extracted engineering knowledge.

Follows DTO Boundary standard:
- No raw ORM models / HTTP requests leak across layers
- to_dict() truncates large fields for token economy
- Machine IDs: uuid.uuid4()[:12]

Standards:
    - Aegis-Architecture-v1.0    → DTO Boundaries, Codification
    - Aegis-ProjectStructure-v1.0 → models/ requirements
"""

from __future__ import annotations

__all__ = ["KnowledgeChunk", "KNOWLEDGE_TYPES"]

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

KNOWLEDGE_TYPES = {
    "concept": "Engineering concept or domain term",
    "constraint": "Constraint, rule, or invariant",
    "decision": "Architectural decision with rationale",
    "flow": "Process flow or lifecycle",
    "risk": "Risk, hotspot, or fragility",
    "invariant": "Business invariant or integrity rule",
    "anti_pattern": "Anti-pattern or practice to avoid",
    "principle": "Engineering principle or standard",
}

CRITICALITY_LEVELS = ["low", "medium", "high"]


@dataclass
class KnowledgeChunk:
    """A single unit of engineering knowledge extracted from documentation."""

    knowledge_type: str
    title: str
    content: str
    source_file: str
    doc_type: str = "unknown"
    summary: str = ""
    section_path: str = ""
    line_start: int = 0
    line_end: int = 0
    importance_score: float = 0.5
    criticality: str = "medium"
    concept: List[str] = field(default_factory=list)
    related_module: List[str] = field(default_factory=list)
    related_features: List[str] = field(default_factory=list)
    architecture_tag: List[str] = field(default_factory=list)
    id: str = ""
    embedding: Optional[List[float]] = None
    confidence_score: float = 0.5
    repo_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]

    @property
    def type_label(self) -> str:
        return KNOWLEDGE_TYPES.get(self.knowledge_type, self.knowledge_type)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "knowledge_type": self.knowledge_type,
            "type_label": self.type_label,
            "title": self.title,
            "content": self.content[:300],
            "summary": self.summary[:200],
            "source_file": self.source_file,
            "doc_type": self.doc_type,
            "section_path": self.section_path,
            "importance_score": self.importance_score,
            "criticality": self.criticality,
            "confidence_score": self.confidence_score,
            "repo_id": self.repo_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "concept": self.concept[:5],
            "related_module": self.related_module[:5],
            "related_features": self.related_features[:5],
            "architecture_tag": self.architecture_tag[:5],
            "relevance_score": None,
        }
