# CodeCortex MCP Tools — JSON Response Insight for AI Coders

> **Audience**: AI coding agents consuming MCP tool outputs.
> **Pattern**: All unified tools return `{success, status_code, message, data, meta}` via `api_response()`.

---

## Unified MCP Tools Overview

CodeCortex registers **6 unified MCP tools** in `src/main.py`. Each tool accepts parameter `action` + `args` — `ActionRouter` routes to the appropriate domain service.

| Unified Tool | Domain Actions | Internal Services |
|---|---|---|
| `codecortex:repository` | init, inspect, analyze, sync, audit, staleness, list, compact, cleanup, dump, restore, git, svn | CodeRepository |
| `codecortex:filesystem` | read, write, delete, copy, move, mkdir, list, search, watch, usage, audit | Filesystem |
| `codecortex:codebase` | analyze, search, audit, graph, status, index, test, refactor | CodeAnalysis + CodeGraph + CodeIndex + CodeTester + CodeRefactor |
| `codecortex:scaffolder` | list_stacks, get_stack, validate_name, list_licenses, generate_content, generate_class, create_project | Scaffolder |
| `codecortex:knowledge` | extract, query, status, relationships, validate | KnowledgeGraph |
| `codecortex:idegraph` | ingest, search, compact, export, timeline, state, artifacts | IDEGraph |

> ⚠️ **Domain actions** (`code_analyze`, `graph_query`, `refactor_symbol`, etc.) **are NOT separate MCP tools** — they are `action` strings passed to one of the 6 unified tools above.

---

## `codecortex:codebase` — CodeAnalysis Actions

### `code_analyze`
**Params**: `target`(req), `mode`(auto|detailed|symbol_focus), `max_depth`(3), `focus`, `follow_depth`(1), `cursor`, `page_size`(100), `include_docstring`(T), `include_comments`(F), `repo_id`

**Success `data`**:
```json
{
  "mode": "auto|detailed|symbol_focus",
  "target": "<path>",
  "count": 42,
  "symbols": [
    {
      "name": "ClassName",
      "kind": "class|function|method|variable",
      "file": "src/app.py",
      "line_start": 10,
      "line_end": 50,
      "signature": "def method(self, arg: str) -> bool",
      "docstring": "...",
      "parent_symbol": "ClassName",
      "calls": ["other_func"],
      "referenced_by": ["caller_func"]
    }
  ],
  "edges": [
    {"from": "Caller", "to": "Callee", "relation": "CALLS|INHERITS|IMPORTS", "weight": 1}
  ],
  "tree": {"dir": {"file.py": {"name": "ClassName", "type": "class"}}}
}
```

**Meta**: `pagination: {next_cursor, has_more, total, limit}`

**Error codes**: `CA_001`(missing target), `CA_002`(not found), `CA_500`(internal)

**🧠 AI Insight**:
- Use `symbols[].calls` to build call graph — suitable for impact analysis before refactor
- Use `edges[].relation` to detect coupling: `INHERITS` + `CALLS` from different modules = potential architectural smell
- Use `tree` for folder structure navigation — select `mode="overview"` for large projects >1000 files
- `pagination.next_cursor` enables streaming for large repositories

---

### `code_search`
**Params**: `query`(req), `repo_id`, `limit`(50), `file_pattern`(*), `include_content`(F), `semantic`(F), `graph`(F), `graph_relations`

**Success `data`** (multi-layer):
```json
{
  "matches": [{"symbol": "...", "file": "...", "line": 10, "context": "...", "score": 0.95}],
  "total_matches": 10,
  "semantic_hits": [{"symbol": "...", "similarity": 0.87}],
  "total_semantic": 3,
  "relationships": [{"from": "...", "to": "...", "relation": "CALLS"}],
  "total_relationships": 5,
  "synced_at": "2026-05-26T..."
}
```

**Error codes**: `CA_010`(no query), `CA_011`(bad request), `CA_500`

**🧠 AI Insight**:
- 3-layer search: text (always) → semantic (`semantic=True`) → graph (`graph=True`)
- For rename: use `semantic=True` first to find all related name variants
- For bug hunting: `graph=True` to see caller/callee chain
- `score` on text matches is FTS5 relevance (0-1); `similarity` on semantic is cosine similarity

---

