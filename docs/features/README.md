# CodeCortex Documentation Guide

This directory contains all project documentation.

## Quick Links

- [Executive Summary](index.md) — Project overview and vision
- [Features Map](features/index.md) — All features by domain with detailed documentation
- [Architecture](architecture/ARCHITECTURE.md) — Domain map, DI wiring, pipeline flow
- [Security](architecture/SECURITY.md) — SSRF guards, path validation, label sanitization
- [Changelog](versions/CHANGELOG.md) — Version history

## Feature Documentation

Feature documentation is organized in `docs/features/` by domain:

| Domain | Description | Docs |
|--------|-------------|------|
| **CodeIndex** | AST parsing, symbol extraction, semantic search | [View](features/codeindex/concept.md) |
| **CodeGraph** | Relationship graph, architecture analysis | [View](features/codegraph/concept.md) |
| **CodeRepository** | Git integration, multi-repo management | [View](features/coderepository/concept.md) |
| **Filesystem** | File I/O, directory operations | [View](features/filesystem/concept.md) |
| **CodeRefactor** | Symbol rename, search & replace | [View](features/coderefactor/concept.md) |
| **CodeTester** | QA automation, test runners, linters | [View](features/codetester/concept.md) |
| **Core** | Database, token economy, CLI | [View](features/core/concept.md) |

## Documentation Standards

All documentation follows Aegis Codeworks standards:
- **lowercase-dashed** filenames
- Each feature has: concept, flow (optional), tools, output, llm-impact
- Sub-features nested under `sub-features/` with recursive structure
