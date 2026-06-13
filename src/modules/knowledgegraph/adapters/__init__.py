"""
KnowledgeGraph Adapters — external service wrappers.

This package wraps all 3rd-party dependencies and external services,
following the Adapter Pattern:
    KnowledgeStore   → Dual-layer persistence (SQLite + GoldenKnowledgeStore)
    FormatParser     → Multi-format document parsing (docx, pdf, xlsx, pptx, csv, json, log)

Standards:
    - CODDY-Architecture-v1.0 (Adapter Pattern)
    - CODDY-ProjectStructure-v1.0 (adapters/ requirements)
"""

from .storage import KnowledgeStore
from .format_parser import FormatParser

__all__ = [
    "KnowledgeStore",
    "FormatParser",
]