### `code_audit`
**Params**: `target`(req), `scan_categories`, `severity_threshold`(medium), `entropy_threshold`(4.5), `include_comments`(F), `max_file_size_kb`(1024), `files`, `output_format`(json), `use_ast`(T), `use_aiignore`(T), `repository_id`, `since`

**Success `data`**:
```json
{
  "target": "<path>",
  "scan_categories": ["secrets", "pii", "misconfig", "vulns", "naming", "type_hints"],
  "scanned_files": 150,
  "compliance_score": 85,
  "summary": {"by_category": {...}, "by_severity": {"critical": 0, "high": 2, "medium": 5}},
  "findings": [
    {
      "category": "secrets|naming|type_hints|di_compliance",
      "severity": "critical|high|medium|low",
      "file": "src/config.py",
      "line": 42,
      "column": 8,
      "code": "API_KEY = "sk-..."",
      "message": "Hardcoded API key detected",
      "details": "...",
      "context": "surrounding code lines",
      "confidence": 0.95,
      "remediation": "Move to environment variable",
      "standard_ref": "Aegis-Security-v1.0"
    }
  ],
  "recommendations": ["Move secrets to .env", "Add type hints to 15 functions"],
  "errors": []
}
```

**Error codes**: `CA_020`(no target), `CA_021`(not found), `CA_500`

**🧠 AI Insight**:
- `compliance_score` is a 0-100 metric for readiness assessment
- Prioritize findings with `severity=critical` + `confidence>0.9`
- `remediation` contains actionable fix suggestions
- `standard_ref` refers to the Aegis standard violated — suitable for compliance reporting
- For incremental audit, use `since` with ISO timestamp from previous audit

---

### `code_status`
**Params**: `path`(req), `repo_id`, `include_metrics`(T), `include_vcs`(T), `include_symbols`(T), `language`

**Success `data`** (cached or fresh):
```json
{
  "target": "<path>",
  "repo_id": "uuid",
  "summary": {
    "files": 150, "directories": 20,
    "total_lines": 15000, "code_lines": 12000,
    "comment_lines": 2000, "blank_lines": 1000,
    "comment_ratio": 0.14,
    "languages": {"python": 80, "javascript": 20, "yaml": 10}
  },
  "symbols": {"classes": 30, "functions": 120, "variables": 300},
  "graph_stats": {"nodes": 450, "edges": 600, "density": 0.003, "components": 5},
  "vcs": {
    "type": "git", "branch": "main",
    "commit": "a1b2c3d", "last_commit_date": "2026-05-25",
    "uncommitted_changes": 3, "untracked_files": 2
  },
  "cached": true
}
```

**Error codes**: `CA_030`(no path), `CA_031`(not found), `CA_500`

**🧠 AI Insight**:
- Always check `cached` — if `true`, data is from index cache (instant)
- `comment_ratio < 0.1` = under-documented; `> 0.3` = too many comments
- `graph_stats.density` low (< 0.01) indicates good modular architecture
- `vcs.uncommitted_changes > 10` indicates unstable code — recommend committing before refactor

---

## `codecortex:codebase` — CodeGraph Actions

### `action=graph` — `graph_search`
**Params**: `action`(req: symbol|relation|trace_flow|modular|semantic), `query`, `repo_id`, `repo_path`, `symbol_type`(any), `fuzzy`(F), `edit_distance`(2), `relation_type`, `target_symbol_id`, `max_depth`(3), `modular_type`, `limit`(20), `cursor`

**Success `data` (action=symbol)**:
```json
{
  "functions": [{"name": "getUser", "file": "src/service.py", "line": 15}],
  "classes": [{"name": "UserService", "file": "src/service.py", "line": 1}],
  "variables": [{"name": "DB_URL", "file": "src/config.py", "line": 5}],
  "total": 3
}
```

**Success `data` (action=relation/trace_flow/modular)**:
```json
{
  "nodes": [...],
  "edges": [...],
  "next_cursor": "...",
  "has_more": false,
  "total": 10
}
```

**Error codes**: `GRPH_008`(invalid action/no repo_id)

**🧠 AI Insight**:
- `action="symbol"` with `fuzzy=True` for typo-tolerant lookup (edit_distance max 2)
- `action="relation"` with `relation_type="callers"` for impact analysis
- `action="trace_flow"` needs `target_symbol_id` (from graph node ID)
- Use `modular_type` filter to limit to specific module

