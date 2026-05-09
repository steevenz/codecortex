# Core: Database Schema

> **Source:** `src/core/database.py`

## Tables

| # | Table | Records | Purpose |
|---|-------|---------|---------|
| 1 | `repositories` | 1 per repo | Repository metadata (id, name, root path, timestamps) |
| 2 | `directories` | 1 per dir | Directory hierarchy with parent_id for nesting |
| 3 | `files` | 1 per file | File metadata (path, size, hash, content, classification) |
| 4 | `symbols` | 5-50+ per file | Functions, classes, variables, imports |
| 5 | `edges` | 10-100+ per file | Relationships: CALLS, INHERITS, IMPORTS, USES, DEFINES |
| 6 | `insights` | 0-5 per file | Architectural/security intelligence findings |
| 7 | `manifest_entries` | 1 per file | Hash + size for incremental sync tracking |
| 8 | `commits` | 1 per commit | Git commit metadata (hash, author, message, timestamp) |
| 9 | `file_commits` | 1 per file-commit | Mapping of files to commits with change type (A/M/D/R/T) |
| 10 | `execution_tasks` | 1 per task | Background QA task tracking (status, payload, result) |

## Entity Relationship

```
repositories 1──N directories 1──N files 1──N symbols 1──N edges (as source/target)
repositories 1──N commits 1──N file_commits N──1 files
repositories 1──N insights
repositories 1──N manifest_entries
repositories 1──N execution_tasks
```

## Key Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_files_repo` | `repository_id` | Fast repo-scoped file queries |
| `idx_symbols_code` | `code` | Symbol name lookup |
| `idx_edges_source` | `source_id` | Find all outgoing edges from a symbol |
| `idx_edges_target` | `target_id` | Find all incoming edges to a symbol |
| `idx_commits_hash` | `commit_hash` | Fast commit deduplication |
| `uq_directories_repo_relpath` | `repository_id, relative_path` | Prevent duplicate directory entries |
| `uq_files_repo_dir_name` | `repository_id, directory_id, name` | Prevent duplicate file entries |
| `uq_manifest_repo_path` | `repository_id, file_path` | Unique manifest tracking |
