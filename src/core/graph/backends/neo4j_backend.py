"""
Neo4jBackend — Remote graph database (optional alternate backend).
Ported from legacy codegraph database.py with Aegis-compliant structure.

:project: CodeCortex
:package: Core.Graph.Backends.Neo4j_backend
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import os
import re
import socket
import threading
from typing import Any, Dict, List, Optional, Tuple

from .base import GraphBackend, GraphSession, GraphResult
from src.core.logging import get_logger

logger = get_logger(__name__)

class Neo4jRecord(dict):
    """Dict wrapper providing .data() for compat."""

    def data(self) -> Dict[str, Any]:
        return dict(self)

class Neo4jResultWrapper:
    """Wraps neo4j.BoltStatementResult."""

    def __init__(self, result: Any):
        self.result = result

    def single(self) -> Optional[Dict[str, Any]]:
        rec = self.result.single()
        return Neo4jRecord(rec.data()) if rec else None

    def data(self) -> List[Dict[str, Any]]:
        return [Neo4jRecord(r.data()) for r in self.result]

    def consume(self) -> "Neo4jResultWrapper":
        self.result.consume()
        return self

    def __iter__(self):
        return iter(self.data())

class Neo4jSessionWrapper:
    """Wraps neo4j.Session."""

    def __init__(self, session: Any):
        self.session = session

    def run(self, query: str, **parameters: Any) -> GraphResult:
        return Neo4jResultWrapper(self.session.run(query, **parameters))

    def __enter__(self) -> GraphSession:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.session.close()

class Neo4jBackend(GraphBackend):
    """
    Neo4j graph backend. Reads credentials from environment variables.
    """

    _instance: Optional["Neo4jBackend"] = None
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

        self.uri = os.getenv("NEO4J_URI")
        self.username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv("NEO4J_DATABASE")
        self._driver: Any = None
        self._initialized = True

    # -- GraphBackend API ---------------------------------------------------

    def get_session(self) -> GraphSession:
        if self._driver is None:
            self._connect()
        kwargs: Dict[str, Any] = {}
        if self.database:
            kwargs["database"] = self.database
        return Neo4jSessionWrapper(self._driver.session(**kwargs))

    def create_schema(self) -> None:
        if self._driver is None:
            self._connect()
        with self._driver.session() as session:
            try:
                session.run("CREATE CONSTRAINT repository_path IF NOT EXISTS FOR (r:Repository) REQUIRE r.path IS UNIQUE")
                session.run("CREATE CONSTRAINT path IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE")
                session.run("CREATE CONSTRAINT directory_path IF NOT EXISTS FOR (d:Directory) REQUIRE d.path IS UNIQUE")
                session.run("CREATE CONSTRAINT function_unique IF NOT EXISTS FOR (f:Function) REQUIRE (f.name, f.path, f.line_number) IS UNIQUE")
                session.run("CREATE CONSTRAINT class_unique IF NOT EXISTS FOR (c:Class) REQUIRE (c.name, c.path, c.line_number) IS UNIQUE")
                session.run("CREATE FULLTEXT INDEX code_search_index IF NOT EXISTS FOR (n:Function|Class|Variable) ON EACH [n.name, n.source, n.docstring]")
                logger.info("Neo4j schema verified/created successfully")
            except Exception as e:
                logger.warning(f"Neo4j schema creation warning: {e}")

    def is_connected(self) -> bool:
        if self._driver is None:
            return False
        try:
            kwargs: Dict[str, Any] = {}
            if self.database:
                kwargs["database"] = self.database
            with self._driver.session(**kwargs) as s:
                s.run("RETURN 1").consume()
            return True
        except Exception:
            return False

    def get_backend_type(self) -> str:
        return "neo4j"

    def close(self) -> None:
        if self._driver is not None:
            logger.info("Closing Neo4j driver")
            self._driver.close()
            self._driver = None

    @staticmethod
    def validate_config() -> Tuple[bool, Optional[str]]:
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        if not all([uri, username, password]):
            return False, "NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD must be set via environment variables."

        uri_pattern = r"^(neo4j|neo4j\+s|neo4j\+ssc|bolt|bolt\+s|bolt\+ssc)://[^:]+(:\d+)?$"
        if not re.match(uri_pattern, uri):
            return False, f"Invalid Neo4j URI format: {uri}. Expected: neo4j://host:port or bolt://host:port"
        return True, None

    @staticmethod
    def test_connection() -> Tuple[bool, Optional[str]]:
        is_valid, err = Neo4jBackend.validate_config()
        if not is_valid:
            return False, err
        try:
            from neo4j import GraphDatabase
            uri = os.getenv("NEO4J_URI")
            username = os.getenv("NEO4J_USERNAME", "neo4j")
            password = os.getenv("NEO4J_PASSWORD")
            driver = GraphDatabase.driver(uri, auth=(username, password))
            with driver.session() as s:
                s.run("RETURN 1").consume()
            driver.close()
            return True, None
        except Exception as e:
            return False, f"Neo4j connection test failed: {e}"

    # -- Internals ----------------------------------------------------------

    def _connect(self) -> None:
        if self._driver is not None:
            return
        with self._lock:
            if self._driver is not None:
                return
            try:
                from neo4j import GraphDatabase
            except ImportError as e:
                raise ImportError("neo4j package not installed. Run: pip install neo4j") from e

            if not all([self.uri, self.username, self.password]):
                raise ValueError("Neo4j credentials missing. Set NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD.")

            logger.info(f"Creating Neo4j driver connection to {self.uri}")
            self._driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            try:
                with self._driver.session() as s:
                    s.run("RETURN 1").consume()
                logger.info("Neo4j connection established successfully")
            except Exception as e:
                logger.error(f"Neo4j connection test failed: {e}")
                self._driver.close()
                self._driver = None
                raise
