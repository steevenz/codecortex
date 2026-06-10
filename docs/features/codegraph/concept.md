# CodeGraph: Code Relationship Graph

> **Domain:** CodeGraph
> **Package:** `src/modules/codegraph/`
> **Version:** 2.0.0
> **AI Coder Impact:** 9/10 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

CodeGraph is the **analysis and reasoning layer**. After CodeIndex extracts symbols, CodeGraph connects them into a rich relationship graph and runs analytical algorithms to surface architectural insights: coupling, community structure, execution flow, technical debt, and security risks.

## Why This Exists

- **Relationships > Symbols:** A list of functions tells you what exists. A graph tells you how they connect — who calls whom, what inherits what, which modules depend on which.
- **Architectural Smell Detection:** God nodes (overly coupled classes), dead code (no callers), cyclical dependencies — these require graph analysis, not flat queries.
- **Execution Flow:** Tracing a request from HTTP handler to database query requires traversing call chains across multiple files.
- **Community Detection:** Grouping related modules into communities reveals the de facto architecture vs. the intended architecture.

## Theoretical Foundation

- **Graph Theory:** Nodes are code symbols (functions, classes, files), edges are relationships (calls, inherits, imports, defines). Weighted, directed, multi-relational graph.
- **Leiden Algorithm:** Community detection that maximizes modularity. Louvain fallback for compatibility. Finds natural module groupings.
- **BFS/DFS:** Breadth-first search for call chain tracing, depth-first for dependency resolution.
- **Centrality Metrics:** Degree centrality (coupling), betweenness centrality (bottlenecks), PageRank (importance).
- **Incremental Build:** Hash-based cache invalidation (SHA-1 over file mtime+size) for fast rebuilds.
- **Undo Logging:** SQLite-based undo log for refactor operations with unique IDs.

## Architecture

```
src/modules/codegraph/
├── api/              → tools.py: 6 MCP tools, cli.py: CLI commands (codegraph/cg)
├── services/         → Service classes: DI via constructor
│   ├── aegis.py      → Graph build (AEGIS) with incremental build + cache invalidation
│   ├── search.py     → Unified search (AEGISGraphSearch)
│   ├── trace.py      → Execution flow tracing (AEGISGraphTrace)
│   ├── relationship.py → Relationship exploration (AEGISGraphRelationship)
│   ├── audit.py      → Architectural audit (AEGISGraphAudit)
│   ├── refactor.py   → Refactoring (AEGISGraphRefactor) with undo log support
│   └── graph.py      → Graph operations (CodeGraphService)
├── core/            → dtos.py: typed DTOs for all public interfaces
└── mixins/           → Reusable graph operations (search, trace)
```

## Domain Boundary

- **Owns:** `graph_build`, `graph_search`, `graph_query`, `graph_audit`, `graph_relationship`, `graph_refactor`
- **Does NOT own:** `code_index` (symbol extraction), `code_refactor` (file-level refactoring)
- **Depends on:** `DatabaseManager`, `GraphManager` (Kuzu/Neo4j/FalkorDB), `FilesystemService`
- **Consumed by:** MCP layer via `api/tools.py`, CLI via `cli.py`

## CLI Architecture Note

The CLI domain is named `codegraph` (alias `cg`) to align with the MCP tool naming. Users access all codegraph operations via `codecortex cg <command>`.

## ~/.aicoders/ Compliance

- **API Standard:** `api_response()` for all tool responses
- **DDD:** `api/` + `services/` + `core/` separation
- **DI:** Constructor injection for all services
- **Boundary:** Data crosses layers only via DTOs
- **Error Handling:** Guard clauses, structured errors
- **Logging:** `CodeCortex.CodeGraph.*` logger namespace
- **Documentation:** All docs in `docs/features/codegraph/`

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

## Related Sub-Features

- [Knowledge Graph](sub-features/knowledge-graph/concept.md)
- [Community Detection](sub-features/community-detection/concept.md)
- [Execution Flow](sub-features/execution-flow/concept.md)
- [Heritage Extraction](sub-features/heritage-extraction/concept.md)
- [Route Extraction](sub-features/route-extraction/concept.md)
- [ORM Dataflow](sub-features/orm-dataflow/concept.md)
- [Entry Point Scoring](sub-features/entry-point-scoring/concept.md)
- [Architecture Audit](sub-features/architecture-audit/concept.md)
- [Graph Backends](sub-features/graph-backends/concept.md)
