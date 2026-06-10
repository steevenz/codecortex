# CodeIndex Documentation Matrix

**Date:** 2026-05-29
**Domain:** CodeIndex
**Scope:** MCP Tools (1 tool with 5 actions)
**Source:** Documentation files in `docs/features/codeindex/`

---

## Tool: `code_index`

### Action: `status`

**Documentation Source:** `tools.md` lines 10-39

**Documented Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| repo_id | str | Yes | - | Repository UUID |

**Documented Operations:**
- Check indexing status of a repository

**Documented Response Format:**
```json
{
  "success": true,
  "message": "Status: 142 symbols, 23 files",
  "data": {
    "repo_id": "abc-123",
    "symbol_count": 142,
    "file_count": 23,
    "last_indexed_at": "2026-05-25T10:30:00"
  },
  "meta": { "request_id": "req_...", "timestamp": "..." }
}
```

**Documented Errors:**
| Error Code | Description |
|------------|-------------|
| CI_002 | repo_id required |
| CI_500 | internal failure |

**Documented Examples:**
- Example JSON response provided in tools.md

---

### Action: `index`

**Documentation Source:** `tools.md` lines 43-73

**Documented Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| repo_id | str | Conditional | - | Repository UUID (mutually exclusive with path) |
| path | str | Conditional | - | Repository root path (auto-sync if no repo_id) |

**Documented Operations:**
- Full re-index of all code files in a repository
- Deletes existing symbols/edges and re-parses everything

**Documented Response Format:**
```json
{
  "success": true,
  "message": "Indexing completed for {repo_id}",
  "data": {
    "repo_id": "uuid",
    "duration_s": 12.5
  }
}
```

**Documented Pipeline:**
1. Reset symbols/edges/insights for repo
2. Pre-scan Python imports
3. Parse all code files (WorkerPool if >=15 files or >=512KB, else sequential async)
4. Framework enrichment via `RepositoryFrameworkDetector.enrich_file()`
5. Write symbols to SQLite via `_write_parsed_to_sqlite()`
6. Scope resolution (multi-pass cross-file reference resolution)
7. SQLite edge resolution (`_resolve_edges_sqlite`) — builds 4 edge types
8. Graph backend sync (if `codegraph_service` injected)

**Documented Errors:**
| Error Code | Description |
|------------|-------------|
| CI_003 | provide repo_id or path |
| CI_500 | internal failure |

---

### Action: `incremental`

**Documentation Source:** `tools.md` lines 76-92

**Documented Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| repo_id | str | Yes | - | Repository UUID |

**Documented Operations:**
- Index only files changed since last index (git diff-based)
- Includes crash guard for `changed=None`

**Documented Response Format:**
```json
{
  "success": true,
  "message": "Incremental: {len(changed)} files processed",
  "data": {
    "repo_id": "uuid",
    "changed_files": ["file1.py", "file2.py"],
    "duration_s": 3.2
  }
}
```

**Documented Errors:**
| Error Code | Description |
|------------|-------------|
| CI_004 | repo_id required |
| CI_500 | internal failure |

**Documented Special Behavior:**
- If `changed` is None (e.g., no git history), the tool returns early without error

---

### Action: `files`

**Documentation Source:** `tools.md` lines 96-111

**Documented Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| repo_id | str | Yes | - | Repository UUID |
| files | str[] | Yes | - | List of relative file paths |

**Documented Operations:**
- Index specific files by relative path
- Useful after external edits

**Documented Response Format:**
```json
{
  "success": true,
  "message": "Indexed {len(files)} file(s)",
  "data": {
    "files_requested": 3,
    "files_indexed": 3,
    "errors": [],
    "duration_s": 1.5
  }
}
```

**Documented Errors:**
| Error Code | Description |
|------------|-------------|
| CI_005 | repo_id and files required |
| CI_500 | internal failure |

---

### Action: `pre_scan`

**Documentation Source:** `tools.md` lines 115-130

**Documented Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| repo_id | str | Conditional | - | Repository UUID (mutually exclusive with path) |
| path | str | Conditional | - | Repository root path (auto-sync if no repo_id) |

**Documented Operations:**
- Pre-scan Python imports for cross-file call resolution
- Builds an `imports_map` mapping symbol names to their defining files
- Used internally by `action="index"` before graph sync

**Documented Response Format:**
```json
{
  "success": true,
  "message": "Pre-scan: {len(imports_map)} modules, {total} symbols",
  "data": {
    "repo_id": "uuid",
    "modules": 15,
    "symbols": 142,
    "duration_s": 2.1
  }
}
```

**Documented Errors:**
| Error Code | Description |
|------------|-------------|
| CI_006 | provide repo_id or path |
| CI_500 | internal failure |

---

## CLI Commands

**Finding:** No CLI commands found for codeindex domain.
- Searched `src/cli/` directory for codeindex references
- No matches found
- CodeIndex is accessed only via MCP tool `code_index`

---

## Documentation Quality Assessment

### Completeness Scores

| Category | Score | Notes |
|----------|-------|-------|
| Parameter Documentation | 100% | All parameters documented with types and requirements |
| Operation Documentation | 100% | All operations clearly described |
| Response Format Documentation | 100% | All response formats documented with JSON examples |
| Error Code Documentation | 100% | All error codes documented |
| Example Documentation | 100% | JSON examples provided for all actions |
| Cross-Reference Consistency | 100% | Consistent with concept.md, flow.md, output.md |

### Documentation Strengths
- Clear parameter descriptions with mutual exclusivity noted
- Comprehensive pipeline documentation for `index` action
- Error codes systematically documented
- Response formats include all documented fields
- Special behaviors documented (e.g., crash guard for incremental)

### Documentation Gaps
- None identified in documentation

### Cross-Documentation References
- concept.md: Business context, edge types, optimization history
- flow.md: Detailed pipeline stages and execution flow
- output.md: Database tables, symbol/edge data shapes
- llm-impact.md: LLM impact analysis
- tools.md: MCP tool specifications (this matrix source)

---

## Summary

**Total MCP Tools:** 1
**Total Actions:** 5
**Total CLI Commands:** 0
**Documentation Accuracy:** 100%
**Documentation Completeness:** 100%
