# CodeCortex Features

> **Version:** 0.1.0
> **Last Updated:** 2026-05-09
> **Maintainer:** Steeven Andrian

## Feature Map

CodeCortex exposes **8 unified MCP tools** (`codecortex:repository`, `:filesystem`, `:codebase`, `:scaffolder`, `:knowledge`, `:idegraph`, `:loggraph`, `:search`) that dispatch to 50+ internal domain actions across **6 bounded contexts (domains)** plus **KnowledgeGraph**, **Scaffolder**, **Codelogs**, **UnifiedSearch**, and a **Core** shared layer.

---

## Quick Links

- [Support Matrix](support-matrix.md) — Languages, frameworks, MCP, LLMs, OS, databases, backends, QA tools, CI/CD
- [CodeIndex](codeindex/concept.md) — AST parsing, symbol extraction, semantic search
- [CodeGraph](codegraph/concept.md) — Relationship graph, architecture analysis
- [Codelogs](codelogs/concept.md) — Log management, discovery, visualization, health assessment
- [UnifiedSearch](unified-search/concept.md) — 16-provider search orchestrator (code, files, git, svn, todo, security, empty, blame)
- [CodeAnalysis](codeanalysis/concept.md) — Source code security audit
- [CodeRepository](coderepository/concept.md) — Git integration, multi-repo management
- [Filesystem](filesystem/concept.md) — File operations, security guards
- [CodeRefactor](coderefactor/concept.md) — Symbol rename, search & replace
- [CodeTester](codetester/concept.md) — QA automation, test runners
- [KnowledgeGraph](knowledgegraph/concept.md) — Engineering knowledge extraction from docs
- [Scaffolder](scaffolder/concept.md) — Project scaffolding and code generation
- [Core](core/concept.md) — Database, token economy, CLI
- [Guides](../guides/how-to-setup-mcp.md) — Setup and operations guides

---

## Domain Index

| Domain | Purpose | Domain Actions (routed via unified MCP tools) | Sub-Features |
|--------|---------|-----------|--------------|
| **CodeIndex** | AST parsing, symbol extraction, semantic search | `index_repo`, `index_file`, `semantic_search` | TreeSitter, Framework Detection, Semantic Search, Scope Resolution, Import Resolution, AST Cache, Worker Pool |
| **CodeGraph** | Relationship graph, architecture analysis, execution flow | `graph_find_symbols`, `graph_query`, `graph_find_related`, `graph_build`, `graph_trace_flow`, `arch_analyze`, `arch_audit` | Knowledge Graph, Community Detection, Execution Flow, Heritage Extraction, Route Extraction, ORM Dataflow, Entry Point Scoring, Architecture Audit, Graph Backends |
| **CodeAnalysis** | Code quality gate with 24 audit categories, auto-fix generation, syntax detection | `code_analyze`, `code_search`, `code_audit`, `code_status` | Code Analyze, Code Search, Code Audit, Code Status |
| **CodeRepository** | Multi-repo management, indexing, discovery, Git/SVN operations | `repo_init`, `repo_inspect`, `repo_analyze`, `repo_sync`, `repo_audit`, `repo_staleness`, `repo_list`, `repo_db_compact`, `repo_cleanup`, `repo_git`, `repo_svn` | Incremental Sync, Global Registry, Git Audit, SVN Support |
| **Filesystem** | File I/O, search, disk usage, file watching, security audit | `fs_manage`, `fs_search`, `fs_watch`, `fs_df`, `fs_audit` | Batch Operations, File Watcher, Security Guards, File Conversion |
| **CodeRefactor** | Symbol rename, impact analysis, refactoring recipes | `refactor_symbol`, `refactor_impact`, `refactor_apply` (search_code/search_replace removed — use `fs_search(use_index=True)`) | Symbol Rename, Impact Analysis, Refactoring Recipes |
| **CodeTester** | QA automation, test running, linting | `qa_run`, `qa_status` | Background Tasks |
| **KnowledgeGraph** | Engineering knowledge extraction from docs — 8 types, pattern-based | `codecortex:knowledge` | Knowledge Extraction, Importance Scoring, Relationship Mapping, GoldenKnowledge Store |
| **Scaffolder** | Project scaffolding, stack detection, boilerplate generation | `scaffold_list_stacks`, `scaffold_get_stack`, `scaffold_validate_name`, `scaffold_generate`, `scaffold_make`, `scaffold_create` | Stack Detection, Naming Conventions, License Templates, Project Generation |
| **Codelogs** | Log management, discovery, visualization, health | `codecortex:loggraph` | Scan, Search, Graph, Discover, Cleanup, Rotate, Validate, Info |
| **UnifiedSearch** | 16-provider search orchestrator | `codecortex:search` | Codebase, Filesystem, RepoWT, Graph, IDEGraph, Knowledge, CrossProject, CodeIndex, AgentArt, Codelogs, Todo, Stub, Security, Empty, SVN, Blame |
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

---

*This document follows CODDY Codeworks documentation standards.*
