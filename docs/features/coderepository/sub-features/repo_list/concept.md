# repo_list: Repository Discovery

> **Tool:** repo_list
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

List all registered repositories with filtering, metadata enrichment, VCS status, pagination, and Markdown table output. Reads from SQLite `repositories` table (not JSON registry).

## Why This Exists

- **Repository Discovery:** Enables AI coders to discover all indexed repositories
- **Fleet Management:** Track repository status (active, orphaned, stale)
- **Metadata Enrichment:** File counts, symbol counts, language breakdown
- **VCS Status:** Real-time git/svn status for each repository
- **AI Actions:** Context-aware recommendations for repository management

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `filter_status` | string | ❌ | — | Filter by status (active, orphaned, stale) |
| `include_metadata` | bool | ❌ | `true` | Include file/symbol/edge counts |
| `include_vcs_status` | bool | ❌ | `true` | Include real-time VCS status |
| `limit` | int | ❌ | `50` | Max results per page |
| `offset` | int | ❌ | `0` | Pagination offset |
| `order_by` | string | ❌ | `created_at` | Sort field |
| `order_dir` | string | ❌ | `desc` | Sort direction (asc/desc) |
| `output_format` | string | ❌ | `json` | "json" or "markdown" |

## Output

```json
{
  "total_count": 25,
  "limit": 50,
  "offset": 0,
  "repositories": [
    {
      "id": "uuid-v7",
      "name": "myproject",
      "root_path": "/absolute/path",
      "sync_at": "2026-05-29T10:00:00Z",
      "status": "active",
      "metadata": {
        "files": 150,
        "symbols": 450,
        "edges": 300
      },
      "vcs_status": {
        "branch": "main",
        "commit": "abc1234",
        "dirty": false
      }
    }
  ],
  "ai_actions": [
    {
      "priority": "medium",
      "action": "2 orphaned repositories detected. Consider cleanup.",
      "command_hint": "repo_cleanup --repo_path /path/to/orphan"
    }
  ]
}
```

## AI Actions

1. **Orphaned Repos** — Alerts for repositories with missing paths
2. **Stale Repos** — Identifies repositories needing sync
3. **Fleet Size** — Repository count with management tips
4. **Next Steps** — Suggests repo_cleanup, repo_sync, repo_staleness

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_500 | 500 | Failed to query repositories |

## Integration

- **repo_cleanup** — For removing orphaned repositories
- **repo_staleness** — For checking stale repositories
- **repo_sync** — For updating stale repositories
