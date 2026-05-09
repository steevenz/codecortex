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
| `graph_build` | `CodeGraphService.build_repository_graph()` | Build/rebuild the graph |
| `graph_query` | `CodeGraphService.analyze_code_relationships()` | Type-specific query |
| `graph_find_symbols` | Symbol search (fuzzy or exact) | Locate code by name |
| `graph_trace_flow` | BFS execution flow tracing | Happy path analysis |
| `arch_analyze` | Full architecture + report | Comprehensive analysis |
| `arch_audit` | Specific audit type | Targeted smell detection |
