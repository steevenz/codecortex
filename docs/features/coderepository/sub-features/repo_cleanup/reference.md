# repo_cleanup — Hapus Repository dari Database CodeCortex

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-25

## Overview

`repo_cleanup` permanently deletes all CodeCortex data for a repository — files, symbols, edges, graph nodes, insights, commits, findings, and registry entry — with safety guards for accidental deletion.

**Safety features**: dual lookup (path or ID), `force` flag to confirm deletion when path still exists on disk, `dry_run` to preview impact.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ❌* | — | Absolute path of the repository to delete |
| `repo_id` | string | ❌* | — | UUID of the repository (alternative to `repo_path`) |
| `delete_snapshot` | boolean | ❌ | `true` | Delete `.agents/codecortex.yaml` or `.json` if exists |
| `dry_run` | boolean | ❌ | `false` | Simulate without making changes |
| `force` | boolean | ❌ | `false` | Force delete even if `repo_path` still exists on disk |

> *Either `repo_path` or `repo_id` is required.

## 5-Phase Flow

```
PHASE 1: Validate target
  • Look up repo by repo_path (via get_repository_by_path) or repo_id (direct SQL)
  • Return 404 if not found
  • Return 400 if neither param provided
  • Return 409 (conflict) if path exists on disk AND force=false

PHASE 2: Count & build plan
  • Count records per table (edges, insights, symbols, file_commits, commits,
    manifest_entries, execution_tasks, files, directories)
  • Check extra tables (findings, history_findings, graph_edges, graph_nodes)
    — graceful if absent
  • Check for existing snapshot file (.agents/codecortex.yaml|json)
  • If dry_run → return plan without executing

PHASE 3: Execute deletion
  • DELETE in dependency order (edges → symbols → files → directories → repo)
  • DELETE extra tables if they exist
  • DELETE repository row
  • COMMIT transaction
  • Remove entry from global registry (~/.codecortex/registry.json)

PHASE 4: Delete snapshot (if delete_snapshot=true)
  • Unlink .agents/codecortex.yaml or .json at repo root
  • Graceful if file already missing

PHASE 5: Return response
  • deleted_records: per-table count of deleted rows
  • snapshot_deleted: boolean
  • snapshot_path: path of deleted snapshot (if any)
```

## Deletion Order & Tables

| Order | Table | Condition |
|-------|-------|-----------|
| 1 | `edges` | WHERE repository_id = ? |
| 2 | `insights` | WHERE repository_id = ? |
| 3 | `symbols` | WHERE repository_id = ? |
| 4 | `file_commits` | WHERE repository_id = ? |
| 5 | `commits` | WHERE repository_id = ? |
| 6 | `manifest_entries` | WHERE repository_id = ? |
| 7 | `execution_tasks` | WHERE repository_id = ? |
| 8 | `files` | WHERE repository_id = ? |
| 9 | `directories` | WHERE repository_id = ? |
| — | `findings` | (if table exists) |
| — | `history_findings` | (if table exists) |
| — | `graph_edges` | (if table exists) |
| — | `graph_nodes` | (if table exists) |
| — | `repositories` | WHERE id = ? (last) |

## Response

### Success — Full cleanup with snapshot

```json
{
  "success": true,
  "status_code": 200,
  "message": "Repository and all associated data removed from CodeCortex",
  "data": {
    "target": {
      "repo_id": "f8a3d2e1-...",
      "repo_path": "/home/user/projects/myapp"
    },
    "deleted_records": {
      "edges": 1987,
      "insights": 2,
      "symbols": 1240,
      "file_commits": 150,
      "commits": 45,
      "manifest_entries": 187,
      "execution_tasks": 0,
      "files": 187,
      "directories": 12,
      "findings": 12,
      "graph_edges": 1987,
      "graph_nodes": 1240,
      "repositories": 1
    },
    "snapshot_deleted": true,
    "snapshot_path": "/home/user/projects/myapp/.agents/codecortex.yaml"
  }
}
```

### Dry run

```json
{
  "success": true,
  "data": {
    "dry_run": true,
    "would_delete": {
      "repo_id": "f8a3d2e1-...",
      "repo_path": "/home/user/projects/myapp",
      "total_records": 6897,
      "snapshot_file": "/home/user/projects/myapp/.agents/codecortex.yaml"
    }
  }
}
```

### Error — Missing target param

```json
{
  "success": false,
  "status_code": 400,
  "message": "Either repo_path or repo_id is required",
  "data": { "suggestion": "Provide repo_path or repo_id" }
}
```

### Error — Not found

```json
{
  "success": false,
  "status_code": 404,
  "message": "Repository not found in CodeCortex database",
  "data": { "provided": { "repo_path": "/nonexistent", "repo_id": null } }
}
```

### Conflict — Path still exists

```json
{
  "success": false,
  "status_code": 409,
  "message": "Repository path still exists on disk. Use force=true to proceed with database deletion only (files will remain).",
  "data": {
    "repo_path": "/home/user/projects/myapp",
    "suggestion": "If you want to delete files from disk as well, remove them manually first, then retry cleanup."
  }
}
```

## Integration

| Tool | Role |
|------|------|
| SQLite | Primary data source for deletion |
| RegistryManager | Global registry cleanup (~/.codecortex/registry.json) |
| `repo_list` | Discover stale/orphaned repos to clean up |
| `repo_compact` | Take snapshot backup before deletion |
| `repo_dump` | Export data before deletion |
