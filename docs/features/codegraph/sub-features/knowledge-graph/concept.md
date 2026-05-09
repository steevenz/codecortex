# Knowledge Graph

> **Source:** `src/domain/codegraph/core/knowledge_graph.py`

## Concept

The in-memory `KnowledgeGraph` is the central data structure for CodeGraph analysis. It provides O(1) lookups via dual-index invariants (by node ID and by name), enabling real-time graph traversal without hitting a database.

## Architecture

```
KnowledgeGraph
├── _nodes: Dict[str, GraphNode]        — O(1) node lookup by ID
├── _name_index: Dict[str, str]         — O(1) node lookup by name
├── _rels: Dict[str, GraphRelationship] — O(1) edge lookup by ID
├── _source_index: Dict[str, Set[str]]  — Outgoing edges by source
└── _target_index: Dict[str, Set[str]]  — Incoming edges by target
```

## Key Operations

| Operation | Complexity | Description |
|-----------|-----------|-------------|
| `add_node()` | O(1) | Insert node with dual-index update |
| `add_relationship()` | O(1) | Insert edge with source/target indexes |
| `get_node()` | O(1) | Lookup by ID |
| `find_node_by_name()` | O(1) | Lookup by name (via name_index) |
| `get_callers()` | O(1) | Incoming CALLS edges via target_index |
| `get_callees()` | O(1) | Outgoing CALLS edges via source_index |
| `bfs_traverse()` | O(V+E) | Breadth-first traversal from start node |
| `remove_node()` | O(V+E) | Cascading removal with index cleanup |

## Node Types

| GraphNode.type | Represents | Properties |
|--------------|-----------|------------|
| `class` | Class declaration | bases, decorators, generics |
| `function` | Function/method definition | signature, async, decorators |
| `variable` | Variable/constant | kind (let/const/var), mutable |
| `file` | Source file | language, path |
| `module` | Package/module | exports, is_init |

## Relationship Types

| RelationshipType | Direction | Semantics |
|-----------------|-----------|-----------|
| CALLS | source → target | Function A calls function B |
| INHERITS | source → target | Class A extends class B |
| IMPORTS | source → target | File A imports module/symbol B |
| USES | source → target | Symbol A references type B |
| DEFINES | source → target | File A defines class/function B |
