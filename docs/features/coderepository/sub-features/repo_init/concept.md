# repo_init: Repository Initialization

> **Tool:** repo_init
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Initialize, clone, or sync a repository for CodeCortex analysis. Performs one-shot setup: validates path, configures VCS (clone/init/checkout), indexes source code (AST → symbols → graph), and optionally runs security audit.

## Why This Exists

- **One-Shot Setup:** Combines VCS setup + indexing + audit in single call
- **AI Coder Onboarding:** Provides comprehensive ai_actions for next steps and best practices
- **VCS Flexibility:** Supports git clone/init, svn checkout/mkdir, or no VCS
- **Safety:** Validates path existence, handles create_new/force, prevents accidental overwrites
- **Integration:** Automatically captures VCS metadata for repo_staleness tracking

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path where repository will be initialized |
| `vcs_type` | string | ❌ | `git` | Version control system: "git", "svn", or "none" |
| `remote_url` | string | ❌ | — | Remote URL for clone (git) or checkout (svn) |
| `create_new` | bool | ❌ | `false` | Create new directory (error 409 if exists) |
| `force` | bool | ❌ | `false` | Overwrite existing index (cleanup + re-index) |
| `include_patterns` | list | ❌ | — | File patterns to include (default: source code extensions) |
| `exclude_patterns` | list | ❌ | — | Directories to exclude (default: node_modules, __pycache__, .git, .svn) |
| `run_audit` | bool | ❌ | `true` | Run security audit after indexing |
| `audit_categories` | list | ❌ | — | Audit categories: "secrets", "pii", "misconfig", "vulns" |
| `parallel` | bool | ❌ | `true` | Process files in parallel during indexing |
| `max_workers` | int | ❌ | `4` | Number of worker threads for parallel processing |

## Output

```json
{
  "repo_id": "uuid-v7",
  "repo_path": "/absolute/path",
  "vcs_type": "git",
  "vcs_operation": {
    "type": "git",
    "operation": "clone",
    "success": true,
    "remote_url": "https://github.com/user/repo.git",
    "branch": "main",
    "commit": "abc1234"
  },
  "indexing_summary": {
    "duration_seconds": 12.5,
    "files_scanned": 150,
    "source_code_files": 120,
    "languages": {"python": 80, "javascript": 40},
    "audit_findings": {
      "critical": 0,
      "high": 2,
      "medium": 5,
      "low": 10
    }
  },
  "ai_actions": [
    {
      "priority": "info",
      "action": "Repository 'myproject' initialized successfully with 150 files indexed.",
      "status": "completed",
      "repo_id": "uuid-v7"
    },
    {
      "priority": "high",
      "action": "2 HIGH severity issues found. Address security concerns before proceeding.",
      "command_hint": "repo_audit --repo_path /absolute/path",
      "count": 2
    },
    {
      "priority": "medium",
      "action": "Large codebase (150 files). Run repo_analyze for full semantic analysis including call graphs.",
      "command_hint": "repo_analyze --repo_path /absolute/path --build_graph=true"
    },
    {
      "priority": "info",
      "action": "Monitor repository health with periodic checks.",
      "recommended_workflow": [
        "repo_staleness --check remote status",
        "repo_sync --incremental updates",
        "repo_audit --periodic security scans"
      ]
    }
  ]
}
```

## AI Actions

The tool provides context-aware ai_actions:

1. **Initialization Status** — Confirms successful repo creation with file count
2. **Security Alerts** — Critical/high findings from audit with remediation commands
3. **Analysis Recommendations** — Suggests repo_analyze for large codebases
4. **VCS Setup Guidance** — Git initialization commands for new repos
5. **Health Monitoring** — Recommended workflow for ongoing maintenance

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_409 | 409 | Path already exists (create_new=true) |
| REP_409 | 409 | Repository already indexed (force=false) |
| REP_404 | 404 | Path does not exist (create_new=false, no remote_url) |
| REP_TIMEOUT | 408 | Git clone or SVN checkout timed out |
| REP_CLONE | 400 | Git clone failed |
| REP_CHECKOUT | 400 | SVN checkout failed |

## Usage Examples

```json
// Clone a remote repo with audit
{
  "tool": "repo_init",
  "repo_path": "/project",
  "remote_url": "https://github.com/user/repo.git"
}

// Initialize local directory as git repo
{
  "tool": "repo_init",
  "repo_path": "/local/project",
  "vcs_type": "git"
}

// Index without VCS
{
  "tool": "repo_init",
  "repo_path": "/local/folder",
  "vcs_type": "none",
  "create_new": true
}

// Re-index existing repo
{
  "tool": "repo_init",
  "repo_path": "/project",
  "force": true
}

// Clone without audit
{
  "tool": "repo_init",
  "repo_path": "/project",
  "remote_url": "https://github.com/user/repo.git",
  "run_audit": false
}
```

## Integration

- **repo_analyze** — For full semantic analysis after initialization
- **repo_audit** — For security scan (if run_audit=false during init)
- **repo_staleness** — For checking VCS sync status
- **repo_sync** — For incremental updates after code changes