---

### `graph_query`
**Params**: `query_type`(req), `target`(req), `repo_id`, `repo_path`, `max_depth`(3), `end_node`, `context`, `direction`(both), `limit`(20)

**Success `data`** (varies by query_type):
```json
// query_type=callers
{"callers": [{"name": "callerFunc", "file": "src/a.py", "line": 10}], "total": 5}

// query_type=callers+depth=3 (all_callers)
{"nodes": [...], "edges": [...], "total": 20}

// query_type=trace_path
{"path": ["A", "B", "C"], "length": 3}

// query_type=dead_code
{"unused_functions": [{"name": "obsolete()", "file": "src/old.py", "line": 5}]}
```

**Error codes**: `GRPH_002`

**🧠 AI Insight**:
- For refactoring: `query_type="all_callers"` for full blast radius
- For bug tracing: `query_type="trace_flow"` from entry point
- For dependency audit: `query_type="deps"` or `query_type="circular"` 
- Use `"module::function"` format in `target` if names are ambiguous

---

### `graph_audit`
**Params**: `repo_id`(req), `audit_types`, `repo_path`, `include_summary`(F), `degree_threshold`(10), `limit`(50)

**Success `data`**:
```json
{
  "god_nodes": [
    {"name": "Utils", "in_degree": 45, "file": "src/utils.py", "risk": "high"}
  ],
  "security": [...],
  "dead_code": [{"name": "unusedFunc", "file": "src/legacy.py"}],
  "complexity": [{"name": "complexFunc", "complexity": 45, "file": "src/hard.py"}],
  "communities": {"count": 12, "clusters": {"0": [...], "1": [...]}},
  "coupling": [
    {"source": "moduleA", "target": "moduleB", "score": 0.85, "relation": "CALLS"}
  ],
  "circular_deps": {"count": 3, "items": [...], "suggestions": [...]},
  "markdown_summary": "# Architectural Report ..."  // if include_summary=true
}
```

**Error codes**: `GRPH_009`

**🧠 AI Insight**:
- Audit types are independent — error in one type does not stop others (partial results)
- `god_nodes` with `in_degree > 30` = God Class that needs to be split
- `coupling.score > 0.7` = architectural smell — unrelated modules calling each other
- `markdown_summary` for direct reporting to user in readable format

---

### `graph_build`
**Params**: `repo_path`(req), `repo_id`, `detect_modular`(T), `build_dependency_graph`(T), `include_core_contracts`(T), `scan_hmvc_p`(T), `max_depth`(5), `use_cache`(T), `include_stats`(T)

**Success `data`**:
```json
{
  "repo_id": "uuid",
  "nodes": 450,
  "edges": 600,
  "modular_summary": {"modules": [...], "plugins": [...], "services": [...]},
  "dependency_graph": {"layers": [...], "circular_deps": [...]},
  "graph_stats": {"functions": 120, "classes": 30, "files": 50, "calls": 400, "inherits": 20}
}
```

**Error codes**: `GRPH_004`(path not found)

**🧠 AI Insight**:
- Must run before `graph_query` / `graph_audit` for new repos
- Cache automatically if `use_cache=True` — call again to refresh
- `graph_stats` provides quick overview of codebase size in graph terms

---

### `graph_relationship`
**Params**: `repo_id`(req), `target_node`(req), `relation_type`, `direction`(both), `depth`(1), `modular_type`, `include_community`(F), `min_confidence`(INFERRED), `limit`(100), `cursor`

**Success `data`**:
```json
{
  "nodes": [...],
  "edges": [...],
  "community": {"id": 1, "size": 15, "members": [...]},
  "total": 50,
  "next_cursor": "...",
  "has_more": false
}
```

**Error codes**: `GRPH_011`

**🧠 AI Insight**:
- For architecture exploration: depth=1 (default) for immediate neighbors; depth=2 for transitive
- `min_confidence` filtering: `EXTRACTED` (definitely from AST) > `INFERRED` (from naming) > `AMBIGUOUS`
- `include_community=True` for Leiden cluster detection — see if 2 nodes in different communities but connected = surprising coupling

---

### `graph_refactor`
**Params**: `repo_id`(req), `action`(req: impact|preview|apply), `refactor_type`(req), `target_node`(req), `options`, `dry_run`(F)

