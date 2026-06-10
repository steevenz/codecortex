# repo_svn — Arbitrary Subversion (SVN) Operations

> **Source:** `src/domain/filesystem/infrastructure/fs_svn.py` — `FsSvnHelper`
> **Since:** 2026-05-24

## Overview

`repo_svn` executes **arbitrary SVN subcommands** with structured parameters and parsed responses. It wraps the SVN CLI and provides parsed responses for common operations. SVN support is optional — returns an error if the `svn` CLI is not installed.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `target` | string | ✅ | — | URL (for checkout/export) or local working copy path |
| `subcommand` | string | ✅ | — | SVN subcommand (e.g. `"status"`, `"commit"`, `"update"`) |
| `args` | array | ❌ | `[]` | Positional arguments |
| `flags` | object | ❌ | `{}` | Flags as dict (e.g. `{"--verbose": true, "--limit": 10}`) |
| `dry_run` | boolean | ❌ | `false` | Simulate without executing |
| `timeout_seconds` | integer | ❌ | `300` | Timeout for remote operations (checkout, update, commit) |

## Supported Subcommands

All standard SVN subcommands are supported. The following have **structured response parsers**:

| Subcommand | Parsed Response Includes |
|------------|-------------------------|
| `checkout` / `co` | Checked out revision, URL, path |
| `update` / `up` | Updated revision, added/modified/deleted file lists |
| `commit` / `ci` | Committed revision, author, timestamp, file list |
| `add` | Added files, any skipped/newly tracked |
| `status` / `stat` | Modified, added, deleted, unversioned, conflicted, ignored files |
| `log` | Revision history with author, date, message, changed paths |
| `diff` / `di` | Parsed diff output |
| `info` | URL, repository root, revision, last changed rev/author, schedule |
| `revert` | Reverted files list |
| `cleanup` | Cleanup status |
| `lock` / `unlock` | Lock/unlock status per path |
| `propset` / `pset` | Property set status |
| `propget` / `pget` | Property value |
| `proplist` / `plist` | List of properties |
| `resolve` | Resolved conflict status |
| `mkdir` | Directory creation status |
| `delete` / `del` | Deletion status |
| `copy` / `cp` | Copy status |
| `move` / `mv` / `rename` / `ren` | Move/rename status |
| `list` / `ls` | Directory listing |
| `switch` / `sw` | Switch status |
| `merge` | Merge result |
| `import` / `export` | Import/export status |

## Response Format

### Status (parsed)

```json
{
  "success": true,
  "status_code": 200,
  "message": "SVN status completed",
  "data": {
    "operation": "status",
    "target": "/home/user/svn-project",
    "files": [
      {"status": "M", "file": "trunk/src/main.py", "wc_status": "modified"},
      {"status": "A", "file": "trunk/src/utils.py", "wc_status": "added"},
      {"status": "?", "file": "trunk/temp.txt", "wc_status": "untracked"},
      {"status": "I", "file": "trunk/node_modules", "wc_status": "ignored"}
    ]
  }
}
```

### Log (parsed)

```json
{
  "success": true,
  "status_code": 200,
  "message": "SVN log completed",
  "data": {
    "operation": "log",
    "target": "/home/user/svn-project",
    "limit": 10,
    "log_entries": [
      {
        "revision": 1234,
        "author": "steeven",
        "date": "2026-05-24T10:00:00Z",
        "message": "feat: add payment retry logic"
      }
    ]
  }
}
```

### Info (parsed)

```json
{
  "success": true,
  "status_code": 200,
  "message": "SVN info completed",
  "data": {
    "operation": "info",
    "target": "/home/user/svn-project",
    "url": "https://svn.example.com/repo/trunk",
    "repository_root": "https://svn.example.com/repo",
    "revision": 1234,
    "last_changed_rev": 1230,
    "last_changed_author": "steeven",
    "last_changed_date": "2026-05-23T15:00:00Z",
    "schedule": "normal"
  }
}
```

### Dry Run

```json
{
  "success": true,
  "status_code": 200,
  "message": "DRY RUN: would execute `svn commit -m fix: resolve conflict`",
  "data": {
    "operation": "commit",
    "target": "/home/user/svn-project",
    "dry_run": true
  }
}
```

### Error — Not a working copy

```json
{
  "success": false,
  "status_code": 404,
  "message": "Not a Subversion working copy",
  "data": {
    "operation": "update",
    "target": "/home/user/plain-folder"
  }
}
```

### Error — Authentication failed

```json
{
  "success": false,
  "status_code": 401,
  "message": "Authentication failed: ...",
  "data": {
    "svn_error_code": "E170001",
    "suggestion": "Check username/password or use --username with --password"
  }
}
```

## Common Examples

### Status
```json
{ "tool": "repo_svn", "target": "/project", "subcommand": "status" }
```

### Checkout Remote Repository
```json
{
  "tool": "repo_svn", "target": "/project",
  "subcommand": "checkout",
  "args": ["https://svn.example.com/repo/trunk", "/local/project"]
}
```

### Stage and Commit
```json
{
  "tool": "repo_svn", "target": "/project",
  "subcommand": "add", "args": ["src/main.py"]
}
{
  "tool": "repo_svn", "target": "/project",
  "subcommand": "commit", "args": ["-m", "fix: resolve merge conflict"]
}
```

### View Log
```json
{
  "tool": "repo_svn", "target": "/project",
  "subcommand": "log", "flags": {"--limit": 10, "--verbose": true}
}
```

### Update Working Copy
```json
{
  "tool": "repo_svn", "target": "/project",
  "subcommand": "update"
}
```

### Resolve Conflict
```json
{
  "tool": "repo_svn", "target": "/project",
  "subcommand": "resolve", "args": ["src/main.py"],
  "flags": {"--accept": "theirs-full"}
}
```

## Integration

| Tool | Integration |
|------|-------------|
| `repo_init` | Calls `svn checkout` / `svn mkdir` during repo setup |
| `repo_audit` | Scans SVN log for secrets (separate tool) |
| `repo_staleness` | Checks if index is behind latest SVN revision |

## Error Cases

| Error | Status | Code | Message |
|-------|--------|------|---------|
| Not a working copy | `404` | — | `"Not a Subversion working copy"` |
| Authentication failed | `401` | `E170001` | Auth error with suggestion |
| Conflict | `409` | `E155010` | Conflict with resolution hint |
| Working copy locked | `423` | `E200033` | Locked — run `svn cleanup` |
| Path not found | `404` | — | `"Path does not exist"` |
| Not under version control | `404` | — | Path not tracked |
| Timeout | `408` | — | `"SVN command timed out after 300s"` |
| CLI not found | `500` | — | `"SVN CLI not available"` |
