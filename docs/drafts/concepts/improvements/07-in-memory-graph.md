# In-Memory Multi-Index Knowledge Graph

**Domain:** CodeGraph  
**Effort:** Medium | **Impact:** High | **Priority:** 7

## Current State
CodeCortex's graph lives in SQLite (edges table) + optional graph backend (Kuzu/Neo4j). Analysis queries require SQL JOINs or graph DB queries. This is slow for:
- Iterating all relationships of a given type (e.g., all CALLS edges)
- Deleting a node + its edges (must scan all edges)
- Per-type graph walks (heritage, call chains)
- Building NetworkX graph for community detection (must export from SQL)

## Proposed Improvement
Port GitNexus's `KnowledgeGraph` — an in-memory graph with dual-index invariants:
1. **`nodeMap`**: `dict[id, Node]`
2. **`relationshipMap`**: `dict[id, Relationship]`
3. **`relationshipsByType`**: `dict[type, dict[id, Relationship]]` — O(1) per-type iteration
4. **`edgeIdsByNode`**: `dict[nodeId, set[relId]]` — O(edges) node removal
5. **`nodeIdsByFile`**: `dict[filePath, set[nodeId]]` — O(nodes-per-file) file removal
6. **Shared mutation helpers**: All writes go through `_add_to_bucket` / `_remove_from_bucket` to maintain index invariants

## Architecture
```
class KnowledgeGraph:
    # Indexes
    _nodes: dict[str, GraphNode]
    _rels: dict[str, GraphRelationship]
    _rels_by_type: dict[RelationshipType, dict[str, GraphRelationship]]
    _edge_ids_by_node: dict[str, set[str]]
    _node_ids_by_file: dict[str, set[str]]
    
    # Ops
    add_node(node) → void
    add_relationship(rel) → void
    remove_node(node_id) → bool
    remove_nodes_by_file(file_path) → int
    get_node(id) → Optional[GraphNode]
    iter_relationships_by_type(type) → Iterator[GraphRelationship]
    to_networkx() → nx.Graph
```

## Key Changes in CodeCortex
- **`src/domain/codegraph/core/`**: New `knowledge_graph.py`  
- **`src/domain/codegraph/application/service.py`**: Use in-memory graph for analysis, sync to DB/graph backend for persistence  
- **Replace direct SQL queries in analysis**: Use graph iterators instead  
- **MCP Tool**: Add `graph_stats` for in-memory graph stats

## Dependencies
- Pure Python (no new deps)

## Effort Breakdown
- `knowledge_graph.py`: ~200 lines  
- Edit `codegraph_service.py`: ~100 lines  
- Port existing analysis to use graph API: ~150 lines  
- Tests: ~100 lines  
- **Total: ~6 hours**
