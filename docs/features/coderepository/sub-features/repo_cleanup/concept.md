# repo_cleanup: Irreversible Deletion

> **Tool:** repo_cleanup
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Irreversible deletion of all repository data — files, symbols, edges, graph, findings, and snapshot. Dual lookup (path/id), dry-run mode, and force safety guard.

## Why This Exists

- **Data Removal:** Permanently removes all repository data from database
- **Safety-First:** Requires dry_run preview and force confirmation
- **Dual Lookup:** Supports both repo_path and repo_id for identification
- **Orphan Cleanup:** Removes data for repositories that no longer exist on disk
- **AI Actions:** Detailed preview with record breakdown and safety warnings

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ❌ | — | Repository path (alternative to repo_id) |
| `repo_id` | string | ❌ | — | Repository ID (alternative to repo_path) |
| `delete_snapshot` | bool | ❌ | `true` | Delete snapshot file (.agents/codecortex.yaml) |
| `dry_run` | bool | ❌ | `false` | Preview without applying changes |
| `force` | bool | ❌ | `false` | Bypass safety guard (requires explicit confirmation) |

## Output

```json
{
  "repo_id": "uuid-v7",
  "repo_path": "/absolute/path",
  "dry_run": false,
  "deleted_records": {
    "files": 150,
    "symbols": 450,
    "edges": 300,
    "findings": 10,
    "graph_nodes": 50,
    "graph_edges": 100
  },
  "snapshot_deleted": true,
  "ai_actions": [
    {
      "priority": "critical",
      "action": "Repository data permanently deleted. 1,010 records removed.",
      "status": "completed"
    }
  ]
}
```

## AI Actions

1. **Dry-Run Preview** — Detailed record breakdown by category
2. **Safety Warnings** — Path existence check and force requirement
3. **Deletion Summary** — Total records removed with counts
4. **Next Steps** — Suggests repo_init for re-initialization

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_404 | 404 | Repository not found |
| REP_409 | 409 | Path still exists (safety guard) |
| REP_400 | 400 | Both repo_path and repo_id provided |
| REP_500 | 500 | Cleanup failed |

## Integration

- **repo_compact** — For orphan cleanup before deletion
- **repo_dump** — For full backup before deletion
- **repo_init** — For re-initialization after deletion
