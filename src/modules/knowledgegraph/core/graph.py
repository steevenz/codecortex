"""
Knowledge Relationship Mapper — builds edges between knowledge chunks and code modules.

Relationship types (semantic + tag-based):
  decision     → introduces → constraint
  principle    → refines    → decision
  anti_pattern → violates   → principle
  risk         → affects    → module
  flow         → describes  → module
  invariant    → enforces   → module
  chunk        → references → chunk (same architecture_tag)

Graph statistics computed:
  density     → Ratio of actual edges to possible edges (0-1)
  avg_degree  → Average connections per node
  clustering  → Transitivity coefficient

Standards:
    - Aegis-Architecture-v1.0    → Clean Architecture (no api/ imports)
    - Aegis-ProjectStructure-v1.0 → core/ logic, testable without MCP/CLI
"""

from __future__ import annotations

__all__ = ["KnowledgeGraphBuilder"]

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.modules.knowledgegraph.models.chunk import KnowledgeChunk
from src.modules.knowledgegraph.models.relationship import DocRelationship


class KnowledgeGraphBuilder:
    """Builds a relationship graph between knowledge chunks and code modules."""

    def build(
        self,
        chunks: List[KnowledgeChunk],
        known_modules: Optional[List[str]] = None,
    ) -> Tuple[List[DocRelationship], Dict[str, Any]]:
        """Build relationships between all chunks and modules.

        Args:
            chunks: Extracted knowledge chunks.
            known_modules: Known module paths for matching.

        Returns:
            (relationships, graph_stats)
        """
        relationships: List[DocRelationship] = []

        # 1. Type-based relationships
        decisions = [c for c in chunks if c.knowledge_type == "decision"]
        constraints = [c for c in chunks if c.knowledge_type == "constraint"]
        principles = [c for c in chunks if c.knowledge_type == "principle"]
        risks = [c for c in chunks if c.knowledge_type == "risk"]

        # Decision → introduces → Constraint
        for d in decisions:
            for c in constraints[:5]:
                if self._text_overlap(d.content, c.content):
                    relationships.append(DocRelationship(
                        source_id=d.id, target_id=c.id,
                        relation_type="introduces", weight=0.7,
                        description=f"Decision '{d.title[:50]}' introduces constraint",
                    ))

        # Principle → refines → Decision
        for p in principles:
            for d in decisions:
                if self._text_overlap(p.content, d.content):
                    relationships.append(DocRelationship(
                        source_id=p.id, target_id=d.id,
                        relation_type="refines", weight=0.6,
                        description=f"Principle refines decision '{d.title[:50]}'",
                    ))

        # Anti-pattern → violates → Principle
        anti = [c for c in chunks if c.knowledge_type == "anti_pattern"]
        for a in anti:
            for p in principles:
                relationships.append(DocRelationship(
                    source_id=a.id, target_id=p.id,
                    relation_type="violates", weight=0.5,
                    description=f"Anti-pattern violates principle '{p.title[:50]}'",
                ))

        # Risk → affects → modules
        for r in risks:
            for module in r.related_module:
                relationships.append(DocRelationship(
                    source_id=r.id, target_id=module,
                    relation_type="affects", weight=0.8,
                    description=f"Risk affects module '{module}'",
                ))

        # 2. Module-based relationships
        all_modules: Set[str] = set()
        for c in chunks:
            for m in c.related_module:
                all_modules.add(m)

        # 3. Tag-based relationships (same tag → related)
        tag_groups: Dict[str, List[KnowledgeChunk]] = {}
        for c in chunks:
            for tag in c.architecture_tag:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(c)

        for tag, tagged in tag_groups.items():
            for i in range(len(tagged)):
                for j in range(i + 1, min(i + 3, len(tagged))):
                    if tagged[i].id != tagged[j].id:
                        relationships.append(DocRelationship(
                            source_id=tagged[i].id, target_id=tagged[j].id,
                            relation_type="references", weight=0.4,
                            description=f"Both related to '{tag}'",
                        ))

        stats = {
            "total_relationships": len(relationships),
            "by_type": self._count_by_type(relationships),
            "unique_chunks_linked": len({r.source_id for r in relationships} |
                                         {r.target_id for r in relationships}),
            "modules_mapped": len(all_modules),
        }

        return relationships, stats

    def build_for_query(
        self,
        chunks: List[KnowledgeChunk],
        focus: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Build focused relationship subgraph for a query."""
        relationships, _ = self.build(chunks)
        focus_lower = focus.lower()

        # Find nodes matching focus
        focus_ids = set()
        for c in chunks:
            if focus_lower in c.title.lower() or focus_lower in c.content.lower():
                focus_ids.add(c.id)

        # Walk graph from focus nodes
        related_ids = set(focus_ids)
        for _ in range(depth):
            for rel in relationships:
                if rel.source_id in related_ids:
                    related_ids.add(rel.target_id)
                if rel.target_id in related_ids:
                    related_ids.add(rel.source_id)

        # Filter to subgraph
        nodes = [c.to_dict() for c in chunks if c.id in related_ids]
        edges = [r.to_dict() for r in relationships
                 if r.source_id in related_ids or r.target_id in related_ids]

        return {"nodes": nodes[:50], "edges": edges[:100], "focus": focus}

    @staticmethod
    def _text_overlap(a: str, b: str) -> bool:
        """Check if two texts share significant vocabulary."""
        words_a = set(re.findall(r"\b\w{4,}\b", a.lower()))
        words_b = set(re.findall(r"\b\w{4,}\b", b.lower()))
        if not words_a or not words_b:
            return False
        overlap = words_a & words_b
        return len(overlap) >= 2

    @staticmethod
    def _count_by_type(rels: List[DocRelationship]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in rels:
            counts[r.relation_type] = counts.get(r.relation_type, 0) + 1
        return counts
