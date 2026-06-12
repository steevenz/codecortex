# CodeCortex Architecture

## Overview

CodeCortex is a modular-monolith intelligence engine built on Domain-Driven Design (DDD) principles. It decomposes codebase analysis into six autonomous bounded contexts, each owning a single responsibility, wired together via constructor injection (DI) to form a unified intelligence pipeline.

**Architectural Philosophy**: The Lego Principle — atomic, injectable, and independently testable components that scale without friction.

## Domain Map

```
+-------------------------------------------------------------------+
|                        CortexOrchestrator                          |
|                     (Composition Root / DI)                        |
+-----+-------+-------+-------+-------+-------+-------------------+
      |       |       |       |       |       |
      v       v       v       v       v       v
+---------+ +-----+ +-----+ +------+ +-----+ +----------+
| CodeRepo | |Code| |Code| |Files | |Refac| |  Tester  |
|  (Git)   | |Index| |Graph| |System| |tor  | |  (QA)    |
+----+----+ +--+--+ +--+--+ +--+---+ +--+--+ +----+-----+
     |         |        |        |        |         |
     +---------+--------+--------+--------+---------+
                           |
                           v
                +------------------+
                |    SQLite DB     |
                |  (Metadata +     |
                |   Manifest)      |
                +--------+---------+
                         |
                         v
                +------------------+
                |  Graph Backend     |
                | (Neo4j/Kùzu/      |
                |  FalkorDB)        |
                +------------------+
```

## Service Responsibilities

| Domain | Service | Single Responsibility |
|--------|---------|----------------------|
| **CodeRepository** | `CodeRepositoryService` | Physical discovery, Git sync, directory tree, file manifest |
| **CodeIndex** | `CodeIndexService` | AST parsing (Tree-Sitter), symbol extraction, SQLite persistence |
| **CodeGraph** | `CodeGraphService` | Call graph / inheritance resolution, relationship mapping, graph backend writes |
| **Filesystem** | `FilesystemService` | File operations abstraction, path validation, I/O safety guards |
| **CodeRefactor** | `CodeRefactorService` | Safe code transformation, dependency-aware refactoring, Git integration |
| **CodeTester** | `QAService` | Test discovery, coverage analysis, quality metrics reporting |

## Dependency Injection Chain

```python
# main.py — Composition Root
db = DatabaseManager(db_path)
repo_store = SQLiteCodeRepositoryStore(db)
repo_service = CodeRepositoryService(repo_store)

# Bidirectional wiring: graph ↔ index share pre_scan + write_repository_graph
graph_service = CodeGraphService(db)
index_service = CodeIndexService(db, codegraph_service=graph_service)
graph_service.code_index_service = index_service

# Filesystem and Refactor services depend on repository store
fs_service = FilesystemService(db, repo_store)
git_service = GitService(repo_store)
refactor_service = CodeRefactorService(db, fs_service, git_service, graph_service)

# QA service for testing capabilities
qa_service = QAService(db)
```

### Why Bidirectional?

- `CodeIndexService` calls `codegraph_service.write_repository_graph()` during `index_repository()` so AST results flow to the graph backend without re-parsing.
- `CodeGraphService` calls `code_index_service.pre_scan_repository()` during `build_repository_graph()` for Python import resolution.

### Graceful Degradation

All constructor arguments (`code_index_service`, `code_graph_service`) are **optional** (`= None`). If a dependency is missing, the service skips the dependent step and logs a warning — no crash, no circular import risk.

## Unified Pipeline: `analyze_codebase()`

```
CodeRepositoryService.sync_repository(root_path)
         │
         ▼
CodeIndexService.index_repository(repo_id)
         │
         ├───► SQLite (symbols, files, edges)
         │
         ├───► CodeGraphService.write_repository_graph()
         │       └──► Graph Backend (nodes + CALLS/INHERITS/CONTAINS)
         │
         ▼
CodeGraphService.build_comprehensive_report(repo_id)
         │
         ├───► Graph Backend (full graph build)
         │
         ├───► God Nodes (high in-degree)
         ├───► Surprising Connections (cross-community CALLS)
         ├───► Security Hygiene (API_KEY / SECRET scan)
         └───► Community Surprises (Leiden / Louvain)
```

## Data Flow

### 1. Repository Phase

- **Input**: Physical file paths (Git repository root)
- **Process**: Git history extraction, manifest tracking, directory tree construction
- **Output**: Repository metadata, file list with hashes, incremental change detection

