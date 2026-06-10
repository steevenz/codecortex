# repo_dump: Full Data Export

> **Tool:** repo_dump
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Full data export — files, symbols, edges, graph, findings, and embeddings. Supports split-by-type format, gzip compression, and dry-run mode for backup and migration.

## Why This Exists

- **Data Portability:** Export repository data for backup or migration
- **Backup Strategy:** Create portable snapshots of indexed data
- **Format Flexibility:** Supports YAML/JSON, split/combined, compressed
- **Dry-Run Safety:** Preview export before writing files
- **AI Actions:** Context-aware recommendations for findings review and restore

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to repository |
| `output_dir` | string | ❌ | — | Output directory (default: <repo_path>/.agents/codecortex) |
| `format` | string | ❌ | `yaml` | "yaml" or "json" |
| `include_findings` | bool | ❌ | `true` | Include audit findings |
| `include_embeddings` | bool | ❌ | `false` | Include vector embeddings (can be very large) |
| `split_by_type` | bool | ❌ | `true` | Split into separate files per data type |
| `compress` | bool | ❌ | `false` | Compress output files with gzip |
| `dry_run` | bool | ❌ | `false` | Simulate without writing files |

## Output

```json
{
  "repo_id": "uuid-v7",
  "repo_path": "/absolute/path",
  "output_dir": "/absolute/path/.agents/codecortex",
  "format": "yaml",
  "split_by_type": true,
  "compress": false,
  "files_created": [
    "manifest.yaml",
    "metadata.yaml",
    "files.yaml",
    "symbols.yaml",
    "edges.yaml"
  ],
  "total_size_bytes": 524288,
  "statistics": {
    "files": 150,
    "symbols": 450,
    "edges": 300,
    "findings": 10,
    "embeddings": 0
  },
  "restore_command": "repo_restore --from /absolute/path/.agents/codecortex",
  "ai_actions": [
    {
      "priority": "info",
      "action": "Successfully exported 910 records (5 files, 512KB).",
      "status": "completed"
    },
    {
      "priority": "medium",
      "action": "Exported 10 findings. Review findings before restoring to new repository.",
      "tip": "Findings may contain security issues that should be addressed before migration."
    }
  ]
}
```

## AI Actions

1. **Export Summary** — Record count, file count, size statistics
2. **Findings Alert** — Warning if findings included for review
3. **Embeddings Note** — Suggestion to include embeddings if needed
4. **Restore Command** — Direct command for importing the dump

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_400 | 400 | Repository not indexed |
| REP_500 | 500 | Export failed |

## Integration

- **repo_restore** — For importing the exported dump
- **repo_compact** — For snapshot export (lighter alternative)
- **repo_cleanup** — For full deletion before re-export
