# CodeCortex Features

> **Version:** 0.1.0
> **Last Updated:** 2026-05-09
> **Maintainer:** Steeven Andrian

## Feature Map

CodeCortex is organized into **6 bounded contexts (domains)** plus a **Core** shared layer. Each domain delivers specific MCP tools and intelligence capabilities.

---

## Quick Links

- [Support Matrix](support-matrix.md) — Languages, frameworks, MCP, LLMs, OS, databases, backends, QA tools, CI/CD
- [CodeIndex](codeindex/concept.md) — AST parsing, symbol extraction, semantic search
- [CodeGraph](codegraph/concept.md) — Relationship graph, architecture analysis
- [CodeRepository](coderepository/concept.md) — Git integration, multi-repo management
- [Filesystem](filesystem/concept.md) — File operations, security guards
- [CodeRefactor](coderefactor/concept.md) — Symbol rename, search & replace
- [CodeTester](codetester/concept.md) — QA automation, test runners
- [Core](core/concept.md) — Database, token economy, CLI

---

## Domain Index

| Domain | Purpose | MCP Tools | Sub-Features |
|--------|---------|-----------|--------------|
| **CodeIndex** | AST parsing, symbol extraction, semantic search | `index_repo`, `index_file`, `semantic_search` | TreeSitter, Framework Detection, Semantic Search, Scope Resolution, Import Resolution, AST Cache, Worker Pool |
| **CodeGraph** | Relationship graph, architecture analysis, execution flow | `graph_find_symbols`, `graph_query`, `graph_find_related`, `graph_build`, `graph_trace_flow`, `arch_analyze`, `arch_audit` | Knowledge Graph, Community Detection, Execution Flow, Heritage Extraction, Route Extraction, ORM Dataflow, Entry Point Scoring, Architecture Audit, Graph Backends |
| **CodeRepository** | Git integration, multi-repo management, discovery | `repo_init`, `repo_inspect`, `repo_analyze`, `repo_codemap`, `multi_repo_sync`, `repo_sync_incremental`, `git_status`, `git_commit`, `git_audit`, `check_staleness`, `list_repos`, `db_compact`, `repo_cleanup` | Incremental Sync, Global Registry, Git Audit |
| **Filesystem** | File I/O, directory tree, batch operations | `fs_tree`, `fs_read`, `fs_write`, `fs_manage`, `fs_glob`, `fs_batch` | Batch Operations, File Watcher, Security Guards |
| **CodeRefactor** | Symbol rename, search & replace, impact analysis | `search_code`, `search_replace`, `refactor_symbol`, `refactor_impact`, `refactor_apply`, `refactor_rename` | Symbol Rename, Impact Analysis, Refactoring Recipes |
| **CodeTester** | QA automation, test running, linting | `qa_run`, `qa_status` | Background Tasks |
| **Core** | Database, token economy, CLI, backup | CLI: `--compact`, `--cleanup`, `--takeout`, `--import-dump`, `--repositories` | Token Economy, Database Maintenance, CLI |

---

## Feature Documentation Convention

Each feature page follows this structure:
- **concept.md** — Business context, why the feature exists, theoretical foundation
- **flow.md** — Execution pipeline, data flow, sequence of operations
- **tools.md** — MCP tool reference, parameters, examples
- **output.md** — Data shape, schema, example output
- **llm-impact.md** — How this feature improves LLM code understanding
- **examples/** — Sample JSON payloads, input/output pairs
- **support-matrix.md** — Language/framework/backend support tables
- **algorithm.md** — Algorithmic details (for complex features)
- **architecture.md** — Internal class/module structure

---

*This document follows Aegis Codeworks documentation standards.*
