"""
DocRelationship DTO — data transfer object for knowledge graph edges.

Represents relationships between knowledge chunks or between chunks and code modules.
Follows DTO Boundary standard with to_dict() serialization.

Standards:
    - CODDY-Architecture-v1.0    → DTO Boundaries
    - CODDY-ProjectStructure-v1.0 → models/ requirements
"""

from __future__ import annotations

__all__ = ["DocRelationship"]

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class DocRelationship:
    """A relationship between two knowledge chunks or between a chunk and a code module."""

    source_id: str
    target_id: str
    relation_type: str  # constrains, introduces, mitigates, violates, depends_on, refines, describes, references, affects
    weight: float = 1.0
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    direction: str = "directed"

    RELATION_TYPES = {
        "constrains": "One item constrains another (e.g., constraint → module)",
        "introduces": "One introduces another (e.g., decision → constraint)",
        "mitigates": "One mitigates another (e.g., principle → risk)",
        "violates": "One violates another (e.g., anti-pattern → principle)",
        "depends_on": "One depends on another",
        "refines": "One refines another (e.g., principle → decision)",
        "describes": "One describes another (e.g., doc → module)",
        "references": "One references another",
        "affects": "One affects another (e.g., change → risk)",
        "implements": "One implements another (e.g., code → decision)",
    }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "relation": self.relation_type,
            "weight": self.weight,
            "direction": self.direction,
            "description": self.description[:100],
            "created_at": self.created_at,
        }
