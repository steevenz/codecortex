"""
AEGIS Graph Trace – Call Graph Visualization & Execution Path Tracing
Uses BFS/DFS traversal for explicit graph navigation without fuzzy matching.

:project: CodeCortex
:package: Modules.Codegraph.Services.Trace
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

import networkx as nx

from src.core.database import DatabaseManager
from src.core.graph import GraphManager
from src.core.logging import get_logger
from src.core import ApiError

logger = get_logger("CodeCortex.Domain.CodeGraph.GraphTrace")

class ConfidenceLevel(str, Enum):
    EXTRACTED = "EXTRACTED"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"

@dataclass
class TraceNode:
    id: str
    name: str
    kind: str
    file: Optional[str] = None
    line: Optional[int] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None

@dataclass
class TraceEdge:
    from_node: str
    to_node: str
    relation: str
    confidence: str
    weight: float = 1.0

@dataclass
class TraceItem:
    depth: int
    node: TraceNode
    relation: str
    confidence: str
    caller_context: Optional[str] = None

@dataclass
class PathStep:
    node: Optional[TraceNode] = None
    edge: Optional[Dict[str, Any]] = None

class AEGISGraphTrace:
    """
    Call graph visualization and execution path tracing.
    Uses BFS/DFS traversal for explicit graph navigation.
    """

    def __init__(self, db: DatabaseManager, graph_manager: Optional[GraphManager] = None):
        self.db = db
        self.graph_manager = graph_manager
        self._graph: Optional[nx.DiGraph] = None

    async def trace(
        self,
        repo_id: str,
        query_type: str,
        target_node: str,
        max_depth: int = 3,
        end_node: Optional[str] = None,
        context_filter: Optional[List[str]] = None,
        min_confidence: str = "INFERRED",
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        repo_check = self.db.conn.execute(
            "SELECT id FROM repositories WHERE id = ?", (repo_id,)
        ).fetchone()
        if not repo_check:
            raise ApiError(f"Repository not found: {repo_id}", status_code=404, error_code="GRPH_010")

        self._graph = await self._load_graph(repo_id)
        if self._graph is None or self._graph.number_of_nodes() == 0:
            raise ApiError("Graph not built for repository. Run graph_build first.", status_code=409, error_code="GRPH_002")

        if query_type == "find_callers":
            result = await self._find_callers(target_node, max_depth, context_filter, min_confidence, limit, cursor)
        elif query_type == "find_callees":
            result = await self._find_callees(target_node, max_depth, context_filter, min_confidence, limit, cursor)
        elif query_type == "trace_path":
            if not end_node:
                raise ApiError("end_node is required for trace_path query", status_code=400, error_code="GRPH_010")
            result = await self._trace_path(target_node, end_node, min_confidence)
        else:
            raise ApiError(f"Unknown query_type: {query_type}", status_code=400, error_code="GRPH_010")

        return result

    async def _load_graph(self, repo_id: str) -> Optional[nx.DiGraph]:
        if self.graph_manager:
            backend = self.graph_manager.get_backend()
            session = backend.get_session()
            G = nx.DiGraph()
            try:
                for node in session.run("MATCH (n) RETURN n.node_id as id, n.name as name, n.type as type, n.file as file, n.line_number as line").data():
                    G.add_node(node["id"], name=node["name"], type=node["type"], file=node.get("file"), line=node.get("line"))
                for rel in session.run("MATCH (a)-[r]->(b) RETURN a.node_id as from, b.node_id as to, type(r) as rel, r.confidence as conf").data():
                    G.add_edge(rel["from"], rel["to"], relation=rel["rel"], confidence=rel.get("conf", "INFERRED"))
                return G
            except Exception:
                return None
        return None

    async def _find_callers(
        self, target_node: str, max_depth: int, context_filter: Optional[List[str]],
        min_confidence: str, limit: int, cursor: Optional[str]
    ) -> Dict[str, Any]:
        if self._graph is None:
            return {}

        min_conf_level = self._confidence_to_level(min_confidence)
        target_id = self._resolve_node_id(target_node)
        if not target_id or target_id not in self._graph:
            return self._success_response("find_callers", [], 0, None, False)

        visited: Set[str] = set()
        items: List[Dict[str, Any]] = []
        queue = deque([(target_id, 0)])

        while queue and len(items) < limit:
            node_id, depth = queue.popleft()
            if node_id in visited or depth >= max_depth:
                continue
            visited.add(node_id)

            for pred in self._graph.predecessors(node_id):
                if pred in visited:
                    continue
                edge_data = self._graph.get_edge_data(pred, node_id) or {}
                conf = edge_data.get("confidence", "INFERRED")
                if self._confidence_to_level(conf) < min_conf_level:
                    continue

                attrs = self._graph.nodes[pred]
                item = {
                    "depth": depth + 1,
                    "node": {
                        "id": pred,
                        "name": attrs.get("name", pred),
                        "kind": attrs.get("type", "function"),
                        "file": attrs.get("file"),
                        "line": attrs.get("line"),
                    },
                    "relation": "calls",
                    "confidence": conf,
                }
                items.append(item)

                if len(items) >= limit:
                    break
                queue.append((pred, depth + 1))

        return self._success_response("find_callers", items, len(items), f"{max_depth}_{list(visited)[-1]}" if visited else None, False)

    async def _find_callees(
        self, target_node: str, max_depth: int, context_filter: Optional[List[str]],
        min_confidence: str, limit: int, cursor: Optional[str]
    ) -> Dict[str, Any]:
        if self._graph is None:
            return {}

        min_conf_level = self._confidence_to_level(min_confidence)
        target_id = self._resolve_node_id(target_node)
        if not target_id or target_id not in self._graph:
            return self._success_response("find_callees", [], 0, None, False)

        visited: Set[str] = set()
        items: List[Dict[str, Any]] = []
        queue = deque([(target_id, 0)])

        while queue and len(items) < limit:
            node_id, depth = queue.popleft()
            if node_id in visited or depth >= max_depth:
                continue
            visited.add(node_id)

            for succ in self._graph.successors(node_id):
                if succ in visited:
                    continue
                edge_data = self._graph.get_edge_data(node_id, succ) or {}
                conf = edge_data.get("confidence", "INFERRED")
                if self._confidence_to_level(conf) < min_conf_level:
                    continue

                attrs = self._graph.nodes[succ]
                caller_ctx = self._graph.nodes[node_id].get("name", "") if depth == 0 else None
                item = {
                    "depth": depth + 1,
                    "node": {
                        "id": succ,
                        "name": attrs.get("name", succ),
                        "kind": attrs.get("type", "function"),
                        "file": attrs.get("file"),
                        "line": attrs.get("line"),
                    },
                    "relation": "calls",
                    "confidence": conf,
                    "caller_context": caller_ctx,
                }
                items.append(item)

                if len(items) >= limit:
                    break
                queue.append((succ, depth + 1))

        return self._success_response("find_callees", items, len(items), None, False)

    async def _trace_path(
        self, start_node: str, end_node: str, min_confidence: str
    ) -> Dict[str, Any]:
        if self._graph is None:
            return {}

        min_conf_level = self._confidence_to_level(min_confidence)
        start_id = self._resolve_node_id(start_node)
        end_id = self._resolve_node_id(end_node)

        if not start_id or not end_id:
            raise ApiError("One or both nodes not found in graph", status_code=404, error_code="GRPH_010")

        if start_id not in self._graph or end_id not in self._graph:
            raise ApiError("One or both nodes not found in graph", status_code=404, error_code="GRPH_010")

        try:
            paths = list(nx.all_simple_paths(self._graph, start_id, end_id, cutoff=10))
            if not paths:
                return self._success_response("trace_path", {}, 0, None, False)

            shortest = min(paths, key=len)
            path_items = []
            for i, node_id in enumerate(shortest):
                attrs = self._graph.nodes[node_id]
                step: Dict[str, Any] = {"node": {
                    "id": node_id,
                    "name": attrs.get("name", node_id),
                    "kind": attrs.get("type", "function"),
                    "file": attrs.get("file"),
                    "line": attrs.get("line"),
                }}
                if i > 0:
                    prev_id = shortest[i - 1]
                    edge_data = self._graph.get_edge_data(prev_id, node_id) or {}
                    step["edge"] = {
                        "from": prev_id,
                        "to": node_id,
                        "relation": "calls",
                        "confidence": edge_data.get("confidence", "INFERRED"),
                    }
                path_items.append(step)

            return self._success_response("trace_path", {"path": path_items}, len(path_items), None, False)
        except nx.NetworkXNoPath:
            return self._success_response("trace_path", {}, 0, None, False)

    def _resolve_node_id(self, node_name: str) -> Optional[str]:
        if "::" in node_name:
            return node_name
        if self._graph:
            for nid in self._graph.nodes():
                if self._graph.nodes[nid].get("name") == node_name:
                    return nid
        return None

    def _confidence_to_level(self, conf: str) -> int:
        return {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}.get(conf, 0)

    def _success_response(self, query_type: str, items: List, total: int, cursor: Optional[str], has_more: bool) -> Dict[str, Any]:
        return {
            "query_type": query_type,
            "items": items,
            "total": total,
            "next_cursor": cursor,
            "has_more": has_more,
        }

    def _error_response(self, message: str, request_id: str) -> Dict[str, Any]:
        raise ApiError(message, status_code=400, error_code="GRPH_010")
