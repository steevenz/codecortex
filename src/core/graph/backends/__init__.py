"""
Graph backend abstraction layer — unified interface for Kùzu, Neo4j, FalkorDB.

:project: CodeCortex
:package: Core.Graph.Backends
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from .base import GraphBackend, GraphSession, GraphResult
from .kuzu_backend import KuzuBackend
from .neo4j_backend import Neo4jBackend
from .falkordb_backend import FalkorDBBackend
from .supabase_backend import SupabaseBackend

__all__ = [
    "GraphBackend",
    "GraphSession",
    "GraphResult",
    "KuzuBackend",
    "Neo4jBackend",
    "FalkorDBBackend",
    "SupabaseBackend",
]
