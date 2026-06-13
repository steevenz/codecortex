"""
KnowledgeGraph Core — indexing (extraction + scoring) and graphing algorithms.

This package implements the core business logic of the KnowledgeGraph domain,
following Clean Architecture principles:
- No imports from api/ layer (circular dependency prevention)
- Uses DTOs from models/ for all data transfer
- Pattern-based extraction (no LLM dependency)
- Multi-dimension scoring with explicit weights

Public API:
    KnowledgeExtractor   → Extract 8 knowledge types from normalized text
    KnowledgeScorer      → 6-dimension importance + confidence scoring
    KnowledgeDedup       → Content fingerprint deduplication
    KnowledgeGraphBuilder→ Relationship mapping between knowledge chunks

Standards:
    - CODDY-Architecture-v1.0 (Lego Principle, DI/IoC, DTO Boundaries)
    - CODDY-ProjectStructure-v1.0 (core/ requirements)
"""

from .extraction import KnowledgeExtractor
from .classification import KnowledgeScorer, KnowledgeDedup
from .graph import KnowledgeGraphBuilder

__all__ = [
    "KnowledgeExtractor",
    "KnowledgeScorer",
    "KnowledgeDedup",
    "KnowledgeGraphBuilder",
]
