"""
Domain CodeIndex – Entrypoint for modularised symbol indexing.

:project: CodeCortex
:package: Modules.Codeindex
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""

from .services.indexer import Indexer

__all__ = ["Indexer"]
