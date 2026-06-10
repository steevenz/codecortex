# repo_sync — Sinkronisasi Index dengan Filesystem

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-25

## Overview

`repo_sync` incrementally synchronizes a repository's CodeCortex index with the current filesystem state. It detects added, modified, and deleted files, re-indexes changes for fresh symbols/edges, and removes orphaned database entries.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Path of the repository to synchronize |
| `mode` | string | ❌ | `"auto"` | Sync mode: `"auto"` (mtime/size diff), `"full"` (re-scan all), `"fast"` (check only) |
| `include_patterns` | array | ❌ | — | File patterns to include (default: from existing index) |
| `exclude_patterns` | array | ❌ | — | Directories/patterns to ignore |
| `reindex_updated` | boolean | ❌ | `true` | Re-run code analysis on modified files |
| `remove_deleted` | boolean | ❌ | `true` | Remove DB entries for deleted files |
| `dry_run` | boolean | ❌ | `false` | Simulate without making changes |

## 5-Phase Flow

```
PHASE 1: Get DB file list
  • Query files table for repo_id → {name: {id, size_bytes, mtime}}
  • Build lookup dict for O(1) comparison

PHASE 2: Scan filesystem
  • os.walk with exclude filtering (.git, __pycache__, node_modules, etc.)
  • Collect: {name: {path, size_bytes, mtime}}
  • Filter by TEXT_EXTS + special files (Dockerfile, .gitignore, Makefile)

PHASE 3: Diff
  • added = disk_names - db_names
  • deleted = db_names - disk_names
  • modified (auto mode) = disk & db with different size/mtime
  • modified (full mode) = all disk & db intersection
  • If dry_run → return change plan

PHASE 4: Process changes (in transaction)
  • Deleted files:
      DELETE edges referencing file's symbols
      DELETE symbols for file_id
      DELETE file record
  • Modified files (if reindex_updated):
      DELETE old symbols/edges for the file
      UPDATE file record (size, content, mtime)
      Re-index: parse file → insert symbols → insert edges
  • Added files (always indexed):
      INSERT file record
      Parse content → insert symbols

PHASE 5: Update metadata
  • UPDATE last_indexed_at = now
  • Re-count total_files, total_symbols, total_edges
  • Return change summary with duration
```

## Classification

| Extension | Classification |
|-----------|---------------|
| `.py`, `.js`, `.ts`, `.go`, `.rs`, `.java`, `.cpp`, `.c`, etc. | code |
| `.md`, `.html`, `.css`, `.rst`, `.txt` | doc |
| `.yml`, `.yaml`, `.json`, `.xml`, `.toml`, `.ini`, `.cfg`, `.env` | config |
| Others | other |

## Default Exclusions

```
.git, .svn, __pycache__, node_modules, venv, env, .venv, dist, build, .agents
```

## Symbol Indexing

Built-in lightweight parser for common languages:

| Language | Extensions | Symbols Detected |
|----------|------------|-----------------|
| Python | `.py` | `def function`, `class Class`, `variable =` |
| JavaScript/TypeScript | `.js/.ts/.jsx/.tsx` | `function name`, `class Name`, `const/let/var name =` |
| Go | `.go` | `func name`, `type Name struct` |

For full AST analysis, run `repo_analyze` after sync.

## Response

### Success — With changes

```json
{
  "success": true,
  "status_code": 200,
  "message": "Repository synchronized with filesystem",
  "data": {
    "repo_id": "f8a3d2e1-...",
    "repo_path": "/home/user/projects/myapp",
    "mode": "auto",
    "duration_seconds": 3.45,
    "changes": {
      "files_added": 2,
      "files_modified": 5,
      "files_deleted": 1,
      "symbols_added": 18,
      "symbols_removed": 3,
      "edges_added": 27,
      "edges_removed": 5
    },
    "updated_index": true
  }
}
```

### Already up to date

```json
{
  "success": true,
  "data": {
    "changes": {
      "files_added": 0,
      "files_modified": 0,
      "files_deleted": 0
    },
    "message": "Repository is already up to date"
  }
}
```

### Error

```json
{
  "success": false,
  "status_code": 404,
  "message": "Repository not found in database. Run repo_init first.",
  "data": { "repo_path": "/home/user/projects/myapp" }
}
```

## Integration

| Tool | Role |
|------|------|
| SQLite | Primary data store |
| `repo_init` | Initial indexing before sync |
| `repo_analyze` | Full AST analysis after sync (complementary) |
| `repo_list` | Discover repos needing sync |
