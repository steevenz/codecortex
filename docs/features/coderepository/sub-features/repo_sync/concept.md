# repo_sync: Incremental Filesystem Sync

> **Tool:** repo_sync
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Incremental filesystem sync — detects added/modified/deleted files, re-indexes changes, and removes orphaned DB entries. Supports auto/fast/full modes with dry-run capability.

## Why This Exists

- **Incremental Updates:** Only re-indexes changed files (mtime/size-based diff)
- **Orphan Cleanup:** Removes DB entries for deleted files
- **Multi-Mode:** Auto (smart), fast (mtime only), full (full scan)
- **Dry-Run Safety:** Preview changes before applying
- **AI Actions:** Context-aware recommendations based on sync results

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to repository |
| `mode` | string | ❌ | `auto` | "auto", "fast", "full" |
| `include_patterns` | list | ❌ | — | File patterns to include |
| `exclude_patterns` | list | ❌ | — | Directories to exclude |
| `reindex_updated` | bool | ❌ | `true` | Re-index modified files |
| `remove_deleted` | bool | ❌ | `true` | Remove orphaned DB entries |
| `dry_run` | bool | ❌ | `false` | Preview without applying changes |

## Output

```json
{
  "repo_id": "uuid-v7",
  "repo_path": "/absolute/path",
  "mode": "auto",
  "duration_seconds": 2.5,
  "changes": {
    "files_added": 5,
    "files_modified": 10,
    "files_deleted": 2,
    "symbols_added": 50,
    "symbols_removed": 15,
    "edges_added": 30,
    "edges_removed": 10
  },
  "updated_index": true,
  "ai_actions": [
    {
      "priority": "info",
      "action": "Synced 17 file changes (5 added, 10 modified, 2 deleted).",
      "command_hint": "repo_analyze --repo_path /absolute/path --incremental=true"
    }
  ]
}
```

## AI Actions

1. **Sync Summary** — File and symbol change counts
2. **Analysis Recommendation** — Suggests repo_analyze for updated files
3. **Cleanup Actions** — Orphaned data removal notifications
4. **Next Steps** — Recommended follow-up operations

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_404 | 404 | Repository not indexed |
| REP_500 | 500 | Sync failed |

## Integration

- **repo_init** — For initial repository setup
- **repo_analyze** — For re-analysis after sync
- **repo_staleness** — For checking if sync is needed