**Success `data`**:
```json
{
  "impact": {"affected_files": [...], "affected_symbols": [...], "risk": "low|medium|high"},
  "plan": {"steps": [...], "estimated_effort": "..."},
  "result": {"applied": true, "commit_hash": "abc123"},
  "validation": {"passed": true, "warnings": [...]}
}
```

**Error codes**: `GRPH_012`

**🧠 AI Insight**:
- Always call with `action="impact"` first before `preview` or `apply`
- `dry_run=True` for simulation without changes
- `risk: "high"` means >10 files affected — needs manual review

---

## `codecortex:filesystem` — Filesystem Actions

### `action=manage` — `fs_manage`
**Params**: `operation`(req), `path`, `content`, `encoding`, `paths`, `operations`, `items`, `mode`, `owner`, `group`, `target`, `dry_run`, `overwrite`, `recursive`, `permissions`, + 20+ optional params

**Operations**: `tree`, `read`, `write`, `append`, `delete`, `move`, `rename`, `write_batch`, `chmod`, `chown`, `symlink`, `touch`, `archive`, `xattr`, `convert`, `tree_sync`

**Success `data`** (varies by operation):
```json
// operation=read
{"path": "/abs/path", "content": "file contents...", "size": 1024, "encoding": "utf8"}

// operation=tree
{"path": "/abs/path", "tree": {"dir": {"file.py": {"type": "file", "size": 1024}}}}

// operation=write
{"path": "/abs/path", "written": true, "size": 500}

// operation=tree_sync
{"total": 150, "duration_seconds": 1.2, "disk": {...}, "synced_at": "ISO8601"}
```

**Error codes**: `FS_001`(no path), `FS_002`(no paths), `FS_003`(no operations), `FS_004`(unknown op), `FS_005`-`FS_012`, `FS_500`

**🧠 AI Insight**:
- One tool for ALL filesystem operations — check `operation` field in response
- `tree_sync` for filesystem to database index synchronization (call before code_analyze)
- `write_batch` for bulk file creation (up to 100 files) — more efficient than looping

---

### `fs_search`
**Params**: `root_path`, `repo_id`, `file_pattern`(*), `file_regex`, `content_regex`, `content_regex_flags`, `recursive`(T), `max_depth`, `include_hidden`(F), `max_results`(100), `include_content_snippet`(T), `exclude_patterns`, `replace_text`, `dry_run`(T)

**Success `data`**:
```json
{
  "results": [
    {"path": "/abs/path/file.py", "size": 1024, "lines": 50,
     "matches": [{"line": 10, "column": 5, "content": "def search():", "context": "..."}]}
  ],
  "total": 10,
  "next_cursor": "...",
  "has_more": false,
  "replace_results": {"files_modified": 0}  // if replace_text provided
}
```

**Error codes**: `FS_005`

**🧠 AI Insight**:
- `replace_text` + `dry_run=True` to preview find-and-replace before execution
- `content_regex_flags="i"` for case-insensitive search
- Combine `file_pattern="*.py"` + `content_regex="class \w+:"` to find class definitions
- Use `include_content_snippet=True` to see context of matching lines

---

### `fs_watch`
**Params**: `target`(req), `recursive`(T), `events`, `poll_interval`(1), `max_events`(100)

**Success `data`**:
```json
{
  "changes": [
    {"path": "/abs/path/file.py", "event": "modify|create|delete", "timestamp": "ISO8601"}
  ],
  "total": 3
}
```

**Error codes**: `FS_006`

**🧠 AI Insight**:
- Polling-based, not event-driven — `poll_interval` minimum 1 second
- For long-running watch, call repeatedly with small `max_events`

---

### `fs_df`
**Params**: `target`(req), `recursive`(T), `depth`(10), `unit`(auto), `include_hidden`(F), `exclude_patterns`, `aggregate_by`(file), `max_items`(100)

**Success `data`**:
```json
{
  "target": "/abs/path",
  "total_size": "150 MB",
  "total_files": 1000,
  "items": [
    {"path": "node_modules", "size": "80 MB", "type": "directory", "percentage": 53}
  ],
  "aggregation": {
    "by_extension": {".py": "20 MB", ".js": "30 MB"},
    "by_vcs_status": {"tracked": "100 MB", "untracked": "50 MB"}
  }
}
```

**Error codes**: `FS_007`

