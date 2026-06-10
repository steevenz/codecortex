# fs_search Tool

**Tool:** `fs_search`  
**Category:** Filesystem Search  
**Domain:** Filesystem  
**Version:** 1.0.0  
**AI Coder Impact:** 10/10 ⭐

---

## Overview

The `fs_search` tool searches the filesystem for files and directories by name patterns and/or content. It supports glob patterns, filename regex, full-content regex search, search-and-replace with diff preview, and exclusion patterns.

> **Scope:** Pure filesystem scan — no VCS or index required. Works on any path, regardless of whether it is registered as a repository.

## Capabilities

### Search Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Glob Pattern** | Filename matching via glob (e.g., `*.py`) | Find files by extension or pattern |
| **Filename Regex** | Regex pattern matched against filenames | Advanced filename matching |
| **Content Regex** | Search within file contents | Find code patterns, TODOs, secrets |
| **Search-and-Replace** | Replace matched content with diff preview | Refactoring, bulk edits |

### Key Features

- **Context Snippets:** Returns surrounding lines for each match, useful for LLM context
- **Dry-Run Safety:** Search-and-replace defaults to dry-run to prevent accidental modifications
- **Binary Detection:** Skips binary files for content search
- **Document Extraction:** PDFs and Office documents extracted for content search if libraries available
- **Depth Limiting:** Control recursion depth for large directory trees
- **Exclusion Patterns:** Exclude specific paths (e.g., `node_modules/`, `*.log`)
- **Symlink Following:** Optional symlink traversal during directory walk
- **Max Results:** Capped at 5000 internally regardless of `max_results` value

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `root_path` | string | ✅ | CWD | Absolute path to search root |
| `repo_id` | string | ❌ | — | Repository UUID for relative path resolution |
| `file_pattern` | string | ❌ | `"*"` | Glob pattern for filenames (e.g. `"*.py"`) |
| `file_regex` | string | ❌ | — | Regex pattern matched against filenames |
| `content_regex` | string | ❌ | — | Regex to search within file contents |
| `content_regex_flags` | string | ❌ | `""` | Flags: `"i"` (case-insensitive), `"m"` (multiline), `"s"` (dotall) |
| `recursive` | boolean | ❌ | `true` | Recursively scan subdirectories |
| `max_depth` | integer | ❌ | unlimited | Maximum directory depth to scan |
| `include_hidden` | boolean | ❌ | `false` | Include hidden files/dirs starting with `.` |
| `follow_symlinks` | boolean | ❌ | `false` | Follow symbolic links during traversal |
| `max_results` | integer | ❌ | `100` | Maximum number of results to return |
| `include_content_snippet` | boolean | ❌ | `true` | Include matching lines in results |
| `exclude_patterns` | array | ❌ | — | Glob patterns to exclude (e.g. `["*.log", "node_modules/"]`) |
| `replace_text` | string | ❌ | — | Replace matched `content_regex` with this text (supports `\1` backreferences) |
| `dry_run` | boolean | ❌ | `true` | When `replace_text` is set: preview only (default). Set `false` to apply. |

## repo_id — Path Resolution

`repo_id` is an optional Repository UUID. When provided, `root_path` can be a **relative path** resolved against the registered repository root.

**Without repo_id** — `root_path` must be absolute:
```json
{
  "root_path": "/home/user/my-project/src",
  "file_pattern": "*.py"
}
```

**With repo_id** — `root_path` can be relative to the repo root:
```json
{
  "root_path": "src",
  "repo_id": "abc-123-def-456",
  "file_pattern": "*.py"
}
```

Use `repo list` or `repo inspect PATH` to find your repository UUID.

## Output

### Result Structure

```json
{
  "success": true,
  "status_code": 200,
  "message": "fs_search completed",
  "data": {
    "root_path": "/home/user/project",
    "total": 12,
    "has_more": false,
    "files": [
      {
        "path": "/home/user/project/src/auth/service.py",
        "name": "service.py",
        "size_bytes": 4096,
        "modified_at": "2026-05-23T12:00:00Z",
        "matches": [
          {
            "line_number": 15,
            "line": "class AuthService:",
            "context_before": ["", "# Authentication logic"],
            "context_after": ["    def __init__(self):"]
          }
        ]
      }
    ]
  },
  "pagination": {
    "total": 12,
    "has_more": false,
    "limit": 100
  }
}
```

