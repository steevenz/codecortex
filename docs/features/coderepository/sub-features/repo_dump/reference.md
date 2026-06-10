# repo_dump — Ekspor Data Repository ke File Portabel

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-25

## Overview

`repo_dump` exports all CodeCortex data for a repository to portable files (YAML or JSON) at a configurable output directory. Supports split-by-type (separate files per data category), gzip compression, and optional embeddings/findings inclusion.

**Difference from `repo_compact` snapshot**: `repo_compact` creates a compact snapshot primarily for VACUUM metadata. `repo_dump` creates a **full, structured export** suitable for backup, migration, CI/CD artifacts, or committing to the repository as code documentation.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Path of the repository to dump |
| `output_dir` | string | ❌ | `<repo_path>/.agents/codecortex` | Output directory |
| `format` | string | ❌ | `"yaml"` | Format: `"json"` or `"yaml"` |
| `include_findings` | boolean | ❌ | `true` | Include audit findings |
| `include_embeddings` | boolean | ❌ | `false` | Include vector embeddings (can be very large) |
| `split_by_type` | boolean | ❌ | `true` | Split into separate files per data type |
| `compress` | boolean | ❌ | `false` | Compress output files with gzip |
| `dry_run` | boolean | ❌ | `false` | Simulate without writing files |

## 4-Phase Flow

```
PHASE 1: Validate
  • Resolve repo_path → lookup in repositories table
  • Return 400 if not found (suggest repo_analyze first)

PHASE 2: Query data
  • files: id, name, classification, size_bytes, mtime
  • symbols: id, name, symbol_type, start_line, end_line, file_id, signature, docstring
  • edges: id, source_id, target_id, relation_type, line_number, weight
  • graph_nodes / graph_edges (if tables exist)
  • findings + history_findings (if include_findings and tables exist)
  • embeddings (if include_embeddings and table exists)

PHASE 3: Assemble + write
  • Build sections dict: {manifest, metadata, files, symbols, edges, graph, findings, embeddings}
  • If split_by_type: write each section as <section_name>.<ext>
    If not split: write all sections as codecortex.<ext>
  • If compress: gzip each output file
  • If dry_run: return statistics without writing

PHASE 4: Return response
  • files_created: list of relative file paths
  • total_size_bytes: sum of output file sizes
  • statistics: per-category counts
  • restore_command: suggested repo_restore invocation
```

## Output Structure

### Split by type (default)

```
.agents/
└── codecortex/
    ├── manifest.yaml       # version, exported_at, repo_id, repo_path, tool
    ├── metadata.yaml       # full repositories row
    ├── files.yaml          # file listing with classification, size
    ├── symbols.yaml        # all symbols with location, signature, docstring
    ├── edges.yaml          # relationship edges with type, weight
    ├── graph.yaml          # graph nodes + edges (if table exists)
    └── findings.yaml       # audit findings (if include_findings=true)
```

### Single file

```
.agents/
└── codecortex/
    └── codecortex.yaml     # all data combined
```

### Compressed (gzip)

All files get `.gz` extension:
```
.agents/
└── codecortex/
    ├── manifest.yaml.gz
    ├── metadata.yaml.gz
    └── ...
```

## Response

### Success — Split by type, YAML

```json
{
  "success": true,
  "status_code": 200,
  "message": "Repository data exported successfully",
  "data": {
    "repo_id": "f8a3d2e1-...",
    "repo_path": "/home/user/projects/myapp",
    "output_dir": "/home/user/projects/myapp/.agents/codecortex",
    "format": "yaml",
    "split_by_type": true,
    "compress": false,
    "files_created": [
      ".agents/codecortex/manifest.yaml",
      ".agents/codecortex/metadata.yaml",
      ".agents/codecortex/files.yaml",
      ".agents/codecortex/symbols.yaml",
      ".agents/codecortex/edges.yaml",
      ".agents/codecortex/graph.yaml",
      ".agents/codecortex/findings.yaml"
    ],
    "total_size_bytes": 524288,
    "statistics": {
      "files": 187,
      "symbols": 1240,
      "edges": 1987,
      "graph_nodes": 1240,
      "graph_edges": 1987,
      "findings": 12,
      "embeddings": 0
    },
    "restore_command": "repo_restore --from /home/user/projects/myapp/.agents/codecortex"
  }
}
```

### Success — Single file, compressed

```json
{
  "success": true,
  "data": {
    "output_dir": "/home/user/projects/myapp/.agents/codecortex",
    "format": "json",
    "compress": true,
    "files_created": [".agents/codecortex/codecortex.json.gz"],
    "total_size_bytes": 524288,
    "statistics": { "files": 187, "symbols": 1240, "edges": 1987 }
  }
}
```

### Dry run

```json
{
  "success": true,
  "data": {
    "dry_run": true,
    "output_dir": "/home/user/projects/myapp/.agents/codecortex",
    "format": "yaml",
    "split_by_type": true,
    "compress": false,
    "statistics": { "files": 187, "symbols": 1240, "edges": 1987 },
    "would_create": ["manifest", "metadata", "files", "symbols", "edges", "graph", "findings"]
  }
}
```

### Error

```json
{
  "success": false,
  "status_code": 400,
  "message": "Repository not indexed. Run repo_analyze first.",
  "data": { "repo_path": "/home/user/projects/myapp" }
}
```

## Integration

| Tool | Role |
|------|------|
| SQLite | Source of all exported data |
| Filesystem | Creates output directory and writes files |
| `repo_compact` | Compact snapshot (lighter alternative) |
| `repo_restore` | (planned) Import dumped data back |
| `repo_cleanup` | Remove data after backup |