**🧠 AI Insight**:
- `aggregate_by="extension"` to see which language is most dominant
- `aggregate_by="vcs_status"` to see how many untracked files
- Suitable for pre-cleanup assessment before repo_init

---

### `fs_audit`
**Params**: `target`(req), `recursive`(T), `severity`, `check_permissions`(T), `check_hidden`(T), `max_file_size_mb`(100), `exclude_patterns`, `limit`(200)

**Success `data`**:
```json
{
  "target": "/abs/path",
  "findings": [
    {
      "path": "credentials.yml",
      "severity": "critical|high|medium|low",
      "category": "sensitive_file|permission|hidden_vcs|large_file",
      "message": "File contains 'password' in name",
      "recommendation": "Remove or .gitignore this file"
    }
  ],
  "total_findings": 5
}
```

**Error codes**: `FS_008`

**🧠 AI Insight**:
- Metadata-based scan (file name, permission, size) — does not read content
- `severity=critical` + `category=sensitive_file` = potential security leak — must handle immediately

---

## `codecortex:repository` — CodeRepository Actions

### `action=init` — `repo_init`
**Params**: `repo_path`(req), `vcs_type`(git), `remote_url`, `create_new`(F), `force`(F), `include_patterns`, `exclude_patterns`, `run_audit`(T), `audit_categories`, `parallel`(T), `max_workers`(4)

**Success `data`**:
```json
{
  "repo_id": "uuid-v4",
  "repo_path": "/abs/path",
  "vcs_type": "git|svn|none",
  "vcs_operation": {"type": "git", "operation": "clone|init", "success": true, "branch": "main", "commit": "abc123"},
  "indexing_summary": {
    "duration_seconds": 5.2,
    "files_scanned": 150,
    "source_code_files": 100,
    "languages": {"python": 5, "javascript": 2},
    "audit_findings": {"total": 3, "critical": 0, ...},
    "audit_recommendations": [...]
  }
}
```

**Error codes**: `REP_409`(exists), `REP_404`(not found), `REP_TIMEOUT`, `REP_CLONE`, `REP_CHECKOUT`

**🧠 AI Insight**:
- Call this first before other tools for new repos — generates `repo_id` required by other tools
- `force=True` to re-index from scratch (destroy + rebuild)
- `vcs_operation` informs whether clone/init succeeded — check `success` field
- If already initialized, response `409` with `existing_repo_id` — use that ID directly

---

### `repo_inspect`
**Params**: `repo_path`(req), `repo_id`, `include_git_diagnostics`(T), `include_svn_diagnostics`(F), `include_index_metadata`(T), `include_vcs_status`(T), `include_file_stats`(T), `include_dependency_summary`(F), `diagnostic_period`(1_year), `output_format`(json), `timeout_seconds`(30)

**Success `data`**:
```json
{
  "repo_id": "uuid",
  "repo_path": "/abs/path",
  "vcs_type": "git",
  "vcs_branch": "main",
  "index_metadata": {
    "indexed": true,
    "last_indexed_at": "ISO8601",
    "total_files_indexed": 150,
    "total_symbols_indexed": 300,
    "total_edges": 500
  },
  "vcs_status": {"has_uncommitted_changes": false, "commits_ahead": 0, "commits_behind": 2},
  "file_statistics": {
    "total_files": 150, "total_size_mb": 25.3,
    "breakdown": {"source_code_files": 100, "config_files": 20, ...},
    "largest_files": [{"path": "bundle.js", "size_mb": 5.2}]
  },
  "dependency_summary": {"package_managers": [{"type": "npm", "file": "package.json"}]},
  "git_diagnostics": {
    "churn_hotspots": [{"file": "src/hot.py", "change_count": 200, "risk": "high"}],
    "bus_factor": {"top_contributor_percentage": 75, "bus_factor_risk": "high"},
    "bug_magnets": [{"file": "src/buggy.py", "bug_commits": 15}],
    "commit_velocity": {"commits_per_month_avg": 42, "trend": "increasing", "history": [...]},
    "crisis_frequency": {"reverts_and_hotfixes": 10, "crisis_risk": "low"}
  },
  "insights": {
    "ai_readiness_score": 78,
    "recommended_actions": [...]
  }
}
```

**Error codes**: `REP_404`

