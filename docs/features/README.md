# CodeCortex Documentation Guide

This directory contains all project documentation following CODDY Codeworks standards.

## Quick Links

- [Executive Summary](index.md) — Project overview and vision
- [Features Map](features/index.md) — All features by domain with detailed documentation
- [Architecture](architecture/architecture.md) — Domain map, DI wiring, pipeline flow
- [Security](architecture/security.md) — SSRF guards, path validation, label sanitization
- [Changelog](versions/changelog.md) — Version history

## 6 Unified MCP Tools

CodeCortex exposes **6 consolidated MCP tools** that dispatch to 35+ internal domain actions. Each tool uses an `action + args` pattern.

| Tool | Purpose | Key Actions |
|------|---------|-------------|
| **codecortex:repository** | Repository lifecycle | init, inspect, analyze, sync, audit, staleness, list, compact, cleanup, dump, restore, git, svn |
| **codecortex:filesystem** | File operations | read, write, delete, copy, move, mkdir, list, search, watch, usage, audit |
| **codecortex:codebase** | Code intelligence | analyze, search, audit, graph, status, index, test, refactor |
| **codecortex:scaffolder** | Project scaffolding | list_stacks, get_stack, validate_name, list_licenses, generate_content, generate_class, create_project |
| **codecortex:knowledge** | Knowledge extraction | extract, query, status, relationships, validate |
| **codecortex:idegraph** | IDE memory | ingest, search, compact, export, timeline, state, artifacts |

## Feature Documentation

Feature documentation is organized in `docs/features/` by domain:

| Domain | Description | Docs |
|--------|-------------|------|
| **CodeIndex** | AST parsing, symbol extraction, semantic search | [View](codeindex/concept.md) |
| **CodeGraph** | Relationship graph, architecture analysis | [View](codegraph/concept.md) |
| **CodeRepository** | Git integration, multi-repo management | [View](coderepository/concept.md) |
| **Filesystem** | File I/O, directory operations | [View](filesystem/concept.md) |
| **CodeRefactor** | Symbol rename, search & replace | [View](coderefactor/concept.md) |
| **CodeTester** | QA automation, test runners, linters | [View](codetester/concept.md) |
| **Core** | Database, token economy, CLI | [View](core/concept.md) |
| **CodeAnalysis** | Source code security audit | [View](codeanalysis/concept.md) |
| **KnowledgeGraph** | Engineering knowledge extraction | [View](knowledgegraph/concept.md) |
| **Scaffolder** | Project scaffolding and templates | [View](scaffolder/concept.md) |
| **IdeGraph** | Cross-IDE contextual memory | [View](idegraph/concept.md) |

## Documentation Standards

All documentation follows CODDY Codeworks standards:
- **lowercase-dashed** filenames
- Each feature has: concept, flow (optional), tools, output, llm-impact
- Sub-features nested under `sub-features/` with recursive structure

---

*Source of Truth: `src/main.py` — 6 unified MCP tools with action+args pattern*
