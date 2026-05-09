# CodeRepository: Repository Management

> **Domain:** CodeRepository
> **Package:** `src/domain/coderepository/`

## Business Context

CodeRepository is the **discovery and lifecycle management** layer. It handles syncing code from disk (or Git) into the database, tracking which repositories are registered, managing staleness detection, and orchestrating the full intelligence pipeline.

## Why This Exists

- **Single entry point:** Every operation starts with a repository. `repo_init` creates the root, `index_repo` processes files, `graph_build` connects them.
- **Multi-repo support:** Track up to 50 repositories in parallel with per-repo isolation.
- **Staleness detection:** Know when a repo is behind HEAD and needs re-indexing.
- **Incremental sync:** Re-index only changed files via `git diff` — much faster than full re-index.
- **Global registry:** `~/.codecortex/registry.json` persists repo state across sessions.

## Flow

```
repo_init(path) ──> File discovery ──> Store in DB
       │                                      │
       ▼                                      ▼
repo_sync_incremental(path) ──> git diff ──> Re-index changed files
       │                                      │
       ▼                                      ▼
repo_analyze(path) ──> Full pipeline: init + index + analyze
```

## MCP Tools

| Tool | Function |
|------|----------|
| `repo_init` | Initialize a repository for analysis |
| `repo_inspect` | Get repo metadata or directory structure |
| `repo_analyze` | Full intelligence pipeline (init + index + analyze) |
| `repo_codemap` | High-density symbol map of the codebase |
| `multi_repo_sync` | Sync multiple repos in one call |
| `repo_sync_incremental` | Fast git diff-based partial sync |
| `git_status` | Current git working tree status |
| `git_commit` | Stage and commit changes |
| `git_audit` | Scan git history for hardcoded secrets |
| `check_staleness` | Check if an indexed repo is behind HEAD |
| `list_repos` | List all registered repositories |
| `db_compact` | VACUUM the database to reclaim space |
| `repo_cleanup` | Delete all data for a project (IRREVERSIBLE) |
