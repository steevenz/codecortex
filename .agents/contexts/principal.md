---
name: project-soul
description: Architectural DNA — CodeCortex MCP Server
version: 3.0.0
last_updated: 2026-05-26
---

# Project Soul — Architectural DNA

## Core Philosophy: Lego Principle
Every module is a standalone brick with standard interfaces. Modules can be added, removed, or replaced without breaking the system.

## Project Identity
- **Domain**: Code Intelligence / AI Coding Agent Infrastructure
- **Stack**: Python 3.12, FastMCP, SQLite (WAL), Kuzu/Neo4j/FalkorDB
- **Standards**: AEGIS Codework v6.2 (Modular Monolith / DDD / HMVC-P)

## Repository Structure
```
src/
├── main.py                    # CortexOrchestrator + 6 tool registration
├── core/                      # Shared: api_response, insight, database, logging
├── api/                       # Unified API tools (4 tools: repository, filesystem, codebase, scaffolder)
├── modules/
│   ├── coderepository/        # Repository lifecycle (git/svn)
│   ├── codeindex/             # AST indexing via Tree-Sitter
│   ├── codegraph/             # Code relationship graph + golden knowledge
│   ├── filesystem/            # File system operations
│   ├── coderefactor/          # Refactoring engine
│   ├── codetester/            # QA testing
│   ├── knowledgegraph/        # Engineering knowledge extraction (8 types)
│   └── idegraph/              # Cross-IDE memory harvesting (16 parsers)
├── scripts/                   # CLI, HTTP server
├── database/                  # codecortex.db (shared SQLite)
├── tests/                     # maker tests
```

## Architectural Patterns
1. **Modular Monolith**: Organized by domain (Bounded Contexts) under `src/modules/`
2. **Domain-Driven Design (DDD)**: Logic in `core/`, `domain/`, `services/`, `api/` per module
3. **Constructor DI**: All dependencies injected — no global state, no `new Class()` in services
4. **Adapter Pattern**: All 3rd-party integrations (TreeSitter, graph backends) wrapped
5. **api/tools.py pattern**: Each module exposes `register_tools(mcp, orchestrator_factory)` for unified registration

## 6 Unified MCP Tools
| Tool | Actions |
|------|---------|
| `codecortex:repository` | init, inspect, analyze, sync, audit, list, status, remove, branches, diff, commit, log, blame |
| `codecortex:filesystem` | read, write, delete, copy, move, search, tree, info, watch, diff, audit |
| `codecortex:codebase` | analyze, search, audit, graph, index, symbols, dependencies, metrics |
| `codecortex:scaffolder` | list_stacks, get_stack, validate_name, list_licenses, generate, make, create |
| `codecortex:knowledge` | extract, query, status, relationships |
| `codecortex:idegraph` | search, get, list, ingest, refresh, health, stats, compact, workspace, harvest |

## Database Architecture
- **Single SQLite**: `database/codecortex.db` with WAL journaling
- All modules share via `DatabaseManager` (thread-safe singleton)
- SideCortex tables co-located (13 tables: sync_runs, ides, workspaces, conversations, messages, etc.)
- Graph backends: Kuzu embedded / Neo4j / FalkorDB for relationship graphs

## Non-Negotiables
1. **No separate databases**: ALL modules must use the shared codecortex.db
2. **DI everywhere**: Constructor injection only — no hardcoded service instantiation
3. **English code**: Identifiers, comments, docs in English
4. **Aegis headers**: Every file must have `@project CodeCortex`, `@author Steeven Andrian`, `@copyright (c) 2026 Aegis Codework`
5. **No Service suffix**: Coding-standard R1 — folder declares role, class does not repeat it
6. **Standard output**: All MCP tools return `api_response()` with `insight` field
