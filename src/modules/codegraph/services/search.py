"""
AEGIS Graph Search – Modular-Aware Symbol & Relation Search
Graph-aware search for symbols, relations, trace flow, and modular types.

:project: CodeCortex
:package: Modules.Codegraph.Services.Search
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

import json
import hashlib
import base64
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field, asdict

from src.core.database import DatabaseManager
from src.core.graph import GraphManager
from src.core.logging import get_logger
from src.core import ApiError

logger = get_logger("CodeCortex.Domain.CodeGraph.GraphSearch")

MODULAR_TYPE_MAP = {
    "module": "Module",
    "plugin": "Plugin",
    "widget": "Widget",
    "component": "Component",
    "core": "CoreContract",
    "service": "Service",
    "application": "Application",
}

RELATION_TYPE_MAP = {
    "callers": "CALLS",
    "callees": "CALLS",
    "requires": "REQUIRES",
    "imports": "IMPORTS",
    "overrides": "OVERRIDES",
    "hierarchy": "INHERITS",
    "modifies": "MODIFIES",
    "deps": "DEPENDS_ON",
}

@dataclass
class SearchResultItem:
    node_id: str
    name: str
    kind: str
    modular_context: Optional[Dict[str, Any]] = None
    file: Optional[str] = None
    line: Optional[int] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None
    incoming_edges_count: Optional[int] = None
    outgoing_edges_count: Optional[int] = None
    caller_node: Optional[Dict[str, Any]] = None
    relation: Optional[str] = None
    distance: Optional[int] = None
    node: Optional[str] = None
    callees: Optional[List[Dict[str, Any]]] = None

@dataclass
class PaginationInfo:
    next_cursor: Optional[str] = None
    has_more: bool = False
    total: int = 0

class AEGISGraphSearch:
    """
    Graph-aware search engine following AEGIS standard.
    Supports symbol, relation, trace_flow, and modular search actions.
    """

    def __init__(self, db: DatabaseManager, graph_manager: Optional[GraphManager] = None):
        self.db = db
        self.graph_manager = graph_manager
        self._session = None

    async def search(
        self,
        repo_id: str,
        action: str,
        query: Optional[str] = None,
        relation_type: Optional[str] = None,
        target_symbol_id: Optional[str] = None,
        max_depth: int = 3,
        modular_type: Optional[str] = None,
        fuzzy: bool = False,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for graph search.
        """
        repo_check = self.db.conn.execute(
            "SELECT id FROM repositories WHERE id = ?", (repo_id,)
        ).fetchone()
        if not repo_check:
            raise ApiError(f"Repository not found: {repo_id}", status_code=404, error_code="GRPH_008")

        if not self._is_graph_built(repo_id):
            raise ApiError(f"Graph not built for repository '{repo_id}'. Run graph_build first.", status_code=409, error_code="GRPH_002")

        if action == "symbol":
            result = await self._search_symbol(repo_id, query, modular_type, fuzzy, limit, cursor)
        elif action == "relation":
            result = await self._search_relation(repo_id, query, relation_type, max_depth, limit, cursor)
        elif action == "trace_flow":
            result = await self._trace_flow(repo_id, target_symbol_id, max_depth)
        elif action == "modular":
            result = await self._search_modular(repo_id, modular_type, limit, cursor)
        else:
            raise ApiError(f"Unknown action: {action}", status_code=400, error_code="GRPH_008")

        return result

    def _is_graph_built(self, repo_id: str) -> bool:
        cursor = self.db.conn.execute(
            "SELECT 1 FROM graph_cache WHERE repository_id = ? LIMIT 1", (repo_id,)
        )
        return cursor.fetchone() is not None

    async def _search_symbol(
        self, repo_id: str, query: str, modular_type: Optional[str],
        fuzzy: bool, limit: int, cursor: Optional[str]
    ) -> Dict[str, Any]:
        if not query:
            return self._success_response("symbol", [], 0, None, False)

        session = self._get_session()
        label = self._resolve_symbol_label(query)
        params = {"name": query, "limit": limit * 2}

        where_parts = [f"node:{label}"]
        if modular_type and modular_type in MODULAR_TYPE_MAP:
            label = MODULAR_TYPE_MAP[modular_type]
            where_parts = [f"node:{label}"]

        query_lower = query.lower()

        cypher = f"""
            MATCH (node:{label})
            WHERE toLower(node.name) CONTAINS $query_lower
            RETURN node.name as name, node.path as path, node.line_number as line_number,
                node.signature as signature, node.docstring as docstring
            LIMIT $limit
        """

        rows = session.run(cypher, query_lower=query_lower, limit=limit * 2).data()

        items = []
        seen_names = set()
        for row in rows:
            if row.get("name") in seen_names:
                continue
            seen_names.add(row["name"])
            items.append({
                "node_id": f"sym_{hashlib.md5(row['name'].encode()).hexdigest()[:8]}",
                "name": row.get("name"),
                "kind": "function" if label == "Function" else "class" if label == "Class" else "symbol",
                "file": row.get("path"),
                "line": row.get("line_number"),
                "signature": row.get("signature"),
                "docstring": row.get("docstring"),
            })
            if len(items) >= limit:
                break

        return self._success_response("symbol", items, len(items), None, False)

    def _resolve_symbol_label(self, query: str) -> str:
        return "Function"

    async def _search_relation(
        self, repo_id: str, query: str, relation_type: str,
        max_depth: int, limit: int, cursor: Optional[str]
    ) -> Dict[str, Any]:
        if not query:
            return self._success_response("relation", [], 0, None, False)

        internal_relation = RELATION_TYPE_MAP.get(relation_type, "CALLS")
        session = self._get_session()

        cypher = f"""
            MATCH (target {{name: $query}})
            MATCH (caller)-[r:{internal_relation}]->(target)
            RETURN caller.name as caller_name, caller.path as caller_path, caller.line_number as caller_line,
                type(r) as relation, 1 as distance
            LIMIT $limit
        """

        rows = session.run(cypher, query=query, limit=limit).data()

        items = []
        for row in rows:
            items.append({
                "caller_node": {
                    "node_id": f"sym_{hashlib.md5(row['caller_name'].encode()).hexdigest()[:8]}",
                    "name": row.get("caller_name"),
                    "kind": "function",
                    "file": row.get("caller_path"),
                    "line": row.get("caller_line"),
                },
                "relation": row.get("relation"),
                "distance": row.get("distance"),
            })

        return self._success_response("relation", items, len(items), None, False)

    async def _trace_flow(
        self, repo_id: str, target_symbol_id: str, max_depth: int
    ) -> Dict[str, Any]:
        if not target_symbol_id:
            return self._success_response("trace_flow", {}, 0, None, False)

        session = self._get_session()

        cypher = """
            MATCH (start {node_id: $target_symbol_id})
            OPTIONAL MATCH (start)-[:CALLS*1..$max_depth]->(callee)
            RETURN start.node_id as node_id, start.name as name, start.path as path, start.line_number as line
        """

        row = session.run(cypher, target_symbol_id=target_symbol_id, max_depth=max_depth).single()

        flow_tree = {"node": "", "callees": []}
        if row:
            flow_tree["node"] = row.get("name", "")
            flow_tree["line"] = row.get("line")

        return {
            "success": True,
            "status_code": 200,
            "message": f"Execution flow traced from '{target_symbol_id}' (depth={max_depth})",
            "data": {
                "action": "trace_flow",
                "start_symbol": {
                    "node_id": target_symbol_id,
                    "name": row.get("name") if row else "",
                    "file": row.get("path") if row else "",
                    "line": row.get("line") if row else None,
                },
                "flow_tree": flow_tree,
            },
            "meta": {"request_id": f"trace_{datetime.now().strftime('%Y%m%d%H%M%S')}"},
        }

    async def _search_modular(
        self, repo_id: str, modular_type: Optional[str], limit: int, cursor: Optional[str]
    ) -> Dict[str, Any]:
        session = self._get_session()

        if modular_type and modular_type in MODULAR_TYPE_MAP:
            label = MODULAR_TYPE_MAP[modular_type]
            cypher = f"MATCH (node:{label}) RETURN node.name as name, node.path as path, node.version as version LIMIT $limit"
            rows = session.run(cypher, limit=limit).data()
            items = [{
                "node_id": f"mod_{row['name'].lower()}_{hashlib.md5(row['name'].encode()).hexdigest()[:6]}",
                "name": row.get("name"),
                "type": modular_type,
                "path": row.get("path"),
                "version": row.get("version"),
            } for row in rows]
        else:
            items = []
            for mtype, label in MODULAR_TYPE_MAP.items():
                cypher = f"MATCH (node:{label}) RETURN node.name as name, node.path as path, node.version as version LIMIT $limit"
                rows = session.run(cypher, limit=limit).data()
                for row in rows:
                    items.append({
                        "node_id": f"mod_{mtype}_{row['name'].lower()}_{hashlib.md5(row['name'].encode()).hexdigest()[:6]}",
                        "name": row.get("name"),
                        "type": mtype,
                        "path": row.get("path"),
                        "version": row.get("version"),
                    })
                    if len(items) >= limit:
                        break

        return self._success_response("modular", items, len(items), None, False)

    def _get_session(self):
        if self.graph_manager:
            return self.graph_manager.get_backend().get_session()
        return None

    def _success_response(self, action: str, items: List[Dict], total: int,
                          next_cursor: Optional[str], has_more: bool) -> Dict[str, Any]:
        return {
            "action": action,
            "total": total,
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    def _error_response(self, message: str, request_id: str) -> Dict[str, Any]:
        raise ApiError(message, status_code=400, error_code="GRPH_008")

    def _error_graph_not_built(self, repo_id: str, request_id: str) -> Dict[str, Any]:
        raise ApiError(f"Graph not built for repository '{repo_id}'. Run graph_build first.", status_code=409, error_code="GRPH_002")
