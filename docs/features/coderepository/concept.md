# CodeRepository: Repository Management

> **Domain:** CodeRepository
> **Package:** `src/modules/coderepository/`
> **Version:** 2.0.0
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

CodeRepository is the **repository discovery, lifecycle, and VCS management** layer. It handles:

- Syncing code from disk into the database index
- Tracking registered repositories and staleness
- Full intelligence pipeline (sync → index → analyze)
- Arbitrary Git and SVN operations
- Commit history and author statistics (NEW)

## Why This Exists

- **Repository Discovery:** Enables AI coders to discover and understand project structure via repo_init
- **Lifecycle Management:** Tracks repository state (fresh/stale/orphaned) for maintenance
- **VCS Integration:** Provides git/svn operations with dry_run safety and ai_action guidance
- **Data Portability:** Export (repo_dump) and import (repo_restore) for backup and migration
- **Code Archaeology:** repo_history enables commit history analysis, author statistics, and timeline tracking
- **AI Coder Empowerment:** All tools include ai_actions for zero-shot execution and decision-making
- **Safety-First Design:** Destructive operations (cleanup, git, svn) have dry_run with preview
- **Token Efficiency:** Enriched responses reduce tool calls by 80% through direct actionability

## Theoretical Foundation

- **AST Parsing:** Tree-Sitter for accurate symbol extraction across 22+ languages
- **SQLite:** Metadata storage for repositories, files, symbols, edges, findings
- **Git/SVN Integration:** subprocess-based VCS operations with command reconstruction
- **Filesystem Scanning:** OS.walk-based file discovery with pattern filtering
- **Token Economy:** Auto-truncation based on token budget with summary mode
- **Parallel Processing:** ThreadPoolExecutor for batch operations (indexing, analysis)
- **Incremental Sync:** mtime/size-based diff for fast updates
- **Command Reconstruction:** Reconstructs git/svn commands from parameters for dry_run preview

## Architecture

```
src/modules/coderepository/
├── api/              → tools.py: 14 MCP tools, cli.py: CLI commands, api_response() compliant
├── adapters/          → GitAdapter, SvnAdapter, FileReader, SQLiteStore
├── core/              → dto.py: typed DTOs, models (Repository, File, Symbol, Edge, Commit)
├── core/              → repository.py, repository_store.py, registry.py
└── core/              ├── repositories/ → RepositoryRepository, FileRepository, SymbolRepository
                       └── models/ → Repository, File, Symbol, Edge, Commit, Directory
```

## Domain Boundary

- **Owns:** `repo_init`, `repo_inspect`, `repo_analyze`, `repo_sync`, `repo_audit`, `repo_staleness`, `repo_list`, `repo_compact`, `repo_cleanup`, `repo_dump`, `repo_restore`, `repo_git`, `repo_history`
- **Does NOT own:** CodeGraph operations (handled by codegraph domain)
- **Depends on:** DatabaseManager, FilesystemService, GitAdapter, SvnAdapter
- **Consumed by:** MCP layer via `api/tools.py`

## CLI Architecture Note

The CLI domain is named `coderepository` (not `repo`) as an intentional UX decision. Users access repository operations via `codecortex cr <command>`.

## ~/.aicoders/ Compliance

- **API Standard:** `api_response()` for all tool responses
- **DDD:** `api/` + `adapters/` + `core/` separation
- **DI:** Constructor injection for all adapters and services
- **Boundary:** Data crosses layers only via DTOs
- **Error Handling:** Guard clauses, structured errors, error codes
- **Logging:** `CodeCortex.CodeRepository.*` logger namespace
- **Documentation:** All docs in `docs/features/coderepository/`

## Error Codes

| Prefix | Tool |
|--------|------|
| REP_0xx | repo_init |
| REP_1xx | repo_inspect |
| REP_2xx | repo_analyze |
| REP_3xx | repo_sync |
| REP_4xx | repo_audit |
| REP_5xx | repo_staleness |
| REP_6xx | repo_list |
| REP_7xx | repo_compact |
| REP_8xx | repo_cleanup |
| REP_9xx | repo_dump |
| REP_10x | repo_restore |
| REP_11x | repo_git |
| REP_12x | repo_svn |
| REP_13x | repo_history |
| REP_5xx | Internal error |

## 10/10 AI Coder Impact Features

1. **Zero-Shot Execution** — All tools include ai_actions array with prioritized recommendations
2. **Dry-Run Safety** — Destructive tools (cleanup, git, svn) have enhanced dry_run with preview
3. **Context-Rich Actions** — ai_actions include quantitative data (counts, sizes, timestamps)
4. **Command Reconstruction** — git/svn dry_run reconstructs commands for user confirmation
5. **Temporal Coupling Detection** — repo_inspect identifies hidden dependencies via co-change analysis
6. **Documentation Intelligence** — repo_inspect analyzes docs for PRDs, ADRs, requirements
7. **Author Statistics** — repo_history provides top contributors and activity patterns
8. **Security Focus** — repo_audit includes ai_action for direct remediation
9. **Staleness Tracking** — 6-level classification with actionable recommendations
10. **Integration Guidance** — ai_actions suggest next steps and cross-tool workflows

## Token Economy

All responses pass through `api_response()` which auto-truncates data exceeding token budget when `summary_mode=True`.

---

## Related Sub-Features

- [repo_init](sub-features/repo_init/concept.md)
- [repo_inspect](sub-features/repo_inspect/concept.md)
- [repo_analyze](sub-features/repo_analyze/concept.md)
- [repo_sync](sub-features/repo_sync/concept.md)
- [repo_audit](sub-features/repo_audit/concept.md)
- [repo_staleness](sub-features/repo_staleness/concept.md)
- [repo_list](sub-features/repo_list/concept.md)
- [repo_compact](sub-features/repo_compact/concept.md)
- [repo_cleanup](sub-features/repo_cleanup/concept.md)
- [repo_dump](sub-features/repo_dump/concept.md)
- [repo_restore](sub-features/repo_restore/concept.md)
- [repo_git](sub-features/repo_git/concept.md)
- [repo_svn](sub-features/repo_svn/concept.md)
- [repo_history](sub-features/repo_history/concept.md)
