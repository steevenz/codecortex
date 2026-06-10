# repo_analyze — Full Semantic Repository Analysis

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-25

## Overview

`repo_analyze` performs **deep semantic analysis** of a repository. It runs a 7-phase pipeline: validate → discover → index (AST) → build graph → VCS integration → embedding (optional) → metrics.

This is a **heavyweight** tool — for fast health checks use `repo_inspect`, for security scanning use `repo_audit`.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to the repository |
| `force` | boolean | ❌ | `false` | Rebuild entire index from scratch |
| `incremental` | boolean | ❌ | `true` | Index only changed files (hash-based) |
| `parallel` | boolean | ❌ | `true` | Process files concurrently |
| `max_workers` | integer | ❌ | `4` | Threads for parallel parsing |
| `include_patterns` | array | ❌ | all common extensions | Source code file patterns |
| `exclude_patterns` | array | ❌ | `["node_modules","__pycache__",".git",".svn","dist","build"]` | Directories to ignore |
| `max_file_size_kb` | integer | ❌ | `500` | Skip files larger than this |
| `languages` | array | ❌ | `["auto"]` | Filter by language |
| `build_graph` | boolean | ❌ | `true` | Build dependency & call graph |
| `graph_relations` | array | ❌ | `["calls","imports","inherits","contains","references"]` | Relation types |
| `graph_backend` | string | ❌ | `"sqlite"` | `"sqlite"` or `"neo4j"` |
| `extract_symbols` | boolean | ❌ | `true` | Extract functions, classes, variables |
| `store_embeddings` | boolean | ❌ | `false` | Generate vector embeddings for semantic search |
| `embedding_model` | string | ❌ | `"codebert"` | Model: `"codebert"`, `"sentence-transformers"` |
| `store_raw_ast` | boolean | ❌ | `false` | Store raw AST (debugging) |
| `timeout_seconds` | integer | ❌ | `300` | Max execution time (5 min) |
| `dry_run` | boolean | ❌ | `false` | Simulate without writing to database |

## Flow (7 Phases)

```
PHASE 0: VALIDATE
  ├── repo_path exists? → 404 if not
  └── Detect VCS (.git → git, .svn → svn)

PHASE 1-3: CORE PIPELINE (orchestrator.analyze)
  ├── 1. File discovery → glob walker → .gitignore filtering
  ├── 2. AST indexing → Tree-Sitter → symbols (functions, classes, variables)
  └── 3. Graph building → calls, imports, inherits, contains, references

PHASE 4: VCS INTEGRATION
  ├── git log --name-only → churn hotspots (most changed files)
  └── git log --grep="fix|bug" → bug magnets (bug-prone files)

PHASE 5: EMBEDDING (optional)
  └── Generate vector embeddings → semantic search capability

PHASE 6: METRICS
  ├── Complexity (cyclomatic, max/avg)
  ├── Entry points (main, handler, controller, service)
  └── Graph density, connected components

PHASE 7: RESPONSE
  └── Return indexing summary + graph metrics + VCS insights + recommendations
```

## Response

### Success — Full analysis

```json
{
  "success": true,
  "message": "Full analysis completed in 18.34s",
  "data": {
    "repo_id": "f8a3d2e1-...",
    "repo_path": "/home/user/project",
    "vcs_type": "git",
    "index_mode": "incremental",
    "duration_seconds": 18.34,
    "indexing_summary": {
      "total_files_scanned": 187,
      "symbols_extracted": 1240,
      "edges_built": 1987,
      "languages": {"python": 98, "typescript": 56}
    },
    "graph_summary": {
      "total_nodes": 1240,
      "total_edges": 1987,
      "density": 0.0026,
      "entry_points": [{"symbol": "main", "file": "src/main.py"}],
      "relationship_types": {"calls": 543, "imports": 234}
    },
    "vcs_metrics": {
      "churn_hotspots": [{"file": "src/auth/handler.py", "change_count": 234, "risk": "high"}],
      "bug_magnets": [{"file": "src/auth/handler.py", "bug_commits": 34}]
    },
    "complexity_metrics": {
      "average_cyclomatic": 2.8,
      "max_cyclomatic": 18
    },
    "embedding_status": "disabled",
    "graph_ready": true,
    "search_ready": true,
    "recommendations": [
      {"severity": "warning", "message": "'src/auth/handler.py' is a high-risk churn hotspot."}
    ]
  }
}
```

### Error — Path not found

```json
{
  "success": false,
  "status_code": 404,
  "message": "Repository path does not exist",
  "data": {"repo_path": "/invalid/path", "suggestion": "Check path or run repo_init first"}
}
```

## When to Use

| Scenario | Use |
|----------|-----|
| Need call graph, dependencies, entry points | ✅ `repo_analyze` |
| Need symbol search, refactoring | ✅ `repo_analyze` |
| Fast health check (< 2s) | ❌ Use `repo_inspect` |
| Security audit only | ❌ Use `repo_audit` |
| File content search | ❌ Use `fs_search` |

## Integration

| Tool | Role in repo_analyze |
|------|----------------------|
| `repo_inspect` | Lightweight alternative (no AST) |
| `repo_audit` | Security-focused alternative |
| `code_search` | Query results after analysis |
| `code_refactor` | Use graph for impact analysis |
| `repo_init` | First-time setup before analysis |
