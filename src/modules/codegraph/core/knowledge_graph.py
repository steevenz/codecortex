"""
In-memory Knowledge Graph with dual-index invariants.
Ported from GitNexus's graph.ts — multi-index for O(1) lookups.

:project: CodeCortex
:package: Modules.Codegraph.Core.Knowledge_graph
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

from typing import Dict, List, Optional, Set, Tuple, Iterator, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

class RelationshipType(Enum):
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPORTS = "IMPORTS"
    USES = "USES"
    DEFINES = "DEFINES"

@dataclass
class GraphNode:
    id: str
    name: str
    type: str  # 'class', 'function', 'variable', 'file', 'module'
    file_path: Optional[str] = None
    language: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphRelationship:
    id: str
    source_id: str
    target_id: str
    type: RelationshipType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

class KnowledgeGraph:
    """
    In-memory graph with dual-index invariants for O(1) lookups.

    Indexes:
    - _nodes: Map<node_id, GraphNode>
    - _rels: Map<rel_id, GraphRelationship>
    - _rels_by_type: Map<type, Map<rel_id, Relationship>>
    - _edge_ids_by_node: Map<node_id, Set<rel_id>>
    - _node_ids_by_file: Map<file_path, Set<node_id>>
    """

    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._rels: Dict[str, GraphRelationship] = {}
        self._rels_by_type: Dict[RelationshipType, Dict[str, GraphRelationship]] = {}
        self._edge_ids_by_node: Dict[str, Set[str]] = {}
        self._node_ids_by_file: Dict[str, Set[str]] = {}

    # ---- Helpers ----

    def _add_to_bucket(self, mapping: Dict[str, Set[str]], key: str, value: str):
        bucket = mapping.get(key)
        if bucket is None:
            bucket = set()
            mapping[key] = bucket
        bucket.add(value)

    def _remove_from_bucket(self, mapping: Dict[str, Set[str]], key: str, value: str):
        bucket = mapping.get(key)
        if bucket is None:
            return
        bucket.discard(value)
        if not bucket:
            mapping.pop(key, None)

    # ---- Node Operations ----

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def relationship_count(self) -> int:
        return len(self._rels)

    def add_node(self, node: GraphNode) -> None:
        self._nodes[node.id] = node
        if node.file_path:
            self._add_to_bucket(self._node_ids_by_file, node.file_path, node.id)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        node = self._nodes[node_id]
        # Remove all edges touching this node
        edge_ids = list(self._edge_ids_by_node.get(node_id, set()))
        for rel_id in edge_ids:
            self._remove_relationship_internal(rel_id)
        # Remove from file index
        if node.file_path:
            self._remove_from_bucket(self._node_ids_by_file, node.file_path, node_id)
        del self._nodes[node_id]
        return True

    def remove_nodes_by_file(self, file_path: str) -> int:
        node_ids = list(self._node_ids_by_file.get(file_path, set()))
        for nid in node_ids:
            self.remove_node(nid)
        return len(node_ids)

    def iter_nodes(self) -> Iterator[GraphNode]:
        return iter(self._nodes.values())

    def for_each_node(self, fn: Callable[[GraphNode], None]) -> None:
        for n in self._nodes.values():
            fn(n)

    # ---- Relationship Operations ----

    def add_relationship(self, rel: GraphRelationship) -> None:
        self._rels[rel.id] = rel
        # Type index
        type_bucket = self._rels_by_type.get(rel.type)
        if type_bucket is None:
            type_bucket = {}
            self._rels_by_type[rel.type] = type_bucket
        type_bucket[rel.id] = rel
        # Edge-by-node index (bidirectional)
        self._add_to_bucket(self._edge_ids_by_node, rel.source_id, rel.id)
        self._add_to_bucket(self._edge_ids_by_node, rel.target_id, rel.id)

    def _remove_relationship_internal(self, rel_id: str) -> bool:
        rel = self._rels.pop(rel_id, None)
        if rel is None:
            return False
        # Remove from type index
        type_bucket = self._rels_by_type.get(rel.type)
        if type_bucket:
            type_bucket.pop(rel_id, None)
            if not type_bucket:
                self._rels_by_type.pop(rel.type, None)
        # Remove from edge-by-node index
        self._remove_from_bucket(self._edge_ids_by_node, rel.source_id, rel_id)
        self._remove_from_bucket(self._edge_ids_by_node, rel.target_id, rel_id)
        return True

    def remove_relationship(self, rel_id: str) -> bool:
        return self._remove_relationship_internal(rel_id)

    def get_relationships_by_type(self, rel_type: RelationshipType) -> Iterator[GraphRelationship]:
        type_bucket = self._rels_by_type.get(rel_type)
        if type_bucket:
            return iter(type_bucket.values())
        return iter([])

    def get_edges_for_node(self, node_id: str) -> List[GraphRelationship]:
        edge_ids = self._edge_ids_by_node.get(node_id, set())
        return [self._rels[eid] for eid in edge_ids if eid in self._rels]

    def iter_relationships(self) -> Iterator[GraphRelationship]:
        return iter(self._rels.values())

    def for_each_relationship(self, fn: Callable[[GraphRelationship], None]) -> None:
        for r in self._rels.values():
            fn(r)

    def get_callees(self, node_id: str) -> List[str]:
        """Get all nodes called by this node (CALLS edges from source)."""
        targets = []
        edge_ids = self._edge_ids_by_node.get(node_id, set())
        for eid in edge_ids:
            rel = self._rels.get(eid)
            if rel and rel.type == RelationshipType.CALLS and rel.source_id == node_id:
                targets.append(rel.target_id)
        return targets

    def get_callers(self, node_id: str) -> List[str]:
        """Get all nodes that call this node (CALLS edges to target)."""
        sources = []
        edge_ids = self._edge_ids_by_node.get(node_id, set())
        for eid in edge_ids:
            rel = self._rels.get(eid)
            if rel and rel.type == RelationshipType.CALLS and rel.target_id == node_id:
                sources.append(rel.source_id)
        return sources

    # ---- Conversion ----

    def to_networkx(self):
        """Convert to NetworkX graph for community detection."""
        import networkx as nx
        G = nx.DiGraph() if True else nx.Graph()  # Use DiGraph for directed edges
        G = nx.DiGraph()
        for n in self._nodes.values():
            G.add_node(n.id, name=n.name, type=n.type)
        for r in self._rels.values():
            G.add_edge(r.source_id, r.target_id, type=r.type.name, weight=r.weight)
        return G

    def to_dict(self) -> Dict:
        return {
            "nodes": [{"id": n.id, "name": n.name, "type": n.type, "file_path": n.file_path} for n in self._nodes.values()],
            "relationships": [{"id": r.id, "source": r.source_id, "target": r.target_id, "type": r.type.name} for r in self._rels.values()],
            "stats": {"nodes": self.node_count, "edges": self.relationship_count},
        }
