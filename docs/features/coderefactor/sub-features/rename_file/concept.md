# Rename File

> **Sub-Feature:** Rename File
> **Action:** `rename_file`
> **Rating:** 5/5 (Essential) ⭐⭐⭐⭐⭐

## Purpose

Rename a file and update all import references across the entire codebase with multi-language import updates and blast radius analysis.

## Why This Exists

- **File Organization:** AI can reorganize file structure without manual tracking
- **Import Updates:** Automatic update of all import statements
- **Blast Radius:** Full impact analysis before file rename
- **Multi-Language:** Supports Python, JS/TS, Go, PHP, Rust

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_id` | string | ✅ | — | Repository UUID |
| `source_path` | string | ✅ | — | Current file path |
| `changes.new_path` | string | ✅ | — | New file path |
| `dry_run` | bool | ❌ | `true` | Preview without applying |

## Output

```json
{
  "status": "preview",
  "message": "Rename plan: 5 change(s)",
  "changes": [
    {
      "path": "src/processor.py",
      "action": "rename",
      "description": "Rename src/processor.py -> src/payment_processor.py"
    },
    {
      "path": "src/handler.py",
      "action": "modify",
      "description": "Update import to src/payment_processor.py"
    }
  ],
  "blast_radius": {
    "total_files": 5,
    "direct_dependents": 5,
    "confidence_score": 100
  }
}
```

## Algorithm

1. Validate source file exists
2. Find ALL files that import from it via DB content search
3. Generate unified diff for each importer
4. If dry_run: return preview
5. Rename file on disk
6. Rewrite all import statements with new path
7. Git commit
8. Auto DB reindex

## Use Case

AI agents can reorganize file structure by renaming files with automatic import updates across the codebase.
