"""
Domain CodeIndex – Entrypoint for modularised symbol indexing.

:project: CodeCortex
:package: Modules.Codeindex
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

from .services.indexer import Indexer

__all__ = ["Indexer"]
