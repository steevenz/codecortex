# repo_staleness: VCS Staleness Detection

> **Tool:** repo_staleness
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

6-level VCS staleness detection (fresh/behind/ahead/diverged/dirty/outdated). Compares index against local HEAD + remote tracking. Optional git fetch and working tree analysis with AI impact assessment.

## Why This Exists

- **Sync Status:** Detects if repository index is behind VCS HEAD
- **Remote Comparison:** Compares local state against remote tracking branch
- **Working Tree Analysis:** Detects uncommitted changes
- **AI Impact Assessment:** Evaluates staleness impact on AI analysis accuracy
- **Actionable Recommendations:** Provides specific next steps for each staleness level

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to repository |
| `compare_remote` | bool | ❌ | `true` | Compare against remote tracking branch |
| `fetch_remote` | bool | ❌ | `false` | Fetch remote before comparison |
| `include_local_changes` | bool | ❌ | `true` | Include working tree analysis |
| `timeout_seconds` | int | ❌ | `30` | Timeout for git operations |

## Output

```json
{
  "repo_id": "uuid-v7",
  "repo_path": "/absolute/path",
  "staleness_level": "behind",
  "status": {
    "local_commit": "abc1234",
    "remote_commit": "def5678",
    "commits_behind": 5,
    "commits_ahead": 0
  },
  "working_tree": {
    "has_changes": true,
    "modified_files": 3,
    "untracked_files": 2
  },
  "ai_impact": {
    "score": 70,
    "recommendation": "Run repo_sync to update index"
  },
  "ai_actions": [
    {
      "priority": "medium",
      "action": "Repository is 5 commits behind remote. Run repo_sync to update.",
      "command_hint": "repo_sync --repo_path /absolute/path --mode=auto"
    }
  ]
}
```

## AI Actions

1. **Staleness Alert** — Current status with commit counts
2. **Sync Recommendation** — Suggests repo_sync for updates
3. **Working Tree Alert** — Uncommitted changes notification
4. **Next Steps** — Recommended actions based on staleness level

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_404 | 404 | Repository not indexed |
| REP_500 | 500 | Staleness check failed |

## Integration

- **repo_sync** — For updating stale repositories
- **repo_git** — For manual git operations
- **repo_init** — For re-initialization if severely outdated
