# Incremental Sync

> **Source:** `CodeRepositoryService.sync_repository_incremental()`

## Concept

Incremental sync uses `git diff --name-only HEAD` to identify files changed since the last commit, then re-indexes only those files. This is **dramatically faster** than full re-index for large codebases.

## Flow

```
repo_sync_incremental(path)
    │
    ▼
  git diff --name-only HEAD ──> List of changed files
    │
    ▼
  For each changed file:
    ├── New file   ──> Parse + Insert
    ├── Modified   ──> Parse + Update
    └── Deleted    ──> Remove from index
    │
    ▼
  Update manifest entries with new hashes
    │
    ▼
  Return: repo_id, [changed_files], count
```

## Performance

| Repository Size | Full Re-index | Incremental (1 file change) |
|----------------|--------------|---------------------------|
| 100 files | 5-10s | 0.1-0.3s |
| 1000 files | 30-60s | 0.1-0.3s |
| 10000 files | 5-10min | 0.1-0.3s |

## Fallback

If `git diff` fails (e.g., first commit, detached HEAD), falls back to full sync.
