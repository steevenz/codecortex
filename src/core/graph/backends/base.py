"""
Abstract GraphBackend protocol — unified interface for Kùzu, Neo4j, FalkorDB.
Decouples graph persistence from domain logic. SQLite remains the metadata/cache layer.

:project: CodeCortex
:package: Core.Graph.Backends.Base
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Protocol, runtime_checkable
from contextlib import contextmanager

@runtime_checkable
class GraphResult(Protocol):
    """Protocol for graph query results (Neo4j/FalkorDB/Kùzu compatible)."""

    def single(self) -> Optional[Dict[str, Any]]:
        """Return first record as dict, or None."""
        ...

    def data(self) -> List[Dict[str, Any]]:
        """Return all records as list of dicts."""
        ...

    def consume(self) -> Any:
        """Mark result as consumed (Neo4j compat)."""
        ...

    def __iter__(self):
        ...

@runtime_checkable
class GraphSession(Protocol):
    """Protocol for graph database sessions."""

    def run(self, query: str, **parameters: Any) -> GraphResult:
        """Execute Cypher/query and return result wrapper."""
        ...

    def __enter__(self) -> GraphSession:
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        ...

class GraphBackend(ABC):
    """
    Abstract base for graph database backends.

    Implementations: KuzuBackend, Neo4jBackend, FalkorDBBackend.
    SQLite DatabaseManager handles metadata/manifest; this handles graph topology.
    """

    @abstractmethod
    def get_session(self) -> GraphSession:
        """Return a session context for executing queries."""
        raise NotImplementedError

    @abstractmethod
    def create_schema(self) -> None:
        """Create node/relationship constraints and indexes."""
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        """Health-check the underlying connection."""
        raise NotImplementedError

    @abstractmethod
    def get_backend_type(self) -> str:
        """Return canonical backend identifier string."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Close connections and release resources."""
        raise NotImplementedError

    @staticmethod
    def validate_config() -> Tuple[bool, Optional[str]]:
        """Validate environment / config for this backend. Returns (is_valid, error_message)."""
        return True, None

    @staticmethod
    def test_connection() -> Tuple[bool, Optional[str]]:
        """Test connectivity. Returns (is_connected, error_message)."""
        return True, None

    def __enter__(self) -> GraphBackend:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
