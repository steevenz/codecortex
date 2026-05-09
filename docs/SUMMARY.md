# CodeCortex Documentation Summary

> **Resume of `docs/`** — 50+ files across 7 domains + support matrix
> **Last Updated:** 2026-05-09

## Directory Structure

```
docs/
├── README.md                           # This directory's guide
├── index.md                            # Executive summary & project vision
├── features/                           # 51 files — feature documentation
│   ├── index.md                        # Feature map with domain index
│   ├── README.md                       # Quick reference
│   ├── support-matrix.md               # Languages, frameworks, MCP, LLMs, OS, DBs
│   │
│   ├── codeindex/                      # 13 files — Semantic Code Indexing
│   │   ├── concept.md                  # Why indexing matters
│   │   ├── flow.md                     # Pipeline: discovery → parse → extract → store
│   │   ├── tools.md                    # index_repo, index_file, semantic_search
│   │   ├── output.md                   # Symbols, edges, manifests data shapes
│   │   ├── llm-impact.md               # How LLM gains structured symbol registry
│   │   └── sub-features/              # 7 sub-domains
│   │       ├── tree-sitter-parsing/    # 22 languages, AST extraction
│   │       ├── framework-detection/    # 8 frameworks (Next.js, React, Flutter, etc.)
│   │       ├── semantic-search/        # all-MiniLM-L6-v2 embeddings
│   │       ├── scope-resolution/       # 6-pass cross-file reference resolver
│   │       ├── import-resolution/      # 7 language resolvers
│   │       ├── ast-cache/              # LRU cache, content-hash keyed
│   │       └── worker-pool/            # ThreadPoolExecutor parallelization
│   │
│   ├── codegraph/                      # 14 files — Code Relationship Graph
│   │   ├── concept.md                  # Why graph analysis matters
│   │   ├── flow.md                     # Build → analyze → insights → response
│   │   ├── tools.md                    # 7 MCP tools (graph_query, arch_analyze, etc.)
│   │   ├── output.md                   # Graph JSON shapes, stats
│   │   ├── llm-impact.md               # Architectural awareness for LLMs
│   │   └── sub-features/              # 9 sub-domains
│   │       ├── knowledge-graph/        # Dual-index in-memory graph, O(1) lookups
│   │       ├── community-detection/    # Leiden + Louvain modularity
│   │       ├── execution-flow/         # BFS call chain tracing
│   │       ├── heritage-extraction/    # Class hierarchy (10 languages)
│   │       ├── route-extraction/       # 6 framework route detection
│   │       ├── orm-dataflow/           # 3 ORM model extraction
│   │       ├── entry-point-scoring/    # 0-100 entry point score
│   │       ├── architecture-audit/     # God nodes, dead code, security, complexity
│   │       └── graph-backends/         # Kuzu / Neo4j / FalkorDB / SQLite
│   │
│   ├── coderepository/                 # 4 files — Repository Management
│   │   ├── concept.md                  # Init → sync → index → analyze
│   │   └── sub-features/
│   │       ├── incremental-sync/       # Git diff-based fast re-index
│   │       ├── global-registry/        # ~/.codecortex/registry.json
│   │       └── git-audit/              # Secrets scanning in git history
│   │
│   ├── filesystem/                     # 4 files — File Operations
│   │   ├── concept.md                  # 6 tools, SSRF/path guards
│   │   └── sub-features/
│   │       ├── batch-operations/       # 5 operation types in one call
│   │       ├── file-watcher/           # Watchdog auto-reindex
│   │       └── security-guards/        # 10 rules enforced
│   │
│   ├── coderefactor/                   # 4 files — Code Transformation
│   │   ├── concept.md                  # Semantic rename, impact analysis
│   │   └── sub-features/
│   │       ├── symbol-rename/          # Multi-file via Knowledge Graph
│   │       ├── impact-analysis/        # Blast radius prediction
│   │       └── refactoring-recipes/    # 4 idempotent recipes
│   │
│   ├── codetester/                     # 2 files — Quality Assurance
│   │   ├── concept.md                  # 23+ QA tools supported
│   │   └── sub-features/
│   │       └── background-tasks/       # Async queue + webhook
│   │
│   └── core/                           # 5 files — Shared Infrastructure
│       ├── concept.md                  # Database, token economy, CLI
│       ├── database-schema.md          # 10 tables, ER diagram, 12 indexes
│       └── sub-features/
│           ├── token-economy/           # Token estimation, budget, cache
│           ├── database-maintenance/    # Compact, cleanup, takeout, import
│           └── cli/                     # 12 commands, Artisan-style output
│
├── architecture/                       # System design docs
│   ├── ARCHITECTURE.md                 # Domain map, DI wiring, pipeline
│   └── SECURITY.md                     # SSRF, path validation, label sanitization
│
├── drafts/                             # Work in progress
├── guidelines/                         # Coding & documentation standards
└── versions/                           # Versioned changelogs
```

## Key Metrics

| Metric | Count |
|--------|:-----:|
| Total docs files | 50+ |
| Documented domains | 7 (6 + Core) |
| Sub-features documented | 27 |
| Languages supported | 22 |
| Frameworks detected | 8 |
| MCP tools | 31+ |
| QA tools integrated | 23+ |
| Graph backends | 4 (Kuzu, Neo4j, FalkorDB, SQLite) |
| LLM clients compatible | 7+ |
| OS supported | 3 (Windows, macOS, Linux) |
