# repo_list — Daftar Repository yang Telah Di‑index

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-25

## Overview

`repo_list` returns all registered repositories from the SQLite database with rich filtering, metadata aggregation, real-time VCS status, pagination, and Markdown table output.

**Difference from `RegistryManager`**: The legacy registry (`~/.codecortex/registry.json`) stores lightweight metadata only. `repo_list` reads from the SQLite `repositories` table (the source of truth) and enriches with counts from `files`, `symbols`, and `edges` tables.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `filter_status` | string | ❌ | `"all"` | Filter by status: `"all"`, `"indexed"`, `"stale"`, `"orphaned"` |
| `include_metadata` | boolean | ❌ | `true` | Include total files, symbols, edges, language breakdown, age |
| `include_vcs_status` | boolean | ❌ | `false` | Include real-time VCS status (branch, ahead/behind, uncommitted changes) |
| `limit` | integer | ❌ | `50` | Maximum number of repos to return |
| `offset` | integer | ❌ | `0` | Pagination offset |
| `order_by` | string | ❌ | `"last_analyzed"` | Sort field: `"name"`, `"path"`, `"last_analyzed"`, `"size_bytes"` |
| `order_dir` | string | ❌ | `"desc"` | Sort direction: `"asc"` or `"desc"` |
| `output_format` | string | ❌ | `"json"` | Response format: `"json"` or `"table"` |

## Status Definitions

| Status | Condition | Description |
|--------|-----------|-------------|
| `indexed` | `last_indexed_at` exists AND ≤ 30 days AND path exists on disk | Healthy, fully indexed |
| `stale` | No `last_indexed_at` OR > 30 days old OR path missing | Needs re-indexing |
| `orphaned` | Path no longer exists on disk | Should be cleaned up |

## 5-Phase Flow

```
PHASE 1: Read SQLite DB
  • Query repositories table via SQLiteCodeRepositoryStore.list_repositories()
  • Enrich with path existence check (Path.exists()) and age calculation
  • Apply filter_status:
    - "all": no filter
    - "indexed": last_indexed_at IS NOT NULL AND age ≤ 30 AND path exists
    - "stale": last_indexed_at IS NULL OR age > 30 OR path missing
    - "orphaned": path does not exist on disk

PHASE 2: Metadata enrichment (if include_metadata=true)
  • Per repo: COUNT(*) from files, symbols, edges tables
  • Per repo: SUM(size_bytes) from files table
  • Per repo: extract file extensions → map to language → COUNT (e.g. .py→python)
  • Per repo: age_days = days since last_indexed_at

PHASE 3: VCS status (if include_vcs_status=true)
  • For each repo with a valid path:
    - Git: .git exists → git rev-parse --abbrev-ref HEAD (branch)
            → git status --porcelain (uncommitted changes)
            → git rev-list --count HEAD..@{upstream} (behind)
            → git rev-list --count @{upstream}..HEAD (ahead)
    - SVN: .svn exists → svn info --show-item revision
            → svn status (local modifications)
  • Timeout: 5 seconds per repo (individual subprocess calls)
  • Errors gracefully handled → partial VCS info returned

PHASE 4: Sorting & Pagination
  • Sort by order_by field (name, path, last_analyzed, size_bytes)
  • Sort direction (asc=ascending, desc=descending)
  • Slice: repos[offset:offset + limit]
  • total_count: count BEFORE pagination (for UI pagination metadata)

PHASE 5: Format Response
  • JSON: { total_count, limit, offset, repositories: [...] }
  • Table: Markdown table with columns: Repo ID, Path, VCS, Last Analyzed, Files, Symbols, Status
```

## Response

### Success — JSON format (default)

