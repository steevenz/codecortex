# CodeIndex: MCP Tool Reference

> **Source:** `src/modules/codeindex/api/tools.py`
> **Registered in:** `src/main.py` (via `register_tools(mcp, orchestrator_factory)`)
> **Version:** 2.0.0

## Single Tool: `code_index`

CodeIndex exposes exactly **one MCP tool** with **6 actions**, following the same pattern as `code_tester` (codetester domain).

### `code_index(action="status")`

Check indexing status of a repository. Returns symbol/file/edge counts, language breakdown, last indexed timestamp, and active performance configuration.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be `"status"` |
| `repo_id` | string | ✅ | — | Repository UUID |

**Returns:**
```json
{
  "success": true,
  "message": "Status: 142 symbols, 23 files, 87 edges",
  "data": {
    "repo_id": "abc-123",
    "symbol_count": 142,
    "file_count": 23,
    "edge_count": 87,
    "last_indexed_at": "2026-05-25T10:30:00",
    "root_path": "/home/user/project",
    "languages": {
      "python": 98,
      "javascript": 32,
      "typescript": 12
    },
    "config": {
      "max_file_size_mb": 5,
      "parse_timeout_seconds": 15,
      "max_concurrent_indexing": 10
    }
  },
  "meta": { "request_id": "req_...", "timestamp": "..." }
}
```

**Error Codes:**
| Code | Severity | Message |
|------|----------|---------|
| CI_002 | medium | repo_id is required for action='status'. Use repo_inspect to find your repo_id. |
| CI_500 | critical | Internal error (logged with context) |

---

### `code_index(action="index")`

Full re-index of all code files in a repository. Deletes existing symbols/edges and re-parses everything.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be `"index"` |
| `repo_id` | string | ❌ | — | Repository UUID (mutually exclusive with path) |
| `path` | string | ❌ | — | Repository root path (auto-sync if no repo_id; validated for traversal/existence) |

**Returns:**
```json
{
  "success": true,
  "message": "Indexing completed: 142 symbols, 23 files in 5.3s",
  "data": {
    "repo_id": "abc-123",
    "symbol_count": 142,
    "file_count": 23,
    "edge_count": 87,
    "languages": {"python": 98, "javascript": 32, "typescript": 12},
    "duration_s": 5.3,
    "metrics": {
      "symbols_per_sec": 26.8,
      "files_per_sec": 4.3
    }
  }
}
```

**Error Codes:**
| Code | Severity | Message |
|------|----------|---------|
| CI_003 | medium | Provide repo_id or path. Path validation failed: {reason} |
| CI_500 | critical | Internal error (logged with context) |

**Path Validation:**
- Path traversal (`..`) is blocked
- Non-existent paths are rejected
- Non-directory paths are rejected

**Pipeline when called:**
1. Reset symbols/edges/insights for repo
2. Pre-scan Python imports
3. Parse all code files (WorkerPool if >=15 files or >=512KB, else sequential async)
4. Framework enrichment via `RepositoryFrameworkDetector.enrich_file()`
5. Write symbols to SQLite via `_write_parsed_to_sqlite()` (converter → raw symbols → persist)
6. Scope resolution (multi-pass cross-file reference resolution via `ScopeExtractor` + `ReferenceResolver`)
7. SQLite edge resolution (`_resolve_edges_sqlite`) — builds 4 edge types:
   - `CALLS` — from function_calls metadata
   - `INHERITS` — from symbol parent_id chain (method → class)
   - `CLASS_INHERITS` — from class signature bases (class → base)
   - `IMPORTS` — from __file__ symbol metadata JSON
8. Graph backend sync (if `codegraph_service` injected)

---

### `code_index(action="incremental")`

Index only files changed since last index (VCS-aware: Git diff for Git, svn status for SVN). Includes transparent fallback reporting.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be `"incremental"` |
| `repo_id` | string | ✅ | — | Repository UUID |

**Returns:**
```json
{
  "success": true,
  "message": "Incremental (git): 3 file(s) re-indexed in 1.2s",
  "data": {
    "repo_id": "abc-123",
    "changed_files": ["src/service.py", "src/models.py", "src/api.py"],
    "files_changed": 3,
    "vcs_type": "git",
    "fallback_to_full_sync": false,
    "fallback_reason": null,
    "duration_s": 1.2
  }
}
```

**Fallback Example (no VCS detected):**
```json
{
  "success": true,
  "message": "Incremental (fallback full sync, no VCS detected): 0 file(s) in 0.1s",
  "data": {
    "repo_id": "abc-123",
    "changed_files": [],
    "files_changed": 0,
    "vcs_type": "none",
    "fallback_to_full_sync": true,
    "fallback_reason": "no VCS detected (.git / .svn not found)",
    "duration_s": 0.1
  }
}
```

