# repo_git: Arbitrary Git Operations

> **Tool:** repo_git
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Execute arbitrary Git operations (status, commit, push, branch, checkout, merge, etc.) with structured output and dry-run support. Wraps DiskGit from filesystem infrastructure.

## Why This Exists

- **Git Flexibility:** Execute any git subcommand without hardcoding
- **Dry-Run Safety:** Preview git commands before execution
- **Structured Output:** Parsed git output for AI consumption
- **Command Reconstruction:** Reconstructs commands from parameters for user confirmation
- **AI Actions:** Context-aware recommendations for git workflows

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to repository |
| `subcommand` | string | ✅ | — | Git subcommand (e.g., "status", "commit", "push") |
| `args` | list | ❌ | — | Positional arguments |
| `flags` | dict | ❌ | — | Flags as dict (e.g., {"--verbose": true}) |
| `dry_run` | bool | ❌ | `false` | Simulate without executing |

## Output

```json
{
  "repo_path": "/absolute/path",
  "subcommand": "status",
  "success": true,
  "output": {
    "branch": "main",
    "ahead": 0,
    "behind": 5,
    "changed_files": ["src/main.py"]
  },
  "ai_action": "Would execute: git status. Remove dry_run=true to apply.",
  "preview": {
    "command": "git status",
    "target": "/absolute/path",
    "estimated_impact": "read-only operation"
  }
}
```

## AI Actions

1. **Dry-Run Preview** — Command reconstruction with preview object
2. **Operation Summary** — Git operation result interpretation
3. **Next Steps** — Suggests follow-up git operations
4. **Workflow Guidance** — Recommended git command sequences

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_GIT_400 | 400 | Git operation failed |
| REP_GIT_408 | 408 | Git operation timed out |
| REP_GIT_500 | 500 | Internal error |

## Integration

- **repo_init** — For git initialization during setup
- **repo_staleness** — For git status checking
- **repo_history** — For commit history retrieval
