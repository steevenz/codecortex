# fs_watch Tool

**Tool:** `fs_watch`  
**Category:** File Change Monitoring  
**Domain:** Filesystem  
**Version:** 1.0.0  
**AI Coder Impact:** 10/10 ⭐

---

## Overview

The `fs_watch` tool monitors files and directories for changes using **polling-based snapshot comparison**. Because MCP is synchronous and does not support streaming, changes are detected by comparing against a previous state defined by a timestamp, Git revision, or SVN revision.

## Capabilities

### Scan Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| **current_state** | Lists all files with current metadata and VCS status | Baseline snapshot |
| **timestamp** | Compares file `mtime` against an ISO 8601 timestamp | Time-based change detection |
| **git** | Uses `git diff --name-status` and `git status --porcelain` | Git-aware change detection |
| **svn** | Uses `svn diff --summarize` and `svn status` | SVN-aware change detection |

### Key Features

- **VCS Integration:** Git and SVN revision-based change detection
- **Event Filtering:** Filter by create, modify, delete, rename, attribute events
- **Detailed Format:** Includes content previews and diff hunks for modified files
- **Merge Deduplication:** Combines committed (diff) and working tree (status) changes without duplicates
- **Ignored Filtering:** Exclude VCS-ignored files from results
- **Scan Timeout:** Configurable timeout to prevent long-running scans

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target` | string | ✅ | — | Absolute path to directory or file to watch |
| `since` | string | ❌ | — | ISO 8601 timestamp, `"git:<revision>"`, or `"svn:<revision>"`. If omitted, reports current file state |
| `recursive` | boolean | ❌ | `true` | Watch subdirectories recursively |
| `include_ignored` | boolean | ❌ | `false` | Include files ignored by Git/SVN in results |
| `events` | array | ❌ | all | Filter: `["create","modify","delete","rename","attribute"]` |
| `format` | string | ❌ | `"simple"` | `"simple"` or `"detailed"` (includes content previews/diffs) |
| `max_changes` | integer | ❌ | `500` | Max changes to report (max `5000`) |
| `timeout_seconds` | integer | ❌ | `60` | Scan timeout |

## Output

### Result Structure

```json
{
  "success": true,
  "status_code": 200,
  "message": "Found 12 change(s) since 2026-05-23T12:00:00Z",
  "data": {
    "target": "/home/user/project",
    "since": "2026-05-23T12:00:00Z",
    "scan_method": "timestamp",
    "current_branch": "main",
    "summary": { "created": 3, "modified": 8, "deleted": 1 },
    "changes": [
      {
        "path": "src/main.go",
        "event": "modified",
        "timestamp": "2026-05-24T10:30:00Z",
        "size_bytes": 12345,
        "git_status": "modified",
        "svn_status": "M"
      }
    ]
  }
}
```

### Detailed Format

When `format="detailed"`, modified entries include a `content_preview` field (first 500 chars) and a `diff` field with parsed hunks:

```json
{
  "path": "src/utils.py",
  "event": "modified",
  "git_status": "modified",
  "diff": [
    {
      "range": "@@ -12,7 +12,8 @@",
      "content": "@@ -12,7 +12,8 @@ def parse(data):\n-    return None\n+    if not data:\n+        return {}\n+    return json.loads(data)\n"
    }
  ]
}
```

### Git Mode Response

When `since="git:a1b2c3d"`, the response includes VCS metadata:

```json
{
  "data": {
    "scan_method": "git",
    "current_branch": "main",
    "changes": [
      {
        "path": "src/utils.py",
        "event": "modified",
        "git_status": "modified"
      },
      {
        "path": "tests/test_utils.py",
        "event": "created",
        "git_status": "added",
        "size_bytes": 2048
      }
    ]
  }
}
```

### SVN Mode Response

When `since="svn:1234"`, the response includes SVN metadata:

```json
{
  "data": {
    "scan_method": "svn",
    "current_revision": 1236,
    "changes": [
      {
        "path": "trunk/config.xml",
        "event": "modified",
        "svn_status": "M",
        "svn_prop_changes": false,
        "timestamp": "2026-05-24T10:00:00Z"
      }
    ]
  }
}
```

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| FS_020 | high | Target path does not exist |
| FS_021 | high | Invalid `since` format |
| FS_022 | high | Scan timeout (partial results in `data.partial_changes`) |

## Examples

### 1. Current state snapshot
```json
{
  "target": "/home/user/project"
}
```

### 2. Timestamp-based change detection
```json
{
  "target": "/home/user/project",
  "since": "2026-05-23T12:00:00Z"
}
```

### 3. Git revision comparison
```json
{
  "target": "/home/user/project",
  "since": "git:a1b2c3d"
}
```

### 4. SVN revision comparison
```json
{
  "target": "/home/user/project",
  "since": "svn:1234"
}
```

### 5. Detailed format with diffs
```json
{
  "target": "/home/user/project",
  "since": "git:HEAD~1",
  "format": "detailed"
}
```

### 6. Event filtering
```json
{
  "target": "/home/user/project",
  "since": "2026-05-23T12:00:00Z",
  "events": ["create", "modify"]
}
```

## Design Notes

- **Polling-based:** MCP is synchronous — no streaming or push. Timestamp/git/svn comparison avoids real-time FS monitoring
- **Git/SVN deduplication:** Both `git diff` (committed) and `git status` (working tree) results are merged with deduplication by relative path
- **Event normalization:** Filter events use base form (`"modify"`), response events use past tense (`"modified"`). Mapping: `modify` ↔ `modified`, `create` ↔ `created`, `delete` ↔ `deleted`
- **Ignored filtering:** `include_ignored=False` (default) filters out git `!!` entries and svn `I` entries
- **Diff hunks:** For `format="detailed"`, hunks are parsed from `git diff`/`svn diff` output lines starting with `@@`

## Internal Implementation

### Background Watchdog (Internal Re-Indexing)

CodeCortex also provides an internal watchdog-based file watching mechanism used for automatic re-indexing. This is separate from the `fs_watch` MCP tool and operates as a background service.

**Watchdog Flow:**
```
Filesystem event (modify/create/delete)
    │
    ▼
  Watchdog observer ──> Event queue
    │
    ▼
  Debounce (2s) ──> Deduplicate rapid changes
    │
    ▼
  Trigger incremental sync or file update
```

**Events Handled:**
| Event | Action |
|-------|--------|
| `on_modified` | Re-index changed file |
| `on_created` | Index new file |
| `on_deleted` | Remove from index |
| `on_moved` | Update file path in index |

This internal watchdog is not exposed as an MCP tool and is used only by the server for automatic index synchronization.

## See Also

- [fs_manage](../fs_manage/concept.md) — Unified filesystem management