**🧠 AI Insight**:
- **Zero parsing** — instant even for large repositories. Use for fast health check.
- `ai_readiness_score` (0-100) — score < 50 means needs indexing or VCS setup
- `git_diagnostics` provides churn, bus factor, bug magnets — suitable for code review prioritization
- `churn_hotspots` with `risk=high` are refactoring priority candidates
- `bus_factor_risk=high` (top contributor >60%) — knowledge silo risk

---

### `repo_analyze`
**Params**: `repo_path`(req), `force`(F), `incremental`(T), `parallel`(T), `max_workers`(4), `include_patterns`, `exclude_patterns`, `max_file_size_kb`(500), `languages`, `build_graph`(T), `graph_relations`, `graph_backend`(sqlite), `extract_symbols`(T), `store_embeddings`(F), `embedding_model`(codebert), `store_raw_ast`(F), `timeout_seconds`(300), `dry_run`(F)

**Success `data`**:
```json
{
  "repo_id": "uuid",
  "repo_path": "/abs/path",
  "vcs_type": "git",
  "index_mode": "incremental|full",
  "duration_seconds": 15.3,
  "indexing_summary": {
    "total_files_scanned": 150,
    "symbols_extracted": 300,
    "edges_built": 500,
    "languages": {"python": {"files": 80, "loc": 8000}}
  },
  "graph_summary": {
    "total_nodes": 450, "total_edges": 600,
    "density": 0.003, "entry_points": [...],
    "relationship_types": {"CALLS": 400, "INHERITS": 50, "IMPORTS": 150}
  },
  "vcs_metrics": {
    "churn_hotspots": [...],
    "bug_magnets": [...]
  },
  "complexity_metrics": {
    "max_cyclomatic": 25, "average_cyclomatic": 3.5,
    "most_complex": [{"name": "func", "file": "src/a.py", "complexity": 25}]
  },
  "embedding_status": "disabled|enabled (codebert)|failed",
  "graph_ready": true,
  "search_ready": true,
  "codemap": {"dir": {"file": {"symbols": [...]}}},
  "recommendations": [...]
}
```

**Error codes**: `REP_404`, `REP_004`

**🧠 AI Insight**:
- **Heavyweight** — 7-phase pipeline. For fast check, use `repo_inspect`.
- `dry_run=True` to see what will be indexed without writing to DB
- `graph_ready` and `search_ready` indicate whether graph/query tools are ready to use
- `complexity_metrics.max_cyclomatic > 15` = function too complex — refactoring candidate
- `codemap` provides complete folder structure + symbol map

---

### `repo_sync`
**Params**: `repo_path`(req), `mode`(auto|full|fast), `include_patterns`, `exclude_patterns`, `reindex_updated`(T), `remove_deleted`(T), `dry_run`(F)

**Success `data`**:
```json
{
  "repo_id": "uuid",
  "mode": "auto",
  "changes_summary": {
    "added": 5, "modified": 3, "deleted": 1, "unchanged": 141
  },
  "duration_ms": 1200
}
```

---

### Additional repo_* actions (repo_audit, repo_staleness, repo_list, repo_db_compact, repo_cleanup, repo_git, repo_svn)

These follow the same `api_response` pattern. Key notes:

| Action | `data` shape | Use case |
|--------|-------------|----------|
| `repo_audit` | `{findings, scanned_files, summary, duration_seconds}` | Git/SVN history secrets scan |
| `repo_staleness` | `{repo_id, stale_files: N}` | Check if re-index needed |
| `repo_list` | `{repositories: [{id, root_path, vcs_type, created_at, sync_at}]}` | List all repositories |
| `repo_db_compact` | `{before_size, after_size, freed_bytes}` | VACUUM maintenance |
| `repo_cleanup` | `{deleted: true, repo_id}` | **Destructive** — delete all data |
| `repo_git` | Varies by git action | Arbitrary git operations |
| `repo_svn` | `{url, revision, ...}` | Arbitrary SVN operations |

---

## `codecortex:codebase` — CodeRefactor Actions

### `action=refactor` — `code_refactor`
**Params**: `repo_id`(req), `action`(req), `target_symbol`(req), `changes`, `dry_run`(T), `ai_feedback`(F), `confidence_threshold`(85)

**Actions**: `impact`, `rename`, `move`, `change_signature`, `extract_function`, `inline_function`, `preview`, `apply`, `rename_file`, `rename_folder`, `move_file`, `modularize`

