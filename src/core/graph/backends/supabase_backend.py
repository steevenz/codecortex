"""
SupabaseBackend — PostgreSQL + pgvector graph backend.
Replaces Neo4j/Kuzu with Supabase cloud database.
Uses SQL instead of Cypher for graph queries.
Supports: vector search, RLS, realtime sync, JSON metadata.

:project: CodeCortex
:package: Core.Graph.Backends.Supabase_backend
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import os
import json
import time
import threading
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from .base import GraphBackend, GraphSession, GraphResult
from src.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Supabase Result / Session wrappers (Neo4j-compatible facade)
# ---------------------------------------------------------------------------

class SupabaseRecord(dict):
    """Dict wrapper providing .data() for Neo4j compat."""

    def data(self) -> Dict[str, Any]:
        return dict(self)

class SupabaseResultWrapper:
    """Wraps Supabase query response to satisfy GraphResult protocol."""

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None):
        self._records = data or []

    def single(self) -> Optional[Dict[str, Any]]:
        return SupabaseRecord(self._records[0]) if self._records else None

    def data(self) -> List[Dict[str, Any]]:
        return [SupabaseRecord(r) for r in self._records]

    def consume(self) -> "SupabaseResultWrapper":
        return self

    def __iter__(self):
        return iter(self._records)

class SupabaseSession:
    """Supabase transaction-like session for graph operations."""

    def __init__(self, client: Any):
        self._client = client
        self._queries: List[str] = []

    def run(self, query: str, **parameters: Any) -> SupabaseResultWrapper:
        """
        Execute a graph operation against Supabase tables.
        Query is a JSON dict with: table, method, params.
        """
        try:
            instruction = json.loads(query) if isinstance(query, str) else query
        except json.JSONDecodeError:
            # Raw SQL passthrough (for simple queries)
            instruction = {"method": "sql", "query": query, "params": parameters}

        method = instruction.get("method", "select")
        table = instruction.get("table", "")
        params = instruction.get("params", {})
        filters = instruction.get("filters", {})
        data = instruction.get("data", {})

        try:
            if method == "sql":
                # Raw SQL via stored procedures / rpc
                if hasattr(self._client, "rpc"):
                    result = self._client.rpc("execute_sql", {"query_text": query}).execute()
                    return SupabaseResultWrapper(result.data if hasattr(result, 'data') else [])

            elif method == "upsert_node":
                result = self._client.table("symbols").upsert(data).execute()
                return SupabaseResultWrapper(result.data if hasattr(result, 'data') else [])

            elif method == "upsert_edge":
                result = self._client.table("edges").upsert(
                    data,
                    on_conflict=["source_id", "target_id", "relation_type", "developer_id"]
                ).execute()
                return SupabaseResultWrapper(result.data if hasattr(result, 'data') else [])

            elif method == "get_dependents":
                result = self._client.rpc("get_symbol_dependents", {
                    "symbol_id": str(params.get("symbol_id", ""))
                }).execute()
                return SupabaseResultWrapper(result.data if hasattr(result, 'data') else [])

            elif method == "search_semantic":
                result = self._client.rpc("search_code_by_text", {
                    "query_text": params.get("query", ""),
                    "match_limit": params.get("limit", 10),
                }).execute()
                return SupabaseResultWrapper(result.data if hasattr(result, 'data') else [])

            elif method == "select":
                query = self._client.table(table).select("*")
                for col, val in filters.items():
                    query = query.eq(col, val)
                if params.get("limit"):
                    query = query.limit(params["limit"])
                if params.get("order"):
                    query = query.order(params["order"])
                result = query.execute()
                return SupabaseResultWrapper(result.data if hasattr(result, 'data') else [])

            elif method == "insert":
                result = self._client.table(table).insert(data).execute()
                return SupabaseResultWrapper(result.data if hasattr(result, 'data') else [])

            elif method == "delete":
                query = self._client.table(table).delete()
                for col, val in filters.items():
                    query = query.eq(col, val)
                result = query.execute()
                return SupabaseResultWrapper(result.data if hasattr(result, 'data') else [])

            else:
                logger.warning(f"Unknown Supabase method: {method}")
                return SupabaseResultWrapper([])

        except Exception as e:
            logger.error(f"Supabase query failed: {e}")
            return SupabaseResultWrapper([])

    def __enter__(self) -> "SupabaseSession":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

# ---------------------------------------------------------------------------
# Supabase Backend Implementation
# ---------------------------------------------------------------------------

class SupabaseBackend(GraphBackend):
    """
    Supabase backend for CodeCortex.

    Uses PostgreSQL + pgvector for graph persistence.
    Environment variables:
        SUPABASE_URL        — Project URL from Supabase dashboard
        SUPABASE_SERVICE_KEY— Service role key (for backend operations)
        SUPABASE_ANON_KEY   — Anon key (for client-side operations)
        CODECORTEX_IDENTITY — Developer identity tag
    """

    def __init__(self):
        self._client: Any = None
        self._lock = threading.Lock()
        self._connected = False

    def _get_client(self):
        """Lazy-init Supabase client."""
        if self._client is None:
            try:
                from supabase import create_client
                url = os.getenv("SUPABASE_URL", "").strip()
                key = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", "")).strip()
                if not url or not key:
                    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
                self._client = create_client(url, key)
                self._connected = True
                logger.info("SupabaseBackend connected")
            except ImportError:
                raise RuntimeError("supabase-py not installed. Run: pip install supabase")
            except Exception as e:
                logger.error(f"SupabaseBackend init failed: {e}")
                raise
        return self._client

    def get_session(self) -> SupabaseSession:
        return SupabaseSession(self._get_client())

    def create_schema(self) -> None:
        """Schema is managed via Supabase migrations (supabase/migrations/)."""
        logger.info("Supabase schema managed via migrations — use supabase CLI or dashboard")
        # Verify connection by checking if symbols table exists
        try:
            client = self._get_client()
            result = client.table("symbols").select("id").limit(1).execute()
            if hasattr(result, 'data'):
                logger.info("Supabase schema verified: symbols table accessible")
        except Exception as e:
            logger.warning(f"Supabase schema verification failed: {e}")

    def is_connected(self) -> bool:
        if not self._connected:
            return False
        try:
            client = self._get_client()
            result = client.table("repositories").select("id").limit(1).execute()
            return hasattr(result, 'data')
        except Exception:
            return False

    def get_backend_type(self) -> str:
        return "supabase"

    def close(self) -> None:
        self._client = None
        self._connected = False
        logger.info("SupabaseBackend closed")

    @staticmethod
    def validate_config() -> Tuple[bool, Optional[str]]:
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", "")).strip()
        if not url:
            return False, "SUPABASE_URL is not set"
        if not key:
            return False, "SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY is not set"
        return True, None

    @staticmethod
    def test_connection() -> Tuple[bool, Optional[str]]:
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL", "").strip()
            key = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", "")).strip()
            if not url or not key:
                return False, "Missing Supabase credentials"
            client = create_client(url, key)
            result = client.table("repositories").select("id").limit(1).execute()
            if hasattr(result, 'data'):
                return True, None
            return False, "Connection failed: no data returned"
        except ImportError:
            return False, "supabase-py not installed"
        except Exception as e:
            return False, str(e)
