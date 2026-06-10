# repo_restore: Import from Dump

> **Tool:** repo_restore
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Import repository data from dump — reads split directory or single file (yaml/json/gz), optional overwrite, dry-run mode, and auto-ID mapping for migration and backup restoration.

## Why This Exists

- **Data Migration:** Import repository data from backups or other environments
- **Backup Restoration:** Restore from repo_dump exports
- **Format Flexibility:** Supports split directory or single file formats
- **Conflict Resolution:** Handles existing repository with overwrite option
- **Validation:** Verify data integrity before import
- **AI Actions:** Context-aware recommendations for post-restore verification

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `source` | string | ✅ | — | Path to dump file (.yaml/.json/.gz) or directory (split format) |
| `repo_path` | string | ❌ | — | New path for repo (overrides path from dump) |
| `overwrite` | bool | ❌ | `false` | Replace existing repo data if already in DB |
| `verify_checksum` | bool | ❌ | `true` | Verify data integrity (if checksums present) |
| `dry_run` | bool | ❌ | `false` | Simulate without writing to database |

## Output

```json
{
  "repo_id": "uuid-v7",
  "repo_path": "/absolute/path",
  "source": "/backup/codecortex",
  "format": "split_directory",
  "restored_records": {
    "repositories": 1,
    "files": 150,
    "symbols": 450,
    "edges": 300,
    "findings": 10,
    "embeddings": 0
  },
  "overwrite": false,
  "ai_actions": [
    {
      "priority": "info",
      "action": "Successfully restored 910 records to repository '/absolute/path'.",
      "status": "completed"
    },
    {
      "priority": "high",
      "action": "Restored 10 findings from backup. Review security findings immediately.",
      "tip": "Use repo_audit to re-scan and verify findings are still relevant."
    },
    {
      "priority": "info",
      "action": "Repository ready. Run repo_inspect to verify restoration or repo_analyze for full analysis.",
      "next_steps": ["repo_inspect", "repo_analyze", "repo_staleness"]
    }
  ]
}
```

## AI Actions

1. **Restoration Summary** — Record count and status
2. **Findings Alert** — Warning if findings included for security review
3. **Large Repo Alert** — Suggests repo_sync for large repositories
4. **Next Steps** — Recommended verification and analysis tools

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_404 | 404 | Source path does not exist |
| REP_400 | 400 | No valid dump data found |
| REP_400 | 400 | Dump missing repository metadata |
| REP_409 | 409 | Repository already exists (overwrite=false) |
| REP_500 | 500 | Restore failed |

## Integration

- **repo_dump** — For creating the dump to restore
- **repo_inspect** — For verification after restoration
- **repo_sync** — For filesystem alignment after restore
- **repo_audit** — For security review of restored findings
