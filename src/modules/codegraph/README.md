# CodeCortex CodeGraph Domain

## Overview
The **CodeGraph Domain** is the knowledge graph engine for CodeCortex. It builds, queries, and analyzes code relationships across 22 languages, supporting execution flow tracing, heritage extraction, route extraction, ORM dataflow analysis, community detection, and architecture auditing.

## Architecture
DDD + Hexagonal Architecture:
- **api/**: MCP tool registrations (6 tools)
- **services/**: Graph construction, query, analysis, and reporting
- **graph_builders/**: Background workers and persistence
- **core/**: Knowledge graph model and security layer

## Key Components
- **CodeGraphService**: Primary orchestration service
- **AegisBuilder**: Graph construction from AST symbols
- **GraphTracer**: BFS-based execution flow tracing
- **HeritageExtractor**: Class inheritance hierarchy extraction
- **RouteExtractor**: Endpoint discovery (FastAPI, Django, Express, Next.js, etc.)
- **ORMExtractor**: Data flow tracing (SQLAlchemy, Django ORM, Prisma)
- **CommunityDetector**: Leiden/Louvain community detection
- **GraphAuditor**: Architecture audit (god nodes, dead code, security)
- **EntryPointScorer**: Main/CLI entry point detection and ranking
- **ServiceBoundary**: Module boundary analysis

## Tools
| Tool | Description |
|------|-------------|
| `graph_build` | Build knowledge graph from indexed symbols |
| `graph_query` | Query graph with custom Cypher-like syntax |
| `graph_find_symbols` | O(1) symbol lookup across the graph |
| `graph_find_related` | Find dependencies and dependents |
| `graph_trace_flow` | Trace execution flow (call chains) |
| `graph_find_patterns` | Find architectural patterns and anti-patterns |

## Graph Backends
- **Kuzu** (default, embedded)
- **Neo4j** (Docker)
- **FalkorDB** (Docker)
- **Supabase** (cloud)

Set `CODECORTEX_GRAPH_BACKEND` to select backend.

## Dependencies
- **coderepository**: Repository metadata and file tracking
- **codeindex**: Symbol index for graph construction
- **core**: Graph abstraction layer, database, errors, telemetry, token economy
