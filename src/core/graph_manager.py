"""
/**
 * @project   CodeCortex
 * @package   Core/GraphManager
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * GraphManager — Singleton backend selector. Delegates graph topology to
 *   Kùzu (default), Neo4j, or FalkorDB while SQLite retains metadata.
 */
"""

from __future__ import annotations

import os
import threading
from typing import Optional

from .backends.base import GraphBackend
from .backends.kuzu_backend import KuzuBackend
from .backends.neo4j_backend import Neo4jBackend
from .backends.falkordb_backend import FalkorDBBackend
from .logging_config import get_logger

logger = get_logger(__name__)

# Env-var override chain: CODECORTEX_GRAPH_BACKEND > config > default('kuzu')
BACKEND_REGISTRY: dict[str, type[GraphBackend]] = {
    "kuzu": KuzuBackend,
    "kuzudb": KuzuBackend,
    "neo4j": Neo4jBackend,
    "falkordb": FalkorDBBackend,
}


class _NoOpResult:
    def single(self):
        return None

    def data(self):
        return []

    def consume(self):
        return None

    def __iter__(self):
        return iter([])


class _NoOpSession:
    def run(self, query: str, **parameters):
        return _NoOpResult()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None


class NoOpBackend(GraphBackend):
    def get_session(self):
        return _NoOpSession()

    def create_schema(self) -> None:
        return None

    def is_connected(self) -> bool:
        return True

    def get_backend_type(self) -> str:
        return "none"

    def close(self) -> None:
        return None

    @staticmethod
    def validate_config():
        return True, None

    @staticmethod
    def test_connection():
        return True, None


BACKEND_REGISTRY["none"] = NoOpBackend
BACKEND_REGISTRY["noop"] = NoOpBackend


class GraphManager:
    """
    Singleton manager for the active graph backend.
    
    Usage:
        gm = GraphManager()
        with gm.get_backend().get_session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS cnt")
    """

    _instance: Optional["GraphManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = False
        self._backend: Optional[GraphBackend] = None
        self._backend_type: str = self._resolve_backend_type()
        self._initialized = True
        logger.info(f"GraphManager initialized with backend type: {self._backend_type}")

    def _resolve_backend_type(self) -> str:
        """Resolve backend type from env, config, or default."""
        env_backend = os.getenv("CODECORTEX_GRAPH_BACKEND", "").lower().strip()
        if env_backend and env_backend in BACKEND_REGISTRY:
            return env_backend
        return "none"

    def get_backend(self) -> GraphBackend:
        """Return (creating if necessary) the active GraphBackend instance."""
        if self._backend is not None:
            return self._backend

        with self._lock:
            if self._backend is not None:
                return self._backend

            backend_cls = BACKEND_REGISTRY.get(self._backend_type)
            if backend_cls is None:
                raise ValueError(
                    f"Unknown graph backend '{self._backend_type}'. "
                    f"Supported: {', '.join(BACKEND_REGISTRY.keys())}"
                )

            required = os.getenv("CODECORTEX_GRAPH_BACKEND_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"}

            try:
                is_valid, err = backend_cls.validate_config()
                if not is_valid:
                    raise ValueError(f"Backend '{self._backend_type}' configuration invalid: {err}")
                self._backend = backend_cls()
                logger.info(f"GraphBackend '{self._backend_type}' instantiated.")
                return self._backend
            except Exception as e:
                if required:
                    raise
                logger.warning(f"GraphBackend '{self._backend_type}' unavailable, falling back to 'none': {e}")
                self._backend_type = "none"
                self._backend = NoOpBackend()
                return self._backend

    def get_backend_type(self) -> str:
        return self._backend_type

    def test_connection(self) -> tuple[bool, Optional[str]]:
        """Test connectivity of the configured backend without instantiating it."""
        backend_cls = BACKEND_REGISTRY.get(self._backend_type)
        if backend_cls is None:
            return False, f"Unknown backend: {self._backend_type}"
        return backend_cls.test_connection()

    def close(self) -> None:
        if self._backend is not None:
            self._backend.close()
            self._backend = None
            logger.info("GraphManager closed active backend.")