### Replace-mode response (dry_run=true)

```json
{
  "success": true,
  "status_code": 200,
  "data": {
    "root_path": "/home/user/project",
    "total": 3,
    "dry_run": true,
    "files": [
      {
        "path": "/home/user/project/src/main.py",
        "matches": 2,
        "diff": "@@ -10,7 +10,7 @@\n-import numpy\n+import numpy as np"
      }
    ]
  }
}
```

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| FS_003 | high | Root path not found |
| FS_003 | high | Invalid regex pattern |
| FS_003 | high | root_path must be a directory |
| FS_000 | high | Path traversal not allowed |

## Examples

### 1. Search by file glob pattern
```json
{
  "root_path": "/home/user/project",
  "file_pattern": "*.py"
}
```

### 2. Search by filename regex
```json
{
  "root_path": "/home/user/project",
  "file_regex": "^test_.*\\.py$"
}
```

### 3. Search by content (case-insensitive)
```json
{
  "root_path": "/home/user/project",
  "content_regex": "TODO|FIXME",
  "content_regex_flags": "i"
}
```

### 4. Combined: Python files containing a class definition
```json
{
  "root_path": "/home/user/project",
  "file_pattern": "*.py",
  "content_regex": "^class\\s+\\w+",
  "content_regex_flags": "m",
  "include_content_snippet": true
}
```

### 5. Deep search with depth limit and exclusions
```json
{
  "root_path": "/home/user/project",
  "file_pattern": "*.ts",
  "max_depth": 5,
  "exclude_patterns": ["node_modules/", "dist/", "*.d.ts"],
  "max_results": 50
}
```

### 6. Include hidden files
```json
{
  "root_path": "/home/user/project",
  "file_pattern": ".*",
  "include_hidden": true
}
```

### 7. Search-and-replace (dry run preview)
```json
{
  "root_path": "/home/user/project",
  "file_pattern": "*.py",
  "content_regex": "import numpy",
  "replace_text": "import numpy as np",
  "dry_run": true
}
```

### 8. Search-and-replace (apply changes)
```json
{
  "root_path": "/home/user/project",
  "file_pattern": "*.py",
  "content_regex": "import numpy",
  "replace_text": "import numpy as np",
  "dry_run": false
}
```

### 9. With repo_id for relative path resolution
```json
{
  "root_path": "src/modules",
  "repo_id": "abc-123-def-456",
  "file_pattern": "*.py",
  "content_regex": "class.*Service"
}
```

## Design Notes

- **Binary detection**: Files detected as binary are skipped for content search
- **Text extraction**: PDFs and Office documents (`.docx`, `.xlsx`) are extracted for content search if libraries are available (`pypdf2`, `python-docx`, `openpyxl`)
- **Context snippets**: `include_content_snippet: true` (default) returns surrounding lines for each match, useful for LLM context
- **Dry run default**: `replace_text` operations default to `dry_run: true` to prevent accidental modifications. Explicitly set `dry_run: false` to apply
- **Max results**: Capped at 5000 internally regardless of `max_results` value

## AI Coder Usage Tips

```json
// Find all files defining a Python class named "Service"
{
  "root_path": "src",
  "repo_id": "your-repo-id",
  "file_pattern": "*.py",
  "content_regex": "^class\\w*Service\\b",
  "content_regex_flags": "m"
}

// Find configuration files anywhere in the project
{
  "root_path": "/project",
  "file_regex": "^(config|settings)\\.(py|json|yaml|toml)$",
  "recursive": true
}

// Find TODO comments across all source files, exclude tests
{
  "root_path": "/project/src",
  "content_regex": "#\\s*TODO",
  "exclude_patterns": ["tests/", "*_test.py"]
}
```

## See Also

- [fs_manage](../fs_manage/concept.md) — Unified filesystem management
- [File Watcher](../file-watcher/concept.md) — Auto-detect file changes
