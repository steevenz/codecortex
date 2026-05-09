# Leiden Community Detection

**Domain:** CodeGraph  
**Effort:** Low | **Impact:** High | **Priority:** 2

## Current State
CodeCortex uses Louvain algorithm (via `python-louvain`) for community detection in `CodeGraphService`. Louvain has known issues:
- May produce disconnected communities
- Lower modularity scores than Leiden
- Not deterministic across runs
- Resolution limit — misses small communities

## Proposed Improvement
Replace Louvain with the **Leiden algorithm** (via `networkx.algorithms.community.leiden` if available, or vendored implementation). Leiden:
- Guarantees connected communities
- Higher modularity on average
- More stable/deterministic
- Better at detecting small communities

## Architecture
```
detect_communities(graph)
  ├── build_nx_graph() → NetworkX Graph from edges
  ├── leiden_partition = leiden_algorithm(nx_graph, resolution=1.0)
  └── map_to_community_nodes() → [CommunityNode, memberships]
```

## Key Changes in CodeCortex
- **`src/domain/codegraph/`**: New `community_leiden.py`  
- **`src/core/graph_manager.py`**: Wire Leiden as default, keep Louvain as fallback  
- **Dependency**: Add `leidenalg` or implement via `networkx` + modularity optimization  
- **DB**: Store modularity score per run in `insights` table

## Dependencies
- `networkx` (already in pyproject.toml)  
- `leidenalg` (C extension, may need conda) — OR implement pure Python Leiden  
- `python-louvain` (keep as fallback)

## Fallback Strategy
If `leidenalg` fails to install, fall back to Louvain automatically. The `GraphManager` circuit breaker already handles backend failures.

## Effort Breakdown
- `community_leiden.py`: ~100 lines  
- Edit `graph_manager.py`: ~20 lines  
- Tests: ~60 lines  
- **Total: ~3 hours**