**Success `data`**:
```json
{
  "status": "ok|error|preview",
  "message": "Renamed 5 occurrences across 3 files",
  "repository_id": "uuid",
  "action": "rename",
  "changes": [
    {"file": "src/a.py", "line": 10, "old": "oldName", "new": "newName", "status": "applied"}
  ],
  "blast_radius": {"files_affected": 3, "symbols_affected": 5, "risk": "low|medium|high"},
  "commit_hash": "abc123def",
  "validation_result": {"passed": true, "warnings": []}
}
```

**Error codes**: `REF_400`(invalid action/missing params), `REF_500`(execution error)

**🧠 AI Insight**:
- **Always start with `action="impact"`** — this is read-only, check blast radius first
- `target_symbol` format: `"file_path::SymbolName"` or `"module::FunctionName"`
- `changes` object varies per action (see tool docstring)
- `dry_run=True` default — SET `dry_run=False` to execute
- `confidence_threshold` (0-100) — if confidence above threshold, auto-apply
- `validation_result.passed=false` means conflict — do not apply

---

## `codecortex:codebase` — CodeTester Actions

### `action=test` — `code_tester`
**Params**: `action`(req), `repo_path`, `repo_id`, `files`, `framework`, `timeout_seconds`(120), `verbose`(F)

**Actions**: `discover`, `run`, `coverage`, `diagnose`, `generate`

**Success `data`**:
```json
// action=discover
{"frameworks": ["pytest", "jest"], "test_files": ["tests/test_a.py"], "total": 10}

// action=run
{"summary": {"passed": 8, "failed": 2, "skipped": 1, "duration_seconds": 5.3},
 "results": [{"file": "tests/test_a.py", "name": "test_login", "status": "passed", "duration_ms": 100}]}

// action=coverage
{"lines_total": 1000, "lines_covered": 750, "coverage_percent": 75,
 "files": [{"file": "src/a.py", "coverage": 80}]}

// action=diagnose
{"flaky_tests": [...], "slow_tests": [...], "suggestions": [...]}

// action=generate
{"files_created": ["tests/test_b.py"], "template": "pytest"}
```

**🧠 AI Insight**:
- `action="discover"` to auto-detect test framework and files
- `action="diagnose"` for flaky test detection + optimization suggestions
- `action="generate"` to auto-generate test boilerplate from existing source code

---

## `codecortex:codebase` — CodeIndex Actions

### `action=index` — `code_index`
**Params**: `action`(req), `repo_id`, `repo_path`, `force`(F)

**Actions**: `status`, `build`, `reindex`, `clear`, `optimize`, `stats`

**Success `data`**:
```json
// action=status
{"repo_id": "uuid", "indexed": true, "last_indexed_at": "ISO8601", "pending_files": 0}

// action=build
{"repo_id": "uuid", "files_indexed": 150, "symbols_indexed": 300, "duration_seconds": 5.2}

// action=clear
{"cleared": true, "repo_id": "uuid"}

// action=stats
{"total_files": 150, "total_symbols": 300, "by_kind": {"class": 30, "function": 120}}
```

---

## `codecortex:scaffolder` — Scaffolder Actions

### `action=list_stacks` — `scaffold_list_stacks`
**Params**: none

**Success `data`**:
```json
{"stacks": [
  {"name": "python", "display_name": "Python", "version": "3.12",
   "project_types": ["standard", "data_science", "web_api", "cli_tool", "automation"]}
]}
```

### `scaffold_get_stack`
**Params**: `stack_name`(req)

**Success `data`**:
```json
{"stack": {
  "name": "python", "display_name": "Python", "version": "3.12",
  "file_conventions": {"directories": "snake_case", "modules": "snake_case.py", "classes": "PascalCase"},
  "project_types": [...]  // full detail with id, display_name, description
}}
```

### `scaffold_validate_name`
**Params**: `name`(req)

**Success `data`**:
```json
{"display": "My Project", "slug": "my-project", "snake": "my_project", "pascal": "MyProject"}
```

**Error**: `INVALID_NAME`

### `scaffold_list_licenses`
**Params**: none

**Success `data`**:
```json
{"licenses": [
  {"id": "MIT", "name": "Mit License"},
  {"id": "Apache-2.0", "name": "Apache License 2.0"}
]}
```

### `scaffold_generate`
**Params**: `file_type`(req), `project_category`(standard), `project_name`, `author`, `email`, `license_name`

