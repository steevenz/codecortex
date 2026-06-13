"""
Domain CodeGraph – Entrypoint for modularised relationship resolution.

:project: CodeCortex
:package: Modules.Codegraph
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeGraph-v1.0
"""

from .services.graph import Graph

__all__ = ["Graph"]
