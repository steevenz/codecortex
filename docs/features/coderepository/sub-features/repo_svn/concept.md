# repo_svn: Arbitrary SVN Operations

> **Tool:** repo_svn
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Execute arbitrary Subversion (SVN) operations (checkout, update, commit, add, status, log, diff, info, revert, cleanup, lock, unlock, propset, resolve, merge, switch, etc.) with structured output and dry-run support. Wraps DiskSvn from filesystem infrastructure.

## Why This Exists

- **SVN Flexibility:** Execute any svn subcommand without hardcoding
- **Dry-Run Safety:** Preview svn commands before execution
- **Structured Output:** Parsed svn output for AI consumption
- **Command Reconstruction:** Reconstructs commands from parameters for user confirmation
- **AI Actions:** Context-aware recommendations for svn workflows

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `target` | string | ✅ | — | URL (for checkout) or local working copy path |
| `subcommand` | string | ✅ | — | SVN subcommand (e.g., "status", "commit") |
| `args` | list | ❌ | — | Positional arguments |
| `flags` | dict | ❌ | — | Flags as dict (e.g., {"--verbose": true}) |
| `dry_run` | bool | ❌ | `false` | Simulate without executing |
| `timeout_seconds` | int | ❌ | `300` | Timeout for long operations |

## Output

```json
{
  "target": "/absolute/path",
  "subcommand": "status",
  "success": true,
  "output": {
    "revision": "12345",
    "changed_files": ["src/main.py"]
  },
  "ai_action": "Would execute: svn status. Remove dry_run=true to apply.",
  "preview": {
    "command": "svn status",
    "target": "/absolute/path",
    "estimated_impact": "read-only operation"
  }
}
```

## AI Actions

1. **Dry-Run Preview** — Command reconstruction with preview object
2. **Operation Summary** — SVN operation result interpretation
3. **Next Steps** — Suggests follow-up svn operations
4. **Workflow Guidance** — Recommended svn command sequences

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_SVN_400 | 400 | SVN operation failed |
| REP_SVN_408 | 408 | SVN operation timed out |
| REP_SVN_500 | 500 | Internal error |

## Integration

- **repo_init** — For svn checkout during setup
- **repo_staleness** — For svn status checking
- **repo_history** — For commit history retrieval