**Success `data`**:
```json
{"filename": "README.md", "content": "# ...", "content_length": 2634}
```

### `scaffold_make`
**Params**: `type`(req), `name`(req), `stack`(python), `module`, `project_name`, `author`, `target_path`, `overwrite`

**Success `data`**:
```json
{
  "type": "model", "type_display": "Model / Entity", "stack": "python",
  "class_name": "User", "file_name": "user.py",
  "relative_path": "models/entities/user.py",
  "absolute_path": null, "content": "class User(BaseModel):...",
  "content_length": 286, "written": false
}
```

### `scaffold_create`
**Params**: `name`(req), `stack`(python), `project_type`(standard), `target_path`, `author`, `email`, `version`, `license`, `dry_run`(T), `overwrite`(F), `include_ai`(F), `include_trainer`(F), `project_code`

**Success `data` (dry_run=true)**:
```json
{
  "dry_run": true,
  "name": {"display": "My Project", "slug": "my-project", "snake": "my_project", "pascal": "MyProject"},
  "stack": "python", "stack_display": "Python",
  "project_type": "standard", "project_type_display": "Standard Python Project",
  "target_path": "/abs/path", "author": "Author", "email": "author@example.com",
  "version": "0.1.0", "license": "MIT",
  "include_ai": false, "include_trainer": false,
  "template_count": 42, "directory_count": 35,
  "template_context_keys": ["project_name", "author", ...]
}
```

---

## Unified API Tools Summary (6 Tools — action+args Dispatch)

### `codecortex:repository`
**Action**: `init|inspect|analyze|sync|audit|staleness|list|compact|cleanup|dump|restore|git|svn`
**Args**: action-specific parameters

Response shape identical to module actions above.

### `codecortex:filesystem`
**Action**: `read|write|delete|copy|move|mkdir|search|watch|usage|audit`
**Args**: action-specific

### `codecortex:codebase`
**Action**: `analyze|search|audit|graph|status|index|test|refactor`
**Args**: action-specific

### `codecortex:scaffolder`
**Action**: `list_stacks|get_stack|validate_name|list_licenses|generate_content|generate_class|create_project`
**Args**: action-specific

### `codecortex:knowledge`
**Action**: `extract|query|status|relationships|validate`
**Args**: action-specific

### `codecortex:idegraph`
**Action**: `ingest|search|compact|export|timeline|state|artifacts`
**Args**: action-specific

---

## Response Contract (All Unified Tools)

### Success:
```json
{
  "success": true,
  "status_code": 200,
  "message": "Human-readable description",
  "data": { /* tool-specific */ },
  "meta": {
    "timestamp": "ISO8601",
    "request_id": "uuid",
    "duration_ms": 123
  }
}
```

### Error:
```json
{
  "success": false,
  "status_code": 400|404|409|500,
  "message": "Error description",
  "data": null,
  "meta": {
    "timestamp": "ISO8601",
    "request_id": "uuid",
    "error_code": "ERR_CODE"
  }
}
```

---

## AI Coder Quick Reference

| What You Want To Do | Tool / Action | Key Field |
|---------------------|-------------------|-----------|
| Check repo health | `repo_inspect` | `ai_readiness_score` |
| Index new repo | `repo_init` | `repo_id` |
| Search code | `code_search` | `matches[].score`, `semantic_hits[].similarity` |
| Analyze architecture | `code_analyze` | `symbols[].kind`, `edges[].relation` |
| Audit security | `code_audit` | `compliance_score`, `findings[].severity` |
| Graph query | `graph_query` | `callers`, `callees`, `dead_code` |
| Audit architecture | `graph_audit` | `god_nodes`, `coupling`, `circular_deps` |
| Impact analysis | `code_refactor` action=impact | `blast_radius.risk` |
| Refactor | `code_refactor` action=rename\|move\|... | `changes[]`, `commit_hash` |
| Run tests | `code_tester` action=run | `summary.passed`, `summary.failed` |
| Generate tests | `code_tester` action=generate | `files_created` |
| File operations | `fs_manage` | `operation` (read\|write\|delete\|move\|...) |
| Disk usage | `fs_df` | `items[].percentage` |
| Git operations | `repo_git` | Varies by git action |
| SVN operations | `repo_svn` | Varies by SVN action |
