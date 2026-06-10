# repo_history: Commit History Analysis

> **Tool:** repo_history
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Retrieve and analyze commit history from Git or SVN repositories. Provides commit logs, author statistics, file change tracking, and timeline data for code archaeology and analysis workflows.

## Why This Exists

- **Code Archaeology:** Enables historical analysis of code evolution and contributor patterns
- **Author Statistics:** Identifies top contributors and activity patterns for team insights
- **Bug Magnet Detection:** Links commits to bug reports (when integrated with repo_analyze)
- **Timeline Visualization:** Provides timeline data for activity graphs and velocity metrics
- **Integration Ready:** Works with repo_inspect (churn), repo_analyze (bug magnets), repo_audit (secret scanning)

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to the repository |
| `vcs_type` | string | ❌ | `auto` | "git", "svn", or "auto" (auto-detect) |
| `limit` | int | ❌ | `100` | Maximum number of commits (max 1000) |
| `since` | string | ❌ | — | Start date (ISO format or "N days ago") |
| `until` | string | ❌ | — | End date (ISO format or "now") |
| `author` | string | ❌ | — | Filter by author name or email |
| `file_path` | string | ❌ | — | Filter to specific file history |
| `include_stats` | bool | ❌ | `true` | Include diff statistics (additions/deletions) |
| `include_file_changes` | bool | ❌ | `false` | Include list of changed files per commit |
| `output_format` | string | ❌ | `json` | "json" or "timeline" |

## Output

```json
{
  "repo_path": "/absolute/path",
  "vcs_type": "git",
  "total_commits": 100,
  "commits": [
    {
      "hash": "abc1234def56",
      "full_hash": "abc1234def567890...",
      "author": "John Doe",
      "email": "john@example.com",
      "date": "2026-05-29T10:30:00+00:00",
      "message": "Add new feature",
      "vcs": "git",
      "stats": {
        "files_changed": 5,
        "insertions": 120,
        "deletions": 30
      }
    }
  ],
  "authors": {
    "John Doe": {
      "commits": 45,
      "email": "john@example.com",
      "first_commit": "2026-01-01T00:00:00+00:00",
      "last_commit": "2026-05-29T10:30:00+00:00"
    }
  },
  "timeline": [
    {
      "date": "2026-05-29",
      "author": "John Doe",
      "hash": "abc1234d"
    }
  ],
  "ai_actions": [
    {
      "priority": "info",
      "action": "Retrieved 100 commits from git history.",
      "count": 100,
      "vcs": "git"
    },
    {
      "priority": "info",
      "action": "Top contributor: John Doe with 45 commits.",
      "top_contributors": [
        {"name": "John Doe", "commits": 45},
        {"name": "Jane Smith", "commits": 30}
      ]
    },
    {
      "priority": "low",
      "action": "Use this history data with other tools:",
      "integrations": {
        "repo_inspect": "For churn hotspot analysis",
        "repo_analyze": "For bug magnet detection (commits linked to bugs)",
        "repo_audit": "For scanning commit history for secrets"
      }
    }
  ]
}
```

## AI Actions

The tool provides context-aware ai_actions:

1. **Retrieval Summary** — Confirms commit count and VCS type
2. **Top Contributors** — Identifies most active authors with commit counts
3. **Limit Warning** — Suggests increasing limit if truncated
4. **Integration Guidance** — Recommends cross-tool workflows for deeper analysis

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_404 | 404 | Repository path does not exist |
| REP_400 | 400 | No Git or SVN repository detected |
| REP_TIMEOUT | 408 | History retrieval timed out |
| REP_500 | 500 | Failed to retrieve history |

## Usage Examples

```json
// Get recent 100 commits
{
  "tool": "repo_history",
  "repo_path": "/project"
}

// Get commits from last 30 days
{
  "tool": "repo_history",
  "repo_path": "/project",
  "since": "30 days ago"
}

// Filter by specific author
{
  "tool": "repo_history",
  "repo_path": "/project",
  "author": "john@example.com"
}

// Get file-specific history
{
  "tool": "repo_history",
  "repo_path": "/project",
  "file_path": "src/main.py"
}

// Get timeline data for visualization
{
  "tool": "repo_history",
  "repo_path": "/project",
  "output_format": "timeline"
}
```

## Integration

- **repo_inspect** — For churn hotspot analysis using commit frequency
- **repo_analyze** — For bug magnet detection (commits linked to bugs)
- **repo_audit** — For scanning commit history for secrets
- **repo_git** — For arbitrary git operations beyond history
