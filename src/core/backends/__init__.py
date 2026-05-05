"""
/**
 * @project   CodeCortex
 * @package   Core/Backends
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Graph backend abstraction layer — unified interface for Kùzu, Neo4j, FalkorDB.
 */
"""

from .base import GraphBackend, GraphSession, GraphResult
from .kuzu_backend import KuzuBackend
from .neo4j_backend import Neo4jBackend
from .falkordb_backend import FalkorDBBackend

__all__ = [
    "GraphBackend",
    "GraphSession",
    "GraphResult",
    "KuzuBackend",
    "Neo4jBackend",
    "FalkorDBBackend",
]
