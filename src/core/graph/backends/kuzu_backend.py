"""
KuzuBackend — Embedded graph database (primary backend). Zero external server.
Ported from legacy codegraph database_kuzu.py with Aegis-compliant structure.

:project: CodeCortex
:package: Core.Graph.Backends.Kuzu_backend
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import os
import re
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import GraphBackend, GraphSession, GraphResult
from src.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Kùzu Result / Session wrappers (Neo4j-compatible facade)
# ---------------------------------------------------------------------------

class KuzuRecord(dict):
    """Dict wrapper providing .data() for Neo4j compat."""

    def data(self) -> Dict[str, Any]:
        return dict(self)

class KuzuResultWrapper:
    """Wraps kuzu.QueryResult to satisfy GraphResult protocol."""

    def __init__(self, result: Any):
        self.result = result

    def _data_raw(self) -> List[Dict[str, Any]]:
        if self.result is None:
            return []
        records: List[Dict[str, Any]] = []
        cols = self.result.get_column_names()
        while self.result.has_next():
            row = self.result.get_next()
            record: Dict[str, Any] = {}
            for i, val in enumerate(row):
                processed = self._process_value(val)
                record[cols[i]] = processed
            records.append(record)
        return records

    @staticmethod
    def _process_value(val: Any) -> Any:
        """Normalize Kùzu Node/Rel objects to plain dicts where possible."""
        cls_name = str(type(val).__name__)
        if "Node" in cls_name and hasattr(val, "get_properties"):
            props = val.get_properties()
            props.setdefault("_label", val.get_label_name() if hasattr(val, "get_label_name") else "")
            return props
        if "Rel" in cls_name and hasattr(val, "get_properties"):
            props = val.get_properties()
            props.setdefault("_type", val.get_label_name() if hasattr(val, "get_label_name") else "")
            return props
        return val

    def single(self) -> Optional[Dict[str, Any]]:
        rows = self._data_raw()
        return KuzuRecord(rows[0]) if rows else None

    def data(self) -> List[Dict[str, Any]]:
        return [KuzuRecord(r) for r in self._data_raw()]

    def consume(self) -> "KuzuResultWrapper":
        return self

    def __iter__(self):
        return iter(self.data())

class KuzuSessionWrapper:
    """Wraps kuzu.Connection to satisfy GraphSession protocol."""

    def __init__(self, conn: Any):
        self.conn = conn

    def run(self, query: str, **parameters: Any) -> GraphResult:
        # Kùzu Cypher differs slightly from Neo4j; apply minimal compatibility transforms
        safe_query = _transform_neo4j_to_kuzu(query)
        try:
            if parameters:
                result = self.conn.execute(safe_query, parameters)
            else:
                result = self.conn.execute(safe_query)
            return KuzuResultWrapper(result)
        except Exception as e:
            logger.error(f"Kùzu query failed: {safe_query} | params={parameters} | error={e}")
            raise

    def __enter__(self) -> GraphSession:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

# ---------------------------------------------------------------------------
# Cypher compatibility transforms (Neo4j → Kùzu)
# ---------------------------------------------------------------------------

def _transform_neo4j_to_kuzu(query: str) -> str:
    """Minimal Neo4j → Kùzu Cypher transformations."""
    # Kùzu 0.9+ supports CREATE/MATCH/RETURN but differs in index/constraint syntax.
    # Strip unsupported Neo4j-only clauses for schema ops.
    lowered = query.lower()
    if "create constraint" in lowered or "create index" in lowered:
        # Kùzu handles PK constraints at CREATE TABLE time; skip here
        return "RETURN 1 AS noop"
    if "create fulltext index" in lowered:
        return "RETURN 1 AS noop"
    # DETACH DELETE → DELETE (Kùzu auto-detaches)
    query = re.sub(r"\bDETACH\s+DELETE\b", "DELETE", query, flags=re.IGNORECASE)
    # CREATE ... IF NOT EXISTS → plain CREATE (Kùzu has limited IF NOT EXISTS)
    query = re.sub(r"\bCREATE\s+NODE\s+TABLE\s+IF\s+NOT\s+EXISTS\b", "CREATE NODE TABLE", query, flags=re.IGNORECASE)
    query = re.sub(r"\bCREATE\s+REL\s+TABLE\s+IF\s+NOT\s+EXISTS\b", "CREATE REL TABLE", query, flags=re.IGNORECASE)
    query = re.sub(r"\bCREATE\s+REL\s+TABLE\s+GROUP\s+IF\s+NOT\s+EXISTS\b", "CREATE REL TABLE GROUP", query, flags=re.IGNORECASE)
    # coalesce fallback
    if "coalesce" in lowered:
        # Kùzu may not support coalesce; simple replacement for common patterns
        query = re.sub(r"coalesce\(([^,]+),\s*([^)]+)\)", r"CASE WHEN \1 IS NOT NULL THEN \1 ELSE \2 END", query, flags=re.IGNORECASE)
    return query

# ---------------------------------------------------------------------------
# Schema definitions (ported from legacy)
# ---------------------------------------------------------------------------

NODE_TABLES: List[Tuple[str, str]] = [
    ("Repository", "path STRING, name STRING, is_dependency BOOLEAN, indexed_at STRING, commit_hash STRING, PRIMARY KEY (path)"),
    ("File", "path STRING, name STRING, relative_path STRING, is_dependency BOOLEAN, PRIMARY KEY (path)"),
    ("Directory", "path STRING, name STRING, PRIMARY KEY (path)"),
    ("Module", "name STRING, lang STRING, full_import_name STRING, PRIMARY KEY (name)"),
    ("Function", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, cyclomatic_complexity INT64, context STRING, context_type STRING, class_context STRING, is_dependency BOOLEAN, decorators STRING[], args STRING[], PRIMARY KEY (uid)"),
    ("Class", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, is_dependency BOOLEAN, decorators STRING[], PRIMARY KEY (uid)"),
    ("Variable", "uid STRING, name STRING, path STRING, line_number INT64, source STRING, docstring STRING, lang STRING, value STRING, context STRING, is_dependency BOOLEAN, PRIMARY KEY (uid)"),
    ("Trait", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, is_dependency BOOLEAN, PRIMARY KEY (uid)"),
    ("Interface", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, is_dependency BOOLEAN, PRIMARY KEY (uid)"),
    ("Macro", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, is_dependency BOOLEAN, PRIMARY KEY (uid)"),
    ("Struct", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, is_dependency BOOLEAN, PRIMARY KEY (uid)"),
    ("Enum", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, is_dependency BOOLEAN, PRIMARY KEY (uid)"),
    ("Union", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, is_dependency BOOLEAN, PRIMARY KEY (uid)"),
    ("Annotation", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, is_dependency BOOLEAN, PRIMARY KEY (uid)"),
    ("Record", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, is_dependency BOOLEAN, PRIMARY KEY (uid)"),
    ("Property", "uid STRING, name STRING, path STRING, line_number INT64, end_line INT64, source STRING, docstring STRING, lang STRING, is_dependency BOOLEAN, PRIMARY KEY (uid)"),
    ("Parameter", "uid STRING, name STRING, path STRING, function_line_number INT64, PRIMARY KEY (uid)"),
]

# (name, schema, is_group)
REL_TABLES: List[Tuple[str, str, bool]] = [
    ("CONTAINS", "FROM File TO Function, FROM File TO Class, FROM File TO Variable, FROM File TO Trait, FROM File TO Interface, FROM `Macro` TO `Macro`, FROM File TO `Macro`, FROM File TO Struct, FROM File TO Enum, FROM File TO `Union`, FROM File TO Annotation, FROM File TO Record, FROM File TO `Property`, FROM Repository TO Directory, FROM Directory TO Directory, FROM Directory TO File, FROM Repository TO File, FROM Class TO Function, FROM Function TO Function", True),
    ("CALLS", "FROM Function TO Function, FROM Function TO Class, FROM File TO Function, FROM File TO Class, FROM Class TO Function, FROM Class TO Class, line_number INT64, args STRING[], full_call_name STRING", True),
    ("IMPORTS", "FROM File TO Module, alias STRING, full_import_name STRING, imported_name STRING, line_number INT64", False),
    ("INHERITS", "FROM Class TO Class, FROM Record TO Record, FROM Interface TO Interface", True),
    ("HAS_PARAMETER", "FROM Function TO Parameter", False),
    ("INCLUDES", "FROM Class TO Module", False),
    ("IMPLEMENTS", "FROM Class TO Interface, FROM Struct TO Interface, FROM Record TO Interface", True),
]

# ---------------------------------------------------------------------------
# Backend implementation
# ---------------------------------------------------------------------------

class KuzuBackend(GraphBackend):
    """
    KùzuDB embedded graph backend.
    Thread-safe singleton pattern adapted from legacy codegraph.
    """

    _instance: Optional["KuzuBackend"] = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if hasattr(self, "_initialized"):
            return
        self._initialized = False

        self.name = "kuzudb"
        self.db_path = db_path or os.getenv(
            "CODECORTEX_KUZU_PATH",
            str(Path.home() / ".codecortex" / "global" / "kuzudb"),
        )
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._db: Any = None
        self._conn: Any = None
        self._initialized = True

    # -- GraphBackend API ---------------------------------------------------

    def get_session(self) -> GraphSession:
        if self._conn is None:
            self._connect()
        return KuzuSessionWrapper(self._conn)

    def create_schema(self) -> None:
        if self._conn is None:
            self._connect()
        for table_name, schema in NODE_TABLES:
            try:
                self._conn.execute(f"CREATE NODE TABLE `{table_name}`({schema})")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Kùzu schema node error ({table_name}): {e}")

        for table_name, schema, is_group in REL_TABLES:
            try:
                if is_group:
                    self._conn.execute(f"CREATE REL TABLE GROUP `{table_name}`({schema})")
                else:
                    self._conn.execute(f"CREATE REL TABLE `{table_name}`({schema})")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Kùzu schema rel error ({table_name}): {e}")

        logger.info("Kùzu schema verified/created successfully")

    def is_connected(self) -> bool:
        if self._conn is None:
            return False
        try:
            self._conn.execute("RETURN 1")
            return True
        except Exception:
            return False

    def get_backend_type(self) -> str:
        return "kuzudb"

    def close(self) -> None:
        if self._conn is not None:
            self._conn = None
        if self._db is not None:
            self._db = None
        logger.info("Kùzu backend closed")

    @staticmethod
    def validate_config() -> Tuple[bool, Optional[str]]:
        try:
            import kuzu
            return True, None
        except ImportError:
            return False, "kuzu package not installed. Run: pip install kuzu"

    @staticmethod
    def test_connection() -> Tuple[bool, Optional[str]]:
        try:
            import kuzu
        except ImportError:
            return False, "kuzu package not installed. Run: pip install kuzu"
        return True, None

    # -- Internals ----------------------------------------------------------

    def _connect(self) -> None:
        if self._conn is not None:
            return
        with self._lock:
            if self._conn is not None:
                return
            try:
                import kuzu
            except ImportError as e:
                raise ImportError("kuzu package not installed. Run: pip install kuzu") from e

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    logger.info(f"Initializing KùzuDB at {self.db_path}")
                    self._db = kuzu.Database(self.db_path)
                    self._conn = kuzu.Connection(self._db)
                    self.create_schema()
                    logger.info("KùzuDB connection established and schema verified")
                    return
                except Exception as e:
                    if "lock" in str(e).lower() and attempt < max_retries - 1:
                        wait = 0.5 * (2 ** attempt)
                        logger.warning(f"KùzuDB lock contention, retrying in {wait:.1f}s ({attempt+1}/{max_retries})...")
                        time.sleep(wait)
                    else:
                        logger.error(f"Failed to initialize KùzuDB: {e}")
                        raise
