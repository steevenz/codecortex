# repo_restore — Impor Repository dari Snapshot/Dump

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-25

## Overview

`repo_restore` imports a repository back into the CodeCortex database from a `repo_dump` or `repo_compact` export. Supports split directories (`.agents/codecortex/`), single files, YAML, JSON, and gzipped formats.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `source` | string | ✅ | — | Path to dump file (`.yaml`/`.json`/`.gz`) or split directory |
| `repo_path` | string | ❌ | — | New path for repo (overrides path from dump) |
| `overwrite` | boolean | ❌ | `false` | Replace existing repo data if already in DB |
| `verify_checksum` | boolean | ❌ | `true` | Verify data integrity (plumbing for future checksums) |
| `dry_run` | boolean | ❌ | `false` | Simulate without writing to database |

## Supported Source Formats

| Format | Detection | Examples |
|--------|-----------|----------|
| Split directory | `source.is_dir()` | `.agents/codecortex/` with `manifest.yaml`, `metadata.yaml`, `files.yaml`, etc. |
| Single YAML | `.yaml` / `.yml` | `codecortex.yaml` |
| Single JSON | `.json` | `codecortex.json` |
| Gzipped YAML | `.yaml.gz` / `.yml.gz` | `codecortex.yaml.gz` |
| Gzipped JSON | `.json.gz` | `codecortex.json.gz` |

## 5-Phase Flow

```
PHASE 1: Read and validate source
  • Detect format (split_dir / yaml / json / gz)
  • Load data into unified dict
  • Extract repository metadata

PHASE 2: Check conflicts
  • Look up repo by final_repo_path in database
  • If exists and overwrite=false → 409 conflict
  • If exists and overwrite=true → delete existing data first
  • If dry_run → return restore plan

PHASE 3: Insert data (in transaction)
  • Insert repository record (original or new UUID)
  • Insert directories + files with preserved IDs
  • Insert symbols with file_id references
  • Insert edges with source/target references
  • Insert graph nodes/edges (if tables exist)
  • Insert findings (if table exists)
  • Insert embeddings (if table exists)

PHASE 4: Update metadata
  • Set last_indexed_at = now
  • Register in global registry (~/.codecortex/registry.json)
  • Commit transaction

PHASE 5: Return response
  • restored_records: per-category counts
  • format: detected source format
```

## Response

### Success

```json
{
  "success": true,
  "status_code": 200,
  "message": "Repository restored successfully from dump",
  "data": {
    "repo_id": "f8a3d2e1-...",
    "repo_path": "/home/user/projects/myapp",
    "source": "/home/user/projects/myapp/.agents/codecortex",
    "format": "split_directory",
    "restored_records": {
      "repositories": 1,
      "files": 187,
      "symbols": 1240,
      "edges": 1987,
      "graph_nodes": 1240,
      "graph_edges": 1987,
      "findings": 12,
      "embeddings": 1240
    },
    "overwrite": false
  }
}
```

### Conflict — Already exists

```json
{
  "success": false,
  "status_code": 409,
  "message": "Repository already exists in database. Use overwrite=true to replace.",
  "data": {
    "existing_repo_id": "f8a3d2e1-...",
    "existing_repo_path": "/home/user/projects/myapp"
  }
}
```

### Error — Source not found

```json
{
  "success": false,
  "status_code": 404,
  "message": "Source path does not exist: /path/to/missing",
  "data": { "source": "/path/to/missing" }
}
```

## Section Name Resolution

The loader maps filenames to section keys:
| Filename | Section Key |
|----------|-------------|
| `manifest.yaml` | manifest |
| `metadata.yaml` | metadata |
| `files.yaml` | files |
| `symbols.yaml` | symbols |
| `edges.yaml` | edges |
| `graph.yaml` | graph |
| `findings.yaml` | findings |
| `codecortex.json` | (combined, key-based lookup) |

## Integration

| Tool | Role |
|------|------|
| `repo_dump` | Creates the dump that `repo_restore` reads |
| `repo_compact` | Creates snapshots (compatible subset) |
| SQLite | Target database for restored data |
| RegistryManager | Registers restored repo in global registry |
