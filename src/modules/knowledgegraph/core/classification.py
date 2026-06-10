"""
Knowledge Classification — scores and enriches knowledge chunks with metadata.

6-Dimension Importance Scoring (weighted sum, explicit weights):
1. architectural_importance (weight: 0.30)
   → Keyword-based: high-impact keywords (+0.2 each) vs generic keywords (-0.1 each)
2. criticality (weight: 0.20)
   → Mapped from criticality level: high=1.0, medium=0.6, low=0.3
3. knowledge_type_weight (weight: 0.20)
   → constraint=0.9, invariant=0.9, risk=0.8, decision=0.7, principle=0.7, ...
4. concept_richness (weight: 0.10)
   → Number of domain concepts extracted / 5 (capped at 1.0)
5. module_relevance (weight: 0.10)
   → Number of related code modules / 3 (capped at 1.0)
6. content_density (weight: 0.10)
   → Content length / 500 characters (capped at 1.0)

Confidence Scoring (5 signals, averaged):
- Pattern specificity (explicit markers like **Constraint:**)
- Content length (longer = more reliable)
- Concept richness (domain term mentions)
- Module linkage (links to actual code paths)
- Architecture tags (categorized)

Standards:
    - Aegis-Architecture-v1.0    → Multi-dimension scoring with explicit weights
    - Aegis-ProjectStructure-v1.0 → core/ logic, testable without MCP/CLI
"""

from __future__ import annotations

__all__ = ["KnowledgeScorer", "KnowledgeDedup"]

import re
from typing import List, Set

from src.modules.knowledgegraph.models.chunk import KnowledgeChunk


class KnowledgeScorer:
    """Scores knowledge chunks across multiple dimensions for relevance ranking."""

    HIGH_IMPACT_KEYWORDS = [
        "architecture", "core", "foundation", "platform", "infrastructure",
        "security", "authentication", "authorization", "payment", "billing",
        "critical", "mandatory", "required", "compliance", "audit",
    ]

    GENERIC_KEYWORDS = [
        "overview", "introduction", "getting started", "welcome",
        "about this", "purpose of", "scope",
    ]

    def score(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        """Score a single knowledge chunk, updating importance_score."""
        scores = []

        # 1. Architectural importance (0.0 - 1.0)
        arch_score = self._score_architectural_importance(chunk)
        scores.append(arch_score * 0.30)

        # 2. Criticality boost
        crit_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
        crit_score = crit_map.get(chunk.criticality, 0.5)
        scores.append(crit_score * 0.20)

        # 3. Knowledge type weight
        type_weights = {
            "constraint": 0.9, "invariant": 0.9, "risk": 0.8,
            "decision": 0.7, "principle": 0.7, "anti_pattern": 0.6,
            "concept": 0.5, "flow": 0.5,
        }
        type_score = type_weights.get(chunk.knowledge_type, 0.5)
        scores.append(type_score * 0.20)

        # 4. Concept richness
        concept_score = min(1.0, len(chunk.concept) / 5)
        scores.append(concept_score * 0.10)

        # 5. Module relevance (has related modules = higher value)
        module_score = min(1.0, len(chunk.related_module) / 3)
        scores.append(module_score * 0.10)

        # 6. Content density (longer content tends to be more valuable)
        density_score = min(1.0, len(chunk.content) / 500)
        scores.append(density_score * 0.10)

        chunk.importance_score = round(sum(scores), 3)
        chunk.confidence_score = round(self._compute_confidence(chunk), 3)
        return chunk

    def score_batch(self, chunks: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        return [self.score(c) for c in chunks]

    def _score_architectural_importance(self, chunk: KnowledgeChunk) -> float:
        text = (chunk.title + " " + chunk.content).lower()
        high_count = sum(1 for kw in self.HIGH_IMPACT_KEYWORDS if kw in text)
        generic_count = sum(1 for kw in self.GENERIC_KEYWORDS if kw in text)
        score = min(1.0, (high_count * 0.2) - (generic_count * 0.1))
        return max(0.1, score)

    def _compute_confidence(self, chunk: KnowledgeChunk) -> float:
        """Compute extraction confidence based on signal quality indicators."""
        signals = []
        # Pattern specificity (has explicit markers like **Constraint:**)
        has_marker = any(marker in chunk.content.lower() for marker in [
            "**", "constraint:", "decision:", "principle:", "risk:", "invariant:"
        ])
        signals.append(0.8 if has_marker else 0.4)
        # Content length (longer = more context = more reliable)
        length_score = min(1.0, len(chunk.content) / 200)
        signals.append(length_score)
        # Concept richness (mentions specific domain terms)
        signals.append(min(1.0, len(chunk.concept) / 3))
        # Module linkage (links to actual code paths)
        signals.append(0.7 if chunk.related_module else 0.3)
        # Architecture tags (categorized)
        signals.append(0.6 if chunk.architecture_tag else 0.3)
        return sum(signals) / len(signals)


class KnowledgeDedup:
    """Deduplicate knowledge chunks by content fingerprint."""

    def __init__(self):
        self._seen: Set[str] = set()

    def dedup(self, chunks: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        unique = []
        for c in chunks:
            fp = c.content[:150].lower().strip()
            if fp not in self._seen:
                self._seen.add(fp)
                unique.append(c)
        return unique
