# fs_df Tool

**Tool:** `fs_df`  
**Category:** Disk Usage Analysis  
**Domain:** Filesystem  
**Version:** 1.0.0  
**AI Coder Impact:** 10/10 ⭐

---

## Overview

The `fs_df` tool calculates disk usage with optional Git/SVN integration. It reports file and directory sizes, identifies largest files, and can categorize usage by VCS status (tracked/untracked/ignored) or file extension.

Despite the name `df` (disk free), this tool behaves like `du` (disk usage) — it measures space consumed, not space available.

## Capabilities

### Analysis Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Basic** | Recursive directory tree with size breakdown | Understand space distribution |
| **VCS Integration** | Categorize by Git/SVN status (tracked/untracked/ignored) | Identify untracked bloat |
| **Extension Aggregation** | Group by file extension | Identify large file types |
| **Single File** | Analyze individual file size | Quick file size check |

### Key Features

- **VCS Breakdown:** Git/SVN integration for tracked/untracked/ignored categorization
- **Extension Aggregation:** Group usage by file type with percentage breakdown
- **Largest Files:** Identifies top space consumers
- **Unit Conversion:** Auto-detection or explicit unit selection (bytes, kb, mb, gb)
- **Depth Limiting:** Control recursion depth for large directory trees
- **Exclusion Patterns:** Exclude specific paths (e.g., `node_modules/`, `*.log`)
- **Suggestions:** Provides actionable recommendations for untracked file cleanup

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target` | string | ✅ | — | Absolute path to directory or file to analyze |
| `recursive` | boolean | ❌ | `true` | Calculate recursively |
| `depth` | integer | ❌ | unlimited | Maximum subdirectory depth |
| `unit` | string | ❌ | `"auto"` | `"bytes"`, `"kb"`, `"mb"`, `"gb"`, or `"auto"` |
| `include_hidden` | boolean | ❌ | `false` | Include files/dirs starting with `.` |
| `exclude_patterns` | array | ❌ | `[]` | Glob patterns to exclude (e.g. `["*.log", "temp/*"]`) |
| `vcs_integration` | string | ❌ | `"none"` | `"none"`, `"git"`, or `"svn"` |
| `aggregate_by` | string | ❌ | `"file"` | `"file"`, `"extension"`, or `"vcs_status"` |
| `max_items` | integer | ❌ | `100` | Max items to report (max `5000`) |

## Output

### Result Structure

```json
{
  "success": true,
  "status_code": 200,
  "message": "Disk usage calculated",
  "data": {
    "target": "/home/user/project",
    "unit": "mb",
    "total_size_mb": 125.45,
    "total_items": 342,
    "breakdown": [
      { "path": "src/", "type": "directory", "size_mb": 88.23, "items": 210 },
      { "path": "src/main.go", "type": "file", "size_mb": 0.03, "items": 1 },
      { "path": "assets/background.png", "type": "file", "size_mb": 15.2, "items": 1 }
    ],
    "largest_files": [
      { "path": "assets/background.png", "size_mb": 15.2 }
    ]
  }
}
```

### VCS Integration Response

```json
{
  "success": true,
  "message": "Disk usage with Git analysis",
  "data": {
    "target": "/home/user/git-project",
    "vcs": "git",
    "branch": "main",
    "commit": "a1b2c3d",
    "unit": "mb",
    "total_size_mb": 256.78,
    "total_items": 365,
    "vcs_breakdown": {
      "tracked": { "size_mb": 180.45, "files": 342 },
      "untracked": { "size_mb": 45.12, "files": 8 },
      "ignored": { "size_mb": 31.21, "files": 15 }
    },
    "details": [
      { "status": "untracked", "path": "temp/large_file.bin", "size_mb": 40.0 },
      { "status": "ignored", "path": "node_modules/", "size_mb": 30.0 },
      { "status": "tracked", "path": "src/", "size_mb": 120.3 }
    ],
    "suggestion": "Untracked files consume 45.12 mb. Consider adding to .gitignore or committing."
  }
}
```

### Extension Aggregation Response

```json
{
  "success": true,
  "data": {
    "aggregate_by": "extension",
    "breakdown": [
      { "extension": ".go", "size_mb": 45.3, "files": 120, "percentage": 35.0 },
      { "extension": ".png", "size_mb": 60.1, "files": 45, "percentage": 46.0 },
      { "extension": ".md", "size_mb": 2.1, "files": 8, "percentage": 2.0 },
      { "extension": "(no extension)", "size_mb": 22.0, "files": 10, "percentage": 17.0 }
    ]
  }
}
```

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| FS_030 | high | Target path does not exist |
| FS_031 | medium | Not a git repository (returns 200 with error in data) |
| FS_032 | medium | Not an SVN working copy (returns 200 with error in data) |

## Examples

### 1. Basic directory usage
```json
{
  "target": "/home/user/project",
  "unit": "mb",
  "depth": 2
}
```

### 2. Git integration — VCS breakdown
```json
{
  "target": "/home/user/git-project",
  "vcs_integration": "git",
  "aggregate_by": "vcs_status",
  "unit": "mb"
}
```

### 3. Extension aggregation
```json
{
  "target": "/home/user/project",
  "aggregate_by": "extension",
  "unit": "mb"
}
```

### 4. Single file analysis
```json
{
  "target": "/home/user/file.txt",
  "unit": "bytes"
}
```

## Design Notes

- **Without VCS (`vcs_integration="none"`):** Uses `pathlib.Path.iterdir()` + recursive walk
- **Git integration (`vcs_integration="git"`):** Uses `git ls-files`, `git ls-files --others --exclude-standard`, `git ls-files --others --ignored --exclude-standard`
- **SVN integration (`vcs_integration="svn"`):** Parses `svn status --no-ignore` output for versioned, unversioned, and ignored files
- **VCS breakdown computation:** Filters all paths by `include_hidden` and `exclude_patterns`, computes per-category size and file count
- **Unit conversion:** Auto-detection (bytes ↔ kb ↔ mb ↔ gb) via `_format_size()`

## See Also

- [fs_manage](../fs_manage/concept.md) — Unified filesystem management
- [fs_watch](../fs_watch/concept.md) — File change monitoring
