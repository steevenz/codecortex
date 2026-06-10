"""
AEGIS Graph Relationship – Architecture Exploration with Community Detection
High-level exploration of relationships between modules, classes, and components.

:project: CodeCortex
:package: Modules.Codegraph.Services.Relationship
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

import networkx as nx

from src.core.database import DatabaseManager
from src.core.graph import GraphManager
from src.core.logging import get_logger
from src.core import ApiError

logger = get_logger("CodeCortex.Domain.CodeGraph.GraphRelationship")

class ModularType(str, Enum):
    MODULE = "module"
    PLUGIN = "plugin"
    WIDGET = "widget"
    COMPONENT = "component"
    SERVICE = "service"
    CLASS = "class"
    FUNCTION = "function"

class Direction(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BOTH = "both"

@dataclass
class NodeInfo:
    id: str
    name: str
    type: str
    file: Optional[str] = None
    community_id: Optional[str] = None

@dataclass
class RelationshipInfo:
    type: str
    direction: str
    confidence: str
    cross_community: bool

class AEGISGraphRelationship:
    """
    Architecture exploration with community detection.
    Explores relationships between modules, classes, and components.
    """

    def __init__(self, db: DatabaseManager, graph_manager: Optional[GraphManager] = None):
        self.db = db
        self.graph_manager = graph_manager
        self._graph: Optional[nx.DiGraph] = None
        self._communities: Dict[str, int] = {}

    async def explore(
        self,
        repo_id: str,
        target_node: str,
        relation_type: Optional[List[str]] = None,
        direction: str = "both",
        depth: int = 1,
        modular_type: Optional[str] = None,
        include_community: bool = False,
        min_confidence: str = "INFERRED",
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        repo_check = self.db.conn.execute(
            "SELECT id FROM repositories WHERE id = ?", (repo_id,)
        ).fetchone()
        if not repo_check:
            raise ApiError(f"Repository not found: {repo_id}", status_code=404, error_code="GRPH_011")

        self._graph = await self._load_graph(repo_id)
        if self._graph is None or self._graph.number_of_nodes() == 0:
            raise ApiError("Graph not built for repository. Run graph_build first.", status_code=409, error_code="GRPH_002")

        if include_community:
            self._communities = self._detect_communities()

        if relation_type is None:
            relation_type = ["calls", "imports", "contains", "inherits"]

        result = await self._explore_relationships(
            target_node, relation_type, direction, depth, modular_type,
            include_community, min_confidence, limit
        )
        return result

    async def _load_graph(self, repo_id: str) -> Optional[nx.DiGraph]:
        if self.graph_manager:
            backend = self.graph_manager.get_backend()
            session = backend.get_session()
            G = nx.DiGraph()
            try:
                for node in session.run("MATCH (n) RETURN n.node_id as id, n.name as name, n.type as type, n.file as file").data():
                    G.add_node(node["id"], name=node["name"], type=node["type"], file=node.get("file"))
                for rel in session.run("MATCH (a)-[r]->(b) RETURN a.node_id as from, b.node_id as to, type(r) as rel").data():
                    G.add_edge(rel["from"], rel["to"], relation=rel["rel"])
                return G
            except Exception:
                return None
        return None

    def _detect_communities(self) -> Dict[str, int]:
        if self._graph is None or self._graph.number_of_nodes() == 0:
            return {}

        G = self._graph
        if G.is_directed():
            G = G.to_undirected()

        communities: Dict[str, int] = {}
        try:
            from graspologic.partition import leiden
            partition = leiden(G)
            for node, cid in partition.items():
                communities[node] = cid
        except ImportError:
            pass

        if not communities:
            try:
                communities_list = nx.community.louvain_communities(G, seed=42)
                for cid, nodes in enumerate(communities_list):
                    for node in nodes:
                        communities[node] = cid
            except Exception:
                pass

        return communities

    async def _explore_relationships(
        self, target_node: str, relation_types: List[str], direction: str,
        depth: int, modular_type: Optional[str], include_community: bool,
        min_confidence: str, limit: int
    ) -> Dict[str, Any]:
        if self._graph is None:
            return {}

        target_id = self._resolve_node_id(target_node)
        if not target_id or target_id not in self._graph:
            return self._success_response([], {}, 0, None)

        items: List[Dict[str, Any]] = []
        visited: Set[str] = set()
        queue = deque([(target_id, 0)])

        target_attrs = self._graph.nodes[target_id]
        target_type = target_attrs.get("type", "unknown")

        while queue and len(items) < limit:
            node_id, current_depth = queue.popleft()
            if node_id in visited or current_depth >= depth:
                continue
            visited.add(node_id)

            attrs = self._graph.nodes[node_id]
            node_type = attrs.get("type", "unknown")

            if modular_type and not self._matches_modular_type(node_type, modular_type):
                continue

            edges_to_process = []
            if direction in ("outbound", "both"):
                edges_to_process = [(n, "outbound") for n in self._graph.successors(node_id)]
            if direction in ("inbound", "both"):
                edges_to_process.extend([(n, "inbound") for n in self._graph.predecessors(node_id)])

            for neighbor, dir_type in edges_to_process:
                if neighbor in visited:
                    continue

                edge_data = self._graph.get_edge_data(node_id, neighbor) or {}
                rel_type = edge_data.get("relation", "UNKNOWN")

                if rel_type.lower() not in [r.lower() for r in relation_types]:
                    continue

                conf = edge_data.get("confidence", "INFERRED")
                if self._confidence_level(conf) < self._confidence_level(min_confidence):
                    continue

                neighbor_attrs = self._graph.nodes.get(neighbor, {})
                cross_community = False
                if include_community and neighbor in self._communities:
                    src_comm = self._communities.get(node_id)
                    tgt_comm = self._communities.get(neighbor)
                    cross_community = src_comm != tgt_comm and src_comm is not None and tgt_comm is not None

                item = {
                    "node": {
                        "id": neighbor,
                        "name": neighbor_attrs.get("name", neighbor),
                        "type": neighbor_attrs.get("type", "unknown"),
                        "file": neighbor_attrs.get("file"),
                        "community_id": self._communities.get(neighbor) if include_community else None,
                    },
                    "relation": {
                        "type": rel_type,
                        "direction": dir_type,
                        "confidence": conf,
                        "cross_community": cross_community,
                    },
                }
                items.append(item)

                if current_depth < depth:
                    queue.append((neighbor, current_depth + 1))

        metrics = self._calculate_metrics(items, target_id) if items else {}

        return self._success_response(items, metrics, len(items), None)

    def _resolve_node_id(self, node_name: str) -> Optional[str]:
        if "::" in node_name:
            return node_name
        if self._graph:
            for nid in self._graph.nodes():
                if self._graph.nodes[nid].get("name") == node_name:
                    return nid
        return None

    def _matches_modular_type(self, node_type: str, modular_type: str) -> bool:
        type_map = {
            ModularType.MODULE.value: ["module", "package"],
            ModularType.PLUGIN.value: ["plugin", "extension"],
            ModularType.WIDGET.value: ["widget", "component"],
            ModularType.COMPONENT.value: ["component", "widget"],
            ModularType.SERVICE.value: ["service", "handler"],
            ModularType.CLASS.value: ["class"],
            ModularType.FUNCTION.value: ["function"],
        }
        return node_type in type_map.get(modular_type, [])

    def _confidence_level(self, conf: str) -> int:
        return {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}.get(conf, 0)

    def _calculate_metrics(self, items: List[Dict], target_id: str) -> Dict[str, Any]:
        total_inbound = sum(1 for i in items if i.get("relation", {}).get("direction") == "inbound")
        total_outbound = sum(1 for i in items if i.get("relation", {}).get("direction") == "outbound")
        cross_community = sum(1 for i in items if i.get("relation", {}).get("cross_community", False))

        return {
            "total_inbound": total_inbound,
            "cross_community_inbound": cross_community,
            "intra_community_inbound": total_inbound - cross_community,
        }

    def _success_response(self, items: List, metrics: Dict, total: int, cursor: Optional[str]) -> Dict[str, Any]:
        return {
            "target_node": None,
            "items": items,
            "metrics": metrics,
            "total": total,
            "next_cursor": cursor,
            "has_more": False,
        }

    def _error_response(self, message: str, request_id: str) -> Dict[str, Any]:
        raise ApiError(message, status_code=400, error_code="GRPH_011")