```json
{
  "success": true,
  "status_code": 200,
  "message": "Found 3 repositories",
  "data": {
    "total_count": 3,
    "limit": 50,
    "offset": 0,
    "repositories": [
      {
        "id": "f8a3d2e1-4b5c-6d7e-8f9a-0b1c2d3e4f5a",
        "name": "myapp",
        "root_path": "/home/user/projects/myapp",
        "last_indexed_at": "2026-05-25T10:00:00Z",
        "created_at": "2026-05-20T08:00:00Z",
        "updated_at": "2026-05-25T10:00:00Z",
        "status": "indexed",
        "total_files": 187,
        "total_symbols": 1240,
        "total_edges": 1987,
        "age_days": 0,
        "language_breakdown": {
          "python": 98,
          "typescript": 56,
          "go": 33
        },
        "vcs_status": {
          "vcs_type": "git",
          "branch": "main",
          "has_uncommitted_changes": false,
          "commits_ahead": 2,
          "commits_behind": 0
        }
      }
    ]
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-05-25T12:00:00Z",
    "version": "1.0.0",
    "api_version": "v1"
  }
}
```

### Success — Markdown table format

```json
{
  "success": true,
  "status_code": 200,
  "message": "Found 3 repositories",
  "data": {
    "total_count": 3,
    "limit": 50,
    "offset": 0,
    "table": "| Repo ID | Path | VCS | Last Analyzed | Files | Symbols | Status |\n|---------|------|-----|---------------|-------|----------|--------|\n| f8a3d2e1... | /home/user/projects/myapp | git | 2026-05-25 | 187 | 1240 | indexed |\n| d4e5f6a7... | /home/user/work/legacy-svn | svn | 2026-05-20 | 342 | 2150 | stale |\n| a1b2c3d4... | /home/user/archived/old-project | git | 2026-04-01 | 89 | N/A | stale |"
  }
}
```

### Error — No repositories found

```json
{
  "success": false,
  "status_code": 404,
  "message": "No repositories found in database. Run repo_init first.",
  "data": {
    "database_path": "~\\MCP\\mcp-codecortex\\database\\codecortex.db",
    "suggestion": "repo_init --repo_path <path> to index your first repository"
  }
}
```

## Language Extension Mapping

| Extension | Language | Extension | Language |
|-----------|----------|-----------|----------|
| `.py` | python | `.js` | javascript |
| `.ts` | typescript | `.jsx` | react |
| `.tsx` | react | `.go` | go |
| `.rs` | rust | `.java` | java |
| `.rb` | ruby | `.php` | php |
| `.swift` | swift | `.kt` | kotlin |
| `.cs` | csharp | `.cpp` | cpp |
| `.c` | c | `.sh` | shell |
| `.yml`/`.yaml` | yaml | `.json` | json |
| `.xml` | xml | `.toml` | toml |
| `.md` | markdown | `.html` | html |
| `.css` | css | `.sql` | sql |
| `.tf` | terraform | `.hcl` | hcl |
| `.lock` | lock | *(other)* | other |

## Integration with Other Tools

| Tool | Role in repo_list |
|------|-------------------|
| SQLite | Primary data source (repositories, files, symbols, edges tables) |
| Filesystem | `Path.exists()` check for orphaned detection |
| Git CLI | Real-time VCS status (branch, ahead/behind, uncommitted changes) |
| SVN CLI | Real-time VCS status (revision, local modifications) |
| `repo_cleanup` | Cleans up orphaned repos found by `filter_status="orphaned"` |
| `repo_init` | Creates repos that appear in the list |
| `repo_analyze` | Updates `last_indexed_at` → changes stale → indexed |

## When to Use

- **Session start:** "Show me all repos I've indexed" → `repo_list()`
- **Before analysis:** Check if a repo is indexed and non-stale → `repo_list(filter_status="indexed")`
- **Maintenance:** Find orphaned repos to clean up → `repo_list(filter_status="orphaned")`
- **VCS health:** Get branch/ahead/behind for all repos → `repo_list(include_vcs_status=true)`
- **Reporting:** Markdown summary of managed projects → `repo_list(output_format="table")`
- **UI pagination:** `repo_list(limit=10, offset=20)` with `total_count` for page controls
