# repo_staleness — Deteksi Ketertinggalan Index dari Remote VCS

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-25

## Overview

`repo_staleness` detects whether the CodeCortex index is behind the current VCS state — comparing last indexed commit/revision against local HEAD and optionally the remote tracking branch. Read-only; never modifies data.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to the repository root |
| `compare_remote` | boolean | ❌ | `true` | Compare with remote tracking branch |
| `fetch_remote` | boolean | ❌ | `false` | Run `git fetch` before comparing (network) |
| `include_local_changes` | boolean | ❌ | `true` | Check uncommitted working tree changes |
| `timeout_seconds` | integer | ❌ | `30` | Timeout for network/git operations |

## 6-Level Classification

| Level | Meaning | Condition |
|-------|---------|-----------|
| `fresh` | Index matches remote + working tree | 0 behind, 0 ahead, 0 dirty, age ≤ 7 days |
| `behind` | Remote is ahead (need pull) | `commits_behind > 0 && commits_ahead == 0` |
| `ahead` | Local is ahead (need push) | `commits_ahead > 0 && commits_behind == 0` |
| `diverged` | Local and remote diverged (need merge/rebase) | `commits_ahead > 0 && commits_behind > 0` |
| `dirty` | Uncommitted changes in working tree | `working_tree.has_uncommitted == true` |
| `outdated` | Index age > 7 days | `index_age_days > 7` |
| `unknown_remote` | Remote unreachable | `compare_remote=true` but fetch/tracking failed |

## 5-Phase Flow

```
PHASE 1: Get DB metadata
  • Look up repository by path
  • Extract last_indexed_at, repo_id
  • Return 400 if never indexed

PHASE 2: (Optional) Fetch remote
  • If fetch_remote=true: run `git fetch` (Git) or `svn info` (SVN)
  • Capture timeout/network errors for 207 response

PHASE 3: Get VCS status
  • Git: branch, HEAD commit, remote tracking, ahead/behind, porcelain
  • SVN: revision, URL, remote revision, status

PHASE 4: Compare + classify
  • Merge VCS data with DB last_indexed_at
  • Run 6-level classifier (dirty → outdated → diverged → behind → ahead → fresh)

PHASE 5: Return response
  • Status, details, recommendation, AI impact
  • 207 if remote unreachable (partial data)
```

## Response

### Success — Behind (needs pull)

```json
{
  "success": true,
  "status_code": 200,
  "message": "Repository index is behind remote by 3 commits",
  "data": {
    "repo_id": "f8a3d2e1-...",
    "repo_path": "/home/user/projects/myapp",
    "vcs_type": "git",
    "status": "behind",
    "details": {
      "current_branch": "main",
      "local_commit": "a1b2c3d",
      "remote_commit": "e5f6g7h",
      "remote_tracking": "origin/main",
      "commits_behind": 3,
      "commits_ahead": 0,
      "last_indexed_commit": "2026-05-23T10:00:00Z",
      "index_age_days": 2,
      "working_tree": {
        "has_uncommitted": false,
        "modified_files": 0,
        "added_files": 0,
        "deleted_files": 0
      }
    },
    "recommendation": "Run `git pull` then `repo_sync --mode auto` to update index.",
    "ai_impact": "CodeCortex index does not contain the latest commits. Semantic search may miss recent changes."
  }
}
```

### Dirty working tree

```json
{
  "success": true,
  "data": {
    "status": "dirty",
    "details": {
      "working_tree": {
        "has_uncommitted": true,
        "modified_files": 2,
        "added_files": 1,
        "deleted_files": 0
      }
    },
    "recommendation": "Commit or stash changes, then run `repo_sync` to update the index.",
    "ai_impact": "Uncommitted changes are not reflected in the index. Use fs_search for real-time search."
  }
}
```

### Fresh

```json
{
  "success": true,
  "data": {
    "status": "fresh",
    "message": "Index is up to date with remote and working tree.",
    "recommendation": "No action needed.",
    "ai_impact": "Index is current. All search and analysis results are reliable."
  }
}
```

### Remote unreachable (207)

```json
{
  "success": true,
  "status_code": 207,
  "message": "Could not reach remote. Returning local staleness only.",
  "data": {
    "status": "unknown_remote",
    "error": "git fetch failed: network unreachable",
    "recommendation": "Check internet connection or set fetch_remote=false."
  }
}
```

## Integration

| Tool | Role |
|------|------|
| Git/SVN CLI | Real-time VCS status (branch, commits, ahead/behind) |
| SQLite | Last indexed timestamp from repositories table |
| `repo_sync` | Recommended action to update index |
| `repo_list` | Discover repos to check for staleness |
