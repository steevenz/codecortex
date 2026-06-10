# repo_init — Repository Initialization & Sync

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-24

## Overview

`repo_init` is the **primary entry point** for AI Coder to set up a repository. It performs:

1. **Validation** — checks path, handles `create_new` / `force`
2. **VCS Setup** — clones (`git clone`), checks out (`svn checkout`), or inits (`git init`)
3. **Indexing** — full pipeline: file discovery → AST parsing → symbol extraction → graph building
4. **Audit** — optional security scan via `code_audit` (secrets, PII, misconfig)
5. **Metadata** — saves repo info to database, returns `repo_id` + stats

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path where the repository will be initialized |
| `vcs_type` | string | ❌ | `"git"` | `"git"`, `"svn"`, or `"none"` |
| `remote_url` | string | ❌ | — | Remote URL for `git clone` or `svn checkout` |
| `create_new` | boolean | ❌ | `false` | Create new directory (error 409 if exists) |
| `force` | boolean | ❌ | `false` | Overwrite existing index (cleanup + re-index) |
| `include_patterns` | array | ❌ | source code exts | File patterns for indexing |
| `exclude_patterns` | array | ❌ | `["node_modules","__pycache__",".git",".svn","dist","build"]` | Directories to ignore |
| `run_audit` | boolean | ❌ | `true` | Run `code_audit` after indexing |
| `audit_categories` | array | ❌ | `["secrets","pii","misconfig"]` | Audit categories |
| `parallel` | boolean | ❌ | `true` | Parallel file processing |
| `max_workers` | integer | ❌ | `4` | Max worker threads |

## Flow

```
repo_init(repo_path, vcs_type, remote_url, run_audit=True)
  │
  ├── STEP 1: Validate path, handle create_new / force
  │     ├── path exists + create_new → 409 Conflict
  │     ├── path exists + already indexed + !force → 409 Conflict (reuse existing)
  │     ├── path exists + already indexed + force → cleanup + re-index
  │     └── path missing + !create_new + !remote_url → 404 Not Found
  │
  ├── STEP 2: VCS Setup
  │     ├── remote_url + git  → subprocess: git clone <url> <path>
  │     │                        → branch, commit from rev-parse
  │     ├── remote_url + svn → subprocess: svn checkout <url> <path>
  │     │                        → revision from svn info
  │     ├── local + git      → git init + rev-parse for branch/commit
  │     └── local + svn      → svn mkdir (attempt)
  │
  ├── STEP 3: Indexing
  │     └── orchestrator.repo_service.initialize(path)
  │           → file discovery (glob_walker)
  │           → .gitignore / .codecortexignore filtering
  │           → AST parsing (Tree-Sitter)
  │           → symbol extraction
  │           → edge building (call graph)
  │           → SQLite upsert
  │
  ├── STEP 4: Security Audit (if run_audit=True)
  │     └── CodeAuditor.audit()
  │           → regex scan for secrets (AWS keys, tokens, passwords)
  │           → PII detection (email, phone, SSN, CC)
  │           → misconfig detection (debug, wildcard CORS)
  │           → generates recommendations (.gitignore, rotate, remove)
  │
  └── STEP 5: Return Response
        ├── repo_id (UUID v4)
        ├── vcs_operation (type, operation, branch/commit/revision)
        ├── indexing_summary (duration, files, languages)
        └── audit_findings (summary, recommendations)
```

## Response Formats

### Success — Clone Git + Index + Audit

```json
{
  "success": true,
  "status_code": 200,
  "message": "Repository initialized (clone) and audited successfully",
  "data": {
    "repo_id": "f8a3d2e1-4b5c-6d7e-8f9a-0b1c2d3e4f5a",
    "repo_path": "/home/user/projects/myapp",
    "vcs_type": "git",
    "vcs_operation": {
      "type": "git",
      "operation": "clone",
      "success": true,
      "remote_url": "https://github.com/user/myapp.git",
      "branch": "main",
      "commit": "a1b2c3d"
    },
    "indexing_summary": {
      "duration_seconds": 15.23,
      "files_scanned": 245,
      "source_code_files": 187,
      "languages": {"python": 98, "typescript": 56, "go": 33},
      "audit_findings": {"critical": 1, "high": 4, "medium": 7, "low": 12},
      "audit_recommendations": {
        "gitignore_entries": [".env", "*.pem"],
        "secrets_to_rotate": ["AKIA..."],
        "files_to_remove": [".env.production"]
      }
    }
  }
}
```

### Success — Local Git Init (no remote, no audit)

```json
{
  "success": true,
  "message": "Repository initialized (init) successfully",
  "data": {
    "repo_id": "d4e5f6a7-...",
    "repo_path": "/home/user/new_project",
    "vcs_type": "git",
    "vcs_operation": {
      "type": "git",
      "operation": "init",
      "success": true,
      "branch": "main"
    },
    "indexing_summary": {
      "duration_seconds": 5.67,
      "files_scanned": 12,
      "audit_findings": {"enabled": false}
    }
  }
}
```

### Error — Repository already exists (no force)

```json
{
  "success": false,
  "status_code": 409,
  "message": "Repository already indexed. Use force=true to re-index.",
  "data": {
    "repo_path": "/home/user/projects/myapp",
    "existing_repo_id": "f8a3d2e1-..."
  }
}
```

### Error — Git clone failed

```json
{
  "success": false,
  "status_code": 400,
  "message": "Git clone failed: repository 'https://github.com/invalid/repo.git' not found",
  "data": null
}
```

## Integration with Other Tools

| Tool | Role in repo_init |
|------|-------------------|
| `repo_git` / `repo_svn` | VCS clone/init (called via subprocess directly) |
| `code_audit` | Security scan of indexed source code |
| `repo_analyze` | Deeper analysis after init |
| `repo_staleness` | Check if re-indexing is needed later |
| `repo_list` | Discover registered repos |
| Database SQLite | Store repo metadata, files, symbols, edges |

## Error Cases

| Error | Status | Message |
|-------|--------|---------|
| Path exists + `create_new=true` | `409` | `"Path already exists. Use create_new=false..."` |
| Already indexed + `force=false` | `409` | `"Repository already indexed. Use force=true..."` |
| Path missing + no remote | `404` | `"Path does not exist. Use create_new=true..."` |
| Git clone timeout | `408` | `"Git clone timed out"` |
| Invalid remote URL | `400` | `"Git clone failed: ..."` |
| SVN checkout failed | `400` | `"SVN checkout failed: ..."` |
