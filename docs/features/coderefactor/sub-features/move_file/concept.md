# Move File

> **Sub-Feature:** Move File
> **Action:** `move_file`
> **Rating:** 5/5 (Essential) ⭐⭐⭐⭐⭐

## Purpose

Move a file to another directory (cross-domain) with import path recalculation, multi-language import updates, and blast radius analysis.

## Why This Exists

- **Cross-Domain Moves:** AI can move files between domains without manual tracking
- **Import Recalculation:** Automatic recalculation of relative import paths
- **Blast Radius:** Full impact analysis before file move
- **Multi-Language:** Supports Python, JS/TS, Go, PHP, Rust

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_id` | string | ✅ | — | Repository UUID |
| `source_path` | string | ✅ | — | Current file path |
| `changes.target_dir` | string | ✅ | — | Target directory |
| `changes.delete_source` | bool | ❌ | `false` | Delete source after move |
| `dry_run` | bool | ❌ | `true` | Preview without applying |

## Output

```json
{
  "status": "preview",
  "message": "Move plan: 5 change(s)",
  "changes": [
    {
      "path": "src/utils/processor.py",
      "action": "rename",
      "description": "Move src/utils/processor.py -> src/payment/processor.py"
    },
    {
      "path": "src/handler.py",
      "action": "modify",
      "description": "Update import to src/payment/processor.py"
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
2. Create target directory if needed
3. Copy (or move) file to new location
4. Find ALL importers via DB content search
5. Rewrite all import paths (recalculate relative paths)
6. Git commit
7. Auto DB reindex

## Use Case

AI agents can reorganize file structure by moving files between domains with automatic import path recalculation.
