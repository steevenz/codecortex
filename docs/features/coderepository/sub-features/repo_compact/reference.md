# repo_compact — Kompaksi Database & Ekspor Snapshot

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-25

## Overview

`repo_compact` performs database maintenance — orphaned data cleanup, portable snapshot export (`.agents/codecortex.yaml|json`), and SQLite VACUUM — for one or all repositories.

**Difference from `VACUUM`-only**: The legacy `repo_db_compact` only ran `VACUUM`. `repo_compact` adds orphaned cleanup, snapshot export with full symbol/edge data, dry-run simulation, and per-repo targeting.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ❌ | — | If given, compact only this repo. Otherwise entire database. |
| `output_format` | string | ❌ | `"yaml"` | Snapshot format: `"json"` or `"yaml"` |
| `output_path` | string | ❌ | — | Custom snapshot path (default: `<repo_root>/.agents/codecortex.<ext>`) |
| `compact_db` | boolean | ❌ | `true` | Run `VACUUM` on SQLite database |
| `remove_orphaned` | boolean | ❌ | `true` | Delete dangling edges/symbols/files |
| `remove_old_embeddings` | boolean | ❌ | `false` | Delete old embeddings (no-op if table absent) |
| `dry_run` | boolean | ❌ | `false` | Simulate without making changes |

## 5-Phase Flow

```
PHASE 1: Identify target
  • If repo_path given: validate → get repo_id → add WHERE clause
  • If absent: operate on entire database
  • Return 404 if path not found or no repos exist

PHASE 2: Cleanup orphaned data (if remove_orphaned=true AND not dry_run)
  • DELETE FROM edges WHERE source_id/target_id NOT IN symbols
  • DELETE FROM symbols WHERE file_id NOT IN files
  • DELETE FROM files WHERE repository_id NOT IN repositories
  • Count rows affected per table

PHASE 3: Export snapshot (if not dry_run)
  • Build dict: {version, exported_at, repositories, files, symbols, edges}
  • Determine output path:
      - explicit output_path → use it
      - single repo → <repo_root>/.agents/codecortex.<ext>
      - all repos → <db_dir>/codecortex-snapshot.<ext>
  • Write as JSON or YAML
  • Record format, path, size_bytes, entry counts

PHASE 4: Compact DB (if compact_db=true AND not dry_run)
  • Rollback any pending transaction
  • VACUUM → REINDEX → ANALYZE
  • Record size_before, size_after, reduction_percent

PHASE 5: Format response
  • target, repo_id/path, cleanup_stats, snapshot, database_compact
  • Dry run: would-remove counts + database_size_before
```

## Snapshot Format

The snapshot is a portable file stored in `.agents/codecortex.yaml` (or `.json`):

```yaml
version: 1
exported_at: "2026-05-25T13:00:00Z"
repositories:
  - id: "f8a3d2e1-..."
    name: "myapp"
    root_path: "/home/user/projects/myapp"
    last_indexed_at: "2026-05-25T10:00:00Z"
files:
  - id: "file-uuid"
    name: "main.py"
    classification: "code"
    size_bytes: 2048
    repository_id: "f8a3d2e1-..."
symbols:
  - id: "sym-uuid"
    name: "calculate_total"
    symbol_type: "function"
    start_line: 42
    file_id: "file-uuid"
    repository_id: "f8a3d2e1-..."
edges:
  - id: "edge-uuid"
    source_id: "sym-uuid-1"
    target_id: "sym-uuid-2"
    relation_type: "CALLS"
    repository_id: "f8a3d2e1-..."
```

## Response

### Success — Single repo with snapshot + compact

```json
{
  "success": true,
  "status_code": 200,
  "message": "Database compacted and snapshot exported",
  "data": {
    "target": "single_repository",
    "repo_id": "f8a3d2e1-4b5c-6d7e-8f9a-0b1c2d3e4f5a",
    "repo_path": "/home/user/projects/myapp",
    "cleanup_stats": {
      "orphaned_edges_removed": 23,
      "orphaned_symbols_removed": 5,
      "orphaned_files_removed": 0
    },
    "snapshot": {
      "format": "yaml",
      "path": "/home/user/projects/myapp/.agents/codecortex.yaml",
      "size_bytes": 245760,
      "entries": {
        "files": 187,
        "symbols": 1240,
        "edges": 1987
      }
    },
    "database_compact": {
      "before_bytes": 52428800,
      "after_bytes": 28311552,
      "reduction_percent": 46.0
    }
  },
  "meta": {
    "request_id": "req_abc",
    "timestamp": "2026-05-25T13:00:00Z"
  }
}
```

### Dry run

```json
{
  "success": true,
  "data": {
    "target": "single_repository",
    "repo_id": "f8a3d2e1-...",
    "repo_path": "/home/user/projects/myapp",
    "dry_run": true,
    "would_remove_orphaned_edges": 23,
    "would_remove_orphaned_symbols": 5,
    "would_remove_orphaned_files": 0,
    "database_size_before": 52428800
  }
}
```

### Error — Repo path not found

```json
{
  "success": false,
  "status_code": 404,
  "message": "Repository path not found in database",
  "data": { "repo_path": "/invalid/path" }
}
```

## Integration with Other Tools

| Tool | Role in repo_compact |
|------|----------------------|
| SQLite | Source of all data (repositories, files, symbols, edges) |
| Filesystem | Creates `.agents/` directory and writes snapshot file |
| `database_cleanup.py` | `compact_database()` for VACUUM/REINDEX/ANALYZE |
| `repo_list` | Discover repos eligible for compaction |
| `repo_cleanup` | Post-compaction cleanup of stale/orphaned entries |
| `.agents/` | Standard snapshot location (can be git-ignored or committed) |

## When to Use

- **Maintenance:** Reduce database size → `repo_compact()`
- **Before cleanup:** Backup snapshot before removing a repo → `repo_compact(repo_path="/path")`
- **CI/CD artifact:** Export snapshot for pipeline consumption → `repo_compact(output_format="json")`
- **Audit:** Preview what would be removed → `repo_compact(dry_run=true)`
- **Migration:** Export all data before DB rebuild → `repo_compact(output_path="/backup/snapshot.json")`
