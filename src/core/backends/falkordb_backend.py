"""
/**
 * @project   CodeCortex
 * @package   Core/Backends
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python, FalkorDB
 * * FalkorDBBackend — RedisGraph-compatible graph database (optional alternate).
 *   Supports both embedded (FalkorDB Lite) and remote TCP modes.
 */
"""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from .base import GraphBackend, GraphSession, GraphResult
from ..logging_config import get_logger

logger = get_logger(__name__)


class FalkorDBRecord(dict):
    """Dict wrapper providing .data() for Neo4j compat."""

    def data(self) -> Dict[str, Any]:
        return dict(self)


class FalkorDBResultWrapper:
    """Wraps FalkorDB result to satisfy GraphResult."""

    def __init__(self, result: Any):
        self.result = result

    def single(self) -> Optional[Dict[str, Any]]:
        data = self.data()
        return FalkorDBRecord(data[0]) if data else None

    def data(self) -> List[Dict[str, Any]]:
        if not hasattr(self.result, "result_set"):
            return []
        records: List[Dict[str, Any]] = []
        if hasattr(self.result, "header") and self.result.header:
            headers = self.result.header
            for row in self.result.result_set:
                row_dict: Dict[str, Any] = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        if isinstance(header, (list, tuple)) and len(header) > 1:
                            header_name = header[1]
                            if isinstance(header_name, bytes):
                                header_name = header_name.decode("utf-8")
                        else:
                            header_name = str(header)
                        row_dict[header_name] = row[i]
                records.append(FalkorDBRecord(row_dict))
        elif hasattr(self.result, "result_set"):
            for row in self.result.result_set:
                if isinstance(row, (list, tuple)) and len(row) == 1:
                    records.append(FalkorDBRecord({"value": row[0]}))
                else:
                    records.append(FalkorDBRecord({"value": row}))
        return records

    def consume(self) -> "FalkorDBResultWrapper":
        return self

    def __iter__(self):
        return iter(self.data())


class FalkorDBSessionWrapper:
    """Wraps FalkorDB graph object for session-like interface."""

    def __init__(self, graph: Any):
        self.graph = graph

    def run(self, query: str, **parameters: Any) -> GraphResult:
        if parameters:
            result = self.graph.query(query, parameters)
        else:
            result = self.graph.query(query)
        return FalkorDBResultWrapper(result)

    def __enter__(self) -> GraphSession:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


class FalkorDBBackend(GraphBackend):
    """
    FalkorDB graph backend. Connects via TCP to external instance.
    For embedded mode, use FalkorDB Lite with Unix sockets (Linux/macOS only).
    """

    _instance: Optional["FalkorDBBackend"] = None
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

        self.host = os.getenv("FALKORDB_HOST", "localhost")
        self.port = int(os.getenv("FALKORDB_PORT", "6379"))
        self.password = os.getenv("FALKORDB_PASSWORD") or None
        self.username = os.getenv("FALKORDB_USERNAME") or None
        self.ssl = os.getenv("FALKORDB_SSL", "false").lower() in ("true", "1", "yes")
        self.graph_name = os.getenv("FALKORDB_GRAPH_NAME", "codegraph")
        self._driver: Any = None
        self._graph: Any = None
        self._initialized = True

    # -- GraphBackend API ---------------------------------------------------

    def get_session(self) -> GraphSession:
        if self._graph is None:
            self._connect()
        return FalkorDBSessionWrapper(self._graph)

    def create_schema(self) -> None:
        # FalkorDB is schemaless; no explicit CREATE needed.
        # Fulltext indexes can be created via CALL db.idx.fulltext.createNodeIndex
        if self._graph is None:
            self._connect()
        try:
            for label in ["Function", "Class"]:
                self._graph.query(
                    f"CALL db.idx.fulltext.createNodeIndex('{label}', 'name', 'source', 'docstring')"
                )
        except Exception as e:
            logger.warning(f"FalkorDB fulltext index warning (may already exist): {e}")
        logger.info("FalkorDB schema verified (schemaless backend)")

    def is_connected(self) -> bool:
        if self._graph is None:
            return False
        try:
            self._graph.query("RETURN 1")
            return True
        except Exception:
            return False

    def get_backend_type(self) -> str:
        return "falkordb"

    def close(self) -> None:
        if self._driver is not None:
            logger.info("Closing FalkorDB connection")
            self._driver = None
            self._graph = None

    @staticmethod
    def validate_config() -> Tuple[bool, Optional[str]]:
        host = os.getenv("FALKORDB_HOST")
        if not host:
            return False, "FALKORDB_HOST environment variable is not set."
        port_str = os.getenv("FALKORDB_PORT", "6379")
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                return False, f"FALKORDB_PORT must be between 1 and 65535, got {port}."
        except ValueError:
            return False, f"FALKORDB_PORT must be a number, got '{port_str}'."
        return True, None

    @staticmethod
    def test_connection() -> Tuple[bool, Optional[str]]:
        try:
            from falkordb import FalkorDB
        except ImportError:
            return False, "FalkorDB client not installed. Run: pip install falkordb"
        is_valid, err = FalkorDBBackend.validate_config()
        if not is_valid:
            return False, err
        try:
            host = os.getenv("FALKORDB_HOST", "localhost")
            port = int(os.getenv("FALKORDB_PORT", "6379"))
            password = os.getenv("FALKORDB_PASSWORD") or None
            username = os.getenv("FALKORDB_USERNAME") or None
            ssl = os.getenv("FALKORDB_SSL", "false").lower() in ("true", "1", "yes")
            graph_name = os.getenv("FALKORDB_GRAPH_NAME", "codegraph")
            kwargs: Dict[str, Any] = {"host": host, "port": port}
            if password:
                kwargs["password"] = password
            if username:
                kwargs["username"] = username
            if ssl:
                kwargs["ssl"] = True
            db = FalkorDB(**kwargs)
            graph = db.select_graph(graph_name)
            graph.query("RETURN 1")
            return True, None
        except Exception as e:
            return False, f"FalkorDB connection test failed: {e}"

    # -- Internals ----------------------------------------------------------

    def _connect(self) -> None:
        if self._graph is not None:
            return
        with self._lock:
            if self._graph is not None:
                return
            try:
                from falkordb import FalkorDB
            except ImportError as e:
                raise ImportError("falkordb package not installed. Run: pip install falkordb") from e

            kwargs: Dict[str, Any] = {"host": self.host, "port": self.port}
            if self.password:
                kwargs["password"] = self.password
            if self.username:
                kwargs["username"] = self.username
            if self.ssl:
                kwargs["ssl"] = True

            logger.info(f"Connecting to FalkorDB at {self.host}:{self.port} (ssl={self.ssl})")
            self._driver = FalkorDB(**kwargs)
            self._graph = self._driver.select_graph(self.graph_name)
            self._graph.query("RETURN 1")
            logger.info(f"FalkorDB connection established (graph={self.graph_name})")
