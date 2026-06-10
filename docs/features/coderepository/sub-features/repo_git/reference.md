# repo_git — Arbitrary Git Operations

> **Source:** `src/domain/filesystem/infrastructure/fs_git.py` — `FsGitHelper`
> **Since:** 2026-05-24

## Overview

`repo_git` executes **arbitrary Git subcommands** with structured parameters and parsed responses. Unlike `repo_init` (lifecycle management) or `repo_audit` (security scanning), `repo_git` is the general-purpose Git tool for AI Coder to perform any VCS operation.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to the Git repository root |
| `subcommand` | string | ✅ | — | Git subcommand (e.g. `"status"`, `"commit"`, `"push"`) |
| `args` | array | ❌ | `[]` | Positional arguments (e.g. `["-m", "message"]`) |
| `flags` | object | ❌ | `{}` | Flags as dict (e.g. `{"--oneline": true, "-n": 5}`) |
| `dry_run` | boolean | ❌ | `false` | Simulate without executing |
| `timeout_seconds` | integer | ❌ | `300` | Timeout for long operations (clone, push, pull) |

## Supported Subcommands

All standard Git subcommands are supported. The following have **structured response parsers**:

| Subcommand | Parsed Response Includes |
|------------|-------------------------|
| `status` | Modified, staged, untracked, deleted file lists + branch name |
| `log` | Commit history with hash, author, date, message |
| `diff` | Parsed diff hunks with file paths and line ranges |
| `branch` | Current branch, local/remote branches, tracking info |
| `remote` | Remote URLs (fetch/push), tracking branches |
| `stash` | Stash list with index, branch, message |
| `commit` | Commit hash, branch, summary |
| `init` | Repo path, git version, default branch |
| `clone` | Cloned path, branch, commit, git version |
| `merge` | Merge result status, commit hash |
| `push` / `pull` / `fetch` | Synced branches, commit counts |

Any subcommand not listed above still works — the response will include `stdout` and `stderr` directly.

## Response Format

### Basic (with parser)

```json
{
  "success": true,
  "status_code": 200,
  "message": "Git status completed",
  "data": {
    "operation": "status",
    "repo_path": "/home/user/project",
    "git_version": "git version 2.43.0",
    "branch": "main",
    "status": {
      "modified": ["src/main.py", "README.md"],
      "staged": ["config.json"],
      "untracked": ["new_feature.py"],
      "deleted": []
    }
  }
}
```

### Fallback (no parser)

```json
{
  "success": true,
  "status_code": 200,
  "message": "Git tag completed",
  "data": {
    "operation": "tag",
    "repo_path": "/home/user/project",
    "stdout": "v1.0.0\nv1.1.0\nv2.0.0"
  }
}
```

### Dry Run

```json
{
  "success": true,
  "status_code": 200,
  "message": "DRY RUN: would execute `git commit -m feat: add payment`",
  "data": {
    "operation": "commit",
    "repo_path": "/home/user/project",
    "dry_run": true,
    "git_version": "git version 2.43.0"
  }
}
```

### Error — Not a Git repository

```json
{
  "success": false,
  "status_code": 404,
  "message": "Not a git repository",
  "data": {
    "operation": "status",
    "repo_path": "/home/user/plain-folder"
  }
}
```

### Error — Merge conflict

```json
{
  "success": false,
  "status_code": 409,
  "message": "Merge conflict: Automatic merge failed...",
  "data": {
    "operation": "merge",
    "conflicts": ["src/main.py", "README.md"],
    "resolution_hint": "Resolve conflicts using 'git add' or 'git mergetool', then commit."
  }
}
```

## Common Examples

### Status
```json
{ "tool": "repo_git", "repo_path": "/project", "subcommand": "status" }
```

### Stage and Commit
```json
{
  "tool": "repo_git", "repo_path": "/project",
  "subcommand": "add", "args": ["src/main.py", "README.md"]
}
{
  "tool": "repo_git", "repo_path": "/project",
  "subcommand": "commit", "args": ["-m", "feat: add payment retry logic"]
}
```

### View Log (last 5 commits)
```json
{
  "tool": "repo_git", "repo_path": "/project",
  "subcommand": "log", "flags": {"--oneline": true, "-n": 5}
}
```

### Create and Switch Branch
```json
{
  "tool": "repo_git", "repo_path": "/project",
  "subcommand": "checkout", "args": ["-b", "feature/new-ui"]
}
```

### Push to Remote
```json
{
  "tool": "repo_git", "repo_path": "/project",
  "subcommand": "push", "args": ["origin", "main"]
}
```

## Integration with Other Tools

| Tool | Integration |
|------|-------------|
| `repo_init` | Calls `git clone` / `git init` during repo setup |
| `repo_audit` | Scans git history for secrets (separate tool) |
| `repo_staleness` | Checks if index is behind HEAD |
| `fs_manage` | `repo_git` replaces old `git=True` in filesystem ops |
| `fs_search` | `repo_git add` to stage files after search-and-replace |

## Error Cases

| Error | Status | Message |
|-------|--------|---------|
| Not a git repository | `404` | `"Not a git repository"` |
| Merge conflict | `409` | Conflict info with resolution hint |
| Pathspec not found | `404` | `"pathspec '...' did not match any files"` |
| Nothing to commit | `200` | `"Nothing to commit, working tree clean"` |
| Already up-to-date | `200` | `"Already up-to-date"` |
| Timeout | `408` | `"Git command timed out after 300s"` |
| CLI not found | `500` | `"Git CLI not found"` |