### 2. Index Phase

- **Input**: Physical file paths from repository
- **Process**: Tree-Sitter parses each file → `RawSymbol` list → SQLite INSERT
- **Side Effect**: `GraphWriter` simultaneously merges nodes/edges into graph backend
- **Languages**: 20+ programming languages via Tree-Sitter grammars

### 3. Graph Phase

- **Input**: Parsed AST dicts + imports_map
- **Process**: `build_function_call_groups()` + `build_inheritance_and_csharp_files()` → Cypher MERGE
- **Output**: CALLS, INHERITS, CONTAINS edges in graph DB

### 4. Analysis Phase

- **Input**: `repo_id`
- **Process**: Dual read — SQLite metadata (god nodes, security scan) + graph backend (fuzzy search, community detection)
- **Output**: JSON envelope with architectural insights, markdown summary, and metrics

### 5. Refactor Phase (Optional)

- **Input**: Symbol IDs, transformation rules
- **Process**: Dependency-aware code transformation with Git integration
- **Output**: Safe refactoring suggestions with impact analysis

### 6. Testing Phase (Optional)

- **Input**: Repository path, test patterns
- **Process**: Test discovery, execution, coverage analysis
- **Output**: Quality metrics, coverage reports, test suite validation

## Backend Abstraction

`DatabaseManager` owns `GraphManager` which abstracts three backends:

| Backend | Native Fuzzy Search | Best For |
|---------|-------------------|----------|
| Neo4j | Yes (Lucene) | Rich text search, production scale |
| Kùzu | No | Fast analytical queries, embeddable |
| FalkorDB | No | Redis-compatible, high throughput |

`CodeGraphService._find_by_name_fuzzy_portable()` is the fallback for backends without native fuzzy search — capped at **5,000** nodes fetched to prevent OOM.

## Error Boundaries

Each domain catches its own exceptions, logs structured events, and returns partial results:

- `CodeIndexService.index_repository()` — per-file try/except; failed files are skipped, others indexed.
- `CodeGraphService.write_repository_graph()` — edge write failures are logged, not fatal.
- `FilesystemService` — path validation failures raise descriptive errors, I/O errors are logged and retried.
- `CodeRefactorService` — transformation failures are rolled back with Git history preservation.
- `QAService` — test execution failures are logged, partial results returned for successful tests.

## MCP Compliance Layer

CodeCortex implements 5 MCP enhancement layers beyond basic JSON-RPC compliance:

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Transport (stdio/SSE/HTTP)          │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: Logging Notifications — ctx.info/warning/error   │
│  Layer 4: MCP Resources — codecortex:// URIs               │
│  Layer 3: Duration in meta — meta.duration_ms              │
│  Layer 2: Progress — ctx.report_progress()                 │
│  Layer 1: Tool Annotations — readOnlyHint/destructiveHint  │
├─────────────────────────────────────────────────────────────┤
│          6 Unified MCP Tools (action+args dispatch)         │
│          FastMCP + JSON-RPC 2.0 Base Protocol                │
└─────────────────────────────────────────────────────────────┘
```

See [MCP Compliance](../features/core/mcp-compliance.md) for full details.

## Related Documentation

- [MCP Compliance](../features/core/mcp-compliance.md) — annotations, progress, resources, logging
- [API Response Format](./api/specs.md) — envelope shape
- [CLI Commands](../features/core/sub-features/cli/commands.md) — CLI equivalents

## Technology Stack Rationale

### Domain-Driven Design (DDD)
- **Why**: Bounded contexts enforce single responsibility, prevent god classes, and enable independent evolution.
- **Implementation**: Each domain has its own `api/`, `application/`, and `infrastructure/` layers.

### Hexagonal Architecture
- **Why**: External dependencies (Git, Tree-Sitter, Graph DBs) are wrapped in adapters, not leaked into domain logic.
- **Implementation**: Infrastructure layer implements domain interfaces; domain layer remains pure.

### Constructor Injection (DI)
- **Why**: Enables testability, loose coupling, and graceful degradation when dependencies are missing.
- **Implementation**: All services receive dependencies via `__init__()` with optional `= None` defaults.

### SQLite + Graph Backend Hybrid
- **Why**: SQLite for structured metadata (fast queries, ACID guarantees); Graph DB for complex relationship queries.
- **Implementation**: `DatabaseManager` coordinates writes to both backends atomically.

---

*This document follows Aegis Codeworks documentation standards.*
