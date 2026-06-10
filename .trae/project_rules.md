# CodeCortex Project Rules

## Project Identity
- **Project**: CodeCortex MCP Server
- **Purpose**: Production-grade MCP server for codebase intelligence, indexing, refactoring, and architecture audit
- **Stack**: Python 3.12, DDD + Hexagonal Architecture, Tree-Sitter 0.25.x

## Naming Conventions
- Variables: snake_case
- Functions/Methods: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Files: snake_case.py
- Directories: snake_case

## Architecture Principles
- **Lego Principle**: Everything must be modular, loosely coupled, and highly cohesive
- **Modular Monolith**: Favor structured domain segregation over flat structures
- **DI/IoC**: Use Constructor Injection; avoid hardcoding
- **DTO Pattern**: Use Data Transfer Objects for all layer crossings
- **Adapter Pattern**: Wrap 3rd-party SDKs in local adapters

## Domain Structure
```
src/
├── main.py                    # Entry point - CortexOrchestrator
├── core/                      # Shared infrastructure
│   ├── database.py           # SQLite + Graph backends
│   ├── tree_sitter_manager.py
│   └── backends/             # Kuzu/Neo4j/FalkorDB
├── domain/
│   ├── codeindex/            # Code indexing & parsing
│   ├── codegraph/            # Graph construction & analysis
│   ├── coderepository/       # Git integration
│   ├── coderefactor/         # Refactoring tools
│   ├── codetester/           # QA automation
│   └── filesystem/           # File operations
```

## Code Standards
- **No Hallucination**: Ground every decision in empirical research
- **Eval-First**: Define evaluation criteria before implementation
- **Zero Placeholder**: No TODOs, stubs, or fake implementations
- **Comments**: English only, minimal, explain why not what

## Tooling
- Package Manager: UV
- Testing: Pytest with coverage >90%
- Linting: Pre-commit hooks
- Database: SQLite (WAL) + Kuzu graph

## MCP Tools Available
| Domain | Tools |
|--------|-------|
| CodeRepository | repo_init, repo_inspect, repo_analyze, repo_codemap, multi_repo_sync, git_status, git_commit, git_audit |
| CodeIndex | index_repository, search_code, framework_detection |
| CodeGraph | graph_build, graph_query, graph_find_symbols, graph_find_related, arch_analyze |
| Filesystem | fs_tree, fs_read, fs_write, fs_glob |
| CodeRefactor | refactor_symbol, refactor_impact, refactor_apply |
| CodeTester | qa_run, qa_status |

## Security
- Path/URL validation on all tools
- SSRF guards enabled
- Max 50 repos, max_depth 1-20, max_file_size 10MB
- Secrets in .env only, never committed

## Environment Variables
- `CODECORTEX_DB_PATH`: SQLite database path
- `CODECORTEX_GRAPH_BACKEND`: kuzu | neo4j | falkordb
- `CODECORTEX_MAX_REPOS`: Max repositories to track (default: 50)
- `CODECORTEX_TRANSPORT`: stdio | http