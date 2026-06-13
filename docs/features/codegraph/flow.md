# CodeGraph: Execution Flow

## Pipeline Stages

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. Graph    │────>│  2. Analysis │────>│  3. Insight  │────>│  4. Response │
│   Build      │     │   Phase     │     │   Generation │     │   Formatting │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                      │                     │
       │ From SQLite +     │ Graph algorithms:     │ Build reports,      │ JSON or Markdown
       │ Graph backend     │ community detection,  │ summaries,          │ response via
       │ (Kuzu/Neo4j/      │ BFS tracing,          │ audit findings,     │ api_response()
       │ FalkorDB)         │ centrality            │ entry point scores  │
       └────────────────────┴──────────────────────┴─────────────────────┘
```

## Detailed Sequence

### Phase 1: Graph Build

1. `graph_build` tool reads symbols and edges from SQLite
2. In-memory `KnowledgeGraph` constructed with dual-index (node_id + name index)
3. Relationships imported: CALLS, INHERITS, IMPORTS, USES, DEFINES
4. Graph backend (Kuzu/Neo4j/FalkorDB) optionally syncs for persistent graph queries

### Phase 2: Analysis

| Analysis | Algorithm | Trigger |
|----------|-----------|---------|
| Community Detection | Leiden (Louvain fallback) | `arch_analyze` |
| God Node Detection | Degree centrality > threshold | `arch_audit(god_nodes)` |
| Dead Code Detection | No incoming CALLS/IMPORTS edges | `arch_audit(dead_code)` |
| Complexity | Cyclomatic complexity from AST | `arch_audit(complexity)` |
| Entry Point Scoring | Call ratio + naming patterns | `arch_analyze` |
| Heritage Extraction | BFS up INHERITS edges | `graph_query(hierarchy)` |
| Route Extraction | Framework decorator + path patterns | `arch_analyze` |

### Phase 3: Insight Generation

- Architecture report (Markdown or JSON)
- Community cluster map
- Security hygiene findings
- Refactoring recommendations

## Key Entry Points

| Tool | Method | Description |
|------|--------|-------------|
| `graph_build` | `CODDY.build()` | Build/rebuild the graph with modular detection |
| `graph_search` | `CODDYGraphSearch.search()` | Unified search (symbols, relations, semantic, modular) |
| `graph_query` | `CodeGraphService.analyze_code_relationships()` + `CODDYGraphTrace.trace()` | Type-specific query + trace |
| `graph_audit` | `CODDYGraphAudit.audit()` + `CodeGraphService` methods | Full architectural audit |
| `graph_relationship` | `CODDYGraphRelationship.explore()` | Explore relationships with community detection |
| `graph_refactor` | `CODDYGraphRefactor.refactor()` | Architectural-scale code transformation |

---

## Error Codes

| Prefix | Tool | Description |
|--------|------|-------------|
| GRPH_001 | graph_build | Repository path does not exist or invalid |
| GRPH_002 | graph_query | Node not found in graph |
| GRPH_003 | graph_search | Invalid action parameter |
| GRPH_004 | graph_audit | Repository ID not found |
| GRPH_005 | graph_relationship | Target node not found |
| GRPH_006 | graph_refactor | Invalid refactor_type |
| GRPH_007 | graph_refactor | Target node not found in graph |
| GRPH_008 | graph_refactor | Undo log entry not found |
| GRPH_009 | graph_refactor | Apply operation failed |
| GRPH_010 | graph_build | Cache write/read error |
| GRPH_011 | graph_query | Invalid query_type parameter |
| GRPH_012 | graph_refactor | Validation failed (options, preconditions) |

---

## Performance

- **Graph Build:** Hash-based incremental build (SHA-1 over file mtime+size) enables sub-second cache hits for unchanged repos
- **Cache Invalidation:** Automatic invalidation on any file change via repo hash comparison
- **Graph Traversal:** BFS O(V+E) for call chain tracing, depth-limited to prevent runaway
- **Community Detection:** Leiden algorithm O(n log n) for large graphs
- **Memory Usage:** In-memory KnowledgeGraph with dual-index for O(1) lookups; scales to ~100k nodes comfortably
- **Backend Sync:** Optional Kuzu/Neo4j/FalkorDB sync for persistent graph queries
