# repo_compact: Database Compaction

> **Tool:** repo_compact
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Compact database — orphaned cleanup, snapshot export (.agents/codecortex.yaml|json), and SQLite VACUUM. Supports single-repo or full DB compaction with dry-run mode.

## Why This Exists

- **Orphan Cleanup:** Removes orphaned files, symbols, edges from database
- **Snapshot Export:** Exports repository metadata to portable format
- **Database Optimization:** SQLite VACUUM to reduce file size
- **Dry-Run Safety:** Preview changes before applying
- **AI Actions:** Context-aware recommendations for maintenance

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ❌ | — | Single repository path (omit for full DB) |
| `output_format` | string | ❌ | `yaml` | "yaml" or "json" |
| `output_path` | string | ❌ | — | Custom output path for snapshot |
| `compact_db` | bool | ❌ | `true` | Run SQLite VACUUM |
| `remove_orphaned` | bool | ❌ | `true` | Remove orphaned records |
| `remove_old_embeddings` | bool | ❌ | `false` | Remove old embedding vectors |
| `dry_run` | bool | ❌ | `false` | Preview without applying changes |

## Output

```json
{
  "repo_id": "uuid-v7",
  "repo_path": "/absolute/path",
  "dry_run": false,
  "orphaned_removed": {
    "files": 5,
    "symbols": 15,
    "edges": 10
  },
  "snapshot_exported": true,
  "snapshot_path": "/absolute/path/.agents/codecortex.yaml",
  "db_compacted": true,
  "size_before": 10485760,
  "size_after": 8388608,
  "ai_actions": [
    {
      "priority": "info",
      "action": "Compaction complete: 5 orphaned files removed, DB size reduced 20%.",
      "status": "completed"
    }
  ]
}
```

## AI Actions

1. **Orphan Summary** — Count of removed orphaned records
2. **Size Reduction** — Database size change statistics
3. **Snapshot Status** — Export confirmation with path
4. **Next Steps** — Suggests repo_dump for full backup

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_404 | 404 | Repository not found |
| REP_500 | 500 | Compaction failed |

## Integration

- **repo_cleanup** — For full repository deletion
- **repo_dump** — For full data export
- **repo_restore** — For importing snapshots