**Error Codes:**
| Code | Severity | Message |
|------|----------|---------|
| CI_004 | medium | repo_id is required for action='incremental'. Use repo_inspect to find your repo_id. |
| CI_500 | critical | Internal error (logged with context) |

**VCS Support:**
- **Git:** `git diff --name-only HEAD` for changed files
- **SVN:** `svn status` (modified + added) → fallback to `svn diff --summarize -r LAST_REV:HEAD`
- **None:** Fallback to full sync with transparent reporting

---

### `code_index(action="files")`

Index specific files by relative path. Useful after external edits.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be `"files"` |
| `repo_id` | string | ✅ | — | Repository UUID |
| `files` | list | ✅ | — | Non-empty list of relative file paths |

**Returns:**
```json
{
  "success": true,
  "message": "Indexed 2/3 file(s) in 0.8s",
  "data": {
    "files_requested": 3,
    "files_indexed": 2,
    "errors": [{"path": "nonexistent.py", "error": "file not found"}],
    "duration_s": 0.8
  }
}
```

**Error Codes:**
| Code | Severity | Message |
|------|----------|---------|
| CI_005 | medium | Both repo_id and files[] are required for action='files'. Provide relative file paths. |
| CI_006 | medium | files[] must be a non-empty list of strings. |
| CI_500 | critical | Internal error (logged with context) |

---

### `code_index(action="pre_scan")`

Pre-scan Python imports for cross-file call resolution. Builds an `imports_map` mapping symbol names to their defining files. Used internally by `action="index"` before graph sync.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be `"pre_scan"` |
| `repo_id` | string | ❌ | — | Repository UUID (mutually exclusive with path) |
| `path` | string | ❌ | — | Repository root path (auto-sync if no repo_id; validated for traversal/existence) |

**Returns:**
```json
{
  "success": true,
  "message": "Pre-scan completed: 15 modules, 142 symbols in 0.3s",
  "data": {
    "repo_id": "abc-123",
    "modules": 15,
    "symbols": 142,
    "duration_s": 0.3
  }
}
```

**Error Codes:**
| Code | Severity | Message |
|------|----------|---------|
| CI_003 | medium | Provide repo_id or path. Path validation failed: {reason} |
| CI_500 | critical | Internal error (logged with context) |

---

### `code_index(action="export")`

Export symbol table as structured JSON for external tooling, auditing, and debugging.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be `"export"` |
| `repo_id` | string | ✅ | — | Repository UUID |
| `limit` | int | ❌ | 500 | Max symbols to export (max 5000) |

**Returns:**
```json
{
  "success": true,
  "message": "Exported 500 symbols from repo abc-123",
  "data": {
    "repo_id": "abc-123",
    "symbol_count": 500,
    "file_count": 45,
    "edge_count": 1000,
    "truncated": false,
    "limit_applied": 500,
    "symbols": [...],
    "files": [...],
    "edges": [...]
  }
}
```

**Error Codes:**
| Code | Severity | Message |
|------|----------|---------|
| CI_007 | medium | repo_id is required for action='export'. Use repo_inspect to find your repo_id. |
| CI_500 | critical | Internal error (logged with context) |

---

## Security

- **Path Validation:** All `path` parameters are validated for traversal attacks (`..`), existence, and directory type
- **Input Validation:** `files` parameter must be a non-empty list of strings
- **Error Messages:** Include actionable guidance (e.g., "Use repo_inspect to find your repo_id")
- **SSRF Guards:** Path validation prevents remote file access
- **Traversal Prevention:** `..` segments blocked in all path parameters

---

## Tool Boundary

| Operation | Tool to Use | Domain |
|-----------|------------|--------|
| Index management | `code_index` | **CodeIndex** |
| Symbol search (name/regex/semantic) | `code_search` | CodeAnalysis |
| Graph relationship query | `graph_query` | CodeGraph |
| Graph build (relationships) | `graph_build` | CodeGraph |
| Full pipeline (sync->index->graph->VCS) | `repo_analyze` | CodeRepository |
| File tree / metadata | `fs_search` / `fs_tree` | Filesystem |

---

## Tool Count

| Domain | Tool Count | Tools |
|--------|-----------|-------|
| CodeIndex | 1 | `code_index` (6 actions) |
| Total (all domains) | ~31 | — |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CODECORTEX_MAX_FILE_SIZE_MB` | 5 | Max file size (MB) before skipping parse |
| `CODECORTEX_PARSE_TIMEOUT_SECONDS` | 15 | Per-file parse timeout in seconds |
| `CODECORTEX_MAX_CONCURRENT_INDEXING` | 10 | Max concurrent async indexing tasks | |
