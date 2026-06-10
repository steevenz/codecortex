"""
GraphBackendManager – Singleton backend selector.
Delegates graph topology to Kùzu (default), Neo4j, or FalkorDB.

:project: CodeCortex
:package: Core.Graph.Manager
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import os
import threading
from typing import Optional

import circuitbreaker
from circuitbreaker import circuit

from .backends.base import GraphBackend
from .backends.kuzu_backend import KuzuBackend
from .backends.neo4j_backend import Neo4jBackend
from .backends.falkordb_backend import FalkorDBBackend
from .backends.supabase_backend import SupabaseBackend
from ..logging import get_logger

logger = get_logger(__name__)

BACKEND_REGISTRY: dict[str, type[GraphBackend]] = {
    "kuzu": KuzuBackend,
    "kuzudb": KuzuBackend,
    "neo4j": Neo4jBackend,
    "falkordb": FalkorDBBackend,
    "supabase": SupabaseBackend,
    "postgres": SupabaseBackend,
}

class GraphBackendManager:
    """
    Singleton manager for the active graph backend.

    Backend selection priority:
      1. CODECORTEX_GRAPH_BACKEND env var
      2. Default: kuzu
    """

    _instance: Optional["GraphBackendManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "GraphBackendManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        backend_name = os.getenv("CODECORTEX_GRAPH_BACKEND", "kuzu").lower()
        self._backend_name = backend_name
        self._backend: Optional[GraphBackend] = None
        self._initialized = True

    @property
    def backend(self) -> GraphBackend:
        if self._backend is None or not self._backend.is_connected():
            self._backend = self._create_backend()
        return self._backend

    def _create_backend(self) -> GraphBackend:
        backend_cls = BACKEND_REGISTRY.get(self._backend_name)
        if backend_cls is None:
            logger.warning(
                "[BACKEND_WARN] Unknown backend '%s', falling back to NoOp",
                self._backend_name,
                extra={"event_code": "BACKEND_WARN", "backend": self._backend_name},
            )
            from .session import NoOpBackend

            return NoOpBackend()

        backend = backend_cls()
        is_valid, error = backend.validate_config()
        if not is_valid:
            logger.warning(
                "[BACKEND_WARN] Backend '%s' invalid: %s, falling back to NoOp",
                self._backend_name,
                error,
                extra={"event_code": "BACKEND_WARN", "backend": self._backend_name, "error": error},
            )
            from .session import NoOpBackend

            return NoOpBackend()

        return backend

    def get_backend_type(self) -> str:
        return self.backend.get_backend_type()

    def get_backend(self) -> GraphBackend:
        return self.backend

    @circuit(failure_threshold=5, recovery_timeout=60)
    def execute_query(self, query: str, **parameters) -> Any:
        return self.backend.get_session().run(query, **parameters)

    def close(self):
        if self._backend is not None:
            self._backend.close()
            self._backend = None

    @staticmethod
    def reset():
        if GraphBackendManager._instance is not None:
            GraphBackendManager._instance.close()
            GraphBackendManager._instance = None

GraphManager = GraphBackendManager
