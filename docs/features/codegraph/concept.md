# CodeGraph: Code Relationship Graph

> **Domain:** CodeGraph
> **Package:** `src/domain/codegraph/`

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
