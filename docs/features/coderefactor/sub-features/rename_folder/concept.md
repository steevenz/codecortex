# Rename Folder

> **Sub-Feature:** Rename Folder
> **Action:** `rename_folder`
> **Rating:** 5/5 (Essential) ⭐⭐⭐⭐⭐

## Purpose

Rename a directory and batch-update all imports for every file inside with per-file blast radius analysis and multi-language import updates.

## Why This Exists

- **Module Reorganization:** AI can reorganize module structure without manual tracking
- **Batch Import Updates:** Updates all imports for every file in the directory
- **Per-File Blast Radius:** Full impact analysis for each file
- **Nested Import Detection:** Handles complex directory renames

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_id` | string | ✅ | — | Repository UUID |
| `source_path` | string | ✅ | — | Current directory path |
| `changes.new_name` | string | ✅ | — | New directory name |
| `dry_run` | bool | ❌ | `true` | Preview without applying |

## Output

```json
{
  "status": "preview",
  "message": "Folder rename: 15 change(s), 20 files, risk=medium, 8 importers affected",
  "changes": [
    {
      "path": "src/old_folder",
      "action": "rename",
      "description": "Rename directory src/old_folder -> src/new_folder"
    },
    {
      "path": "src/handler.py",
      "action": "modify",
      "description": "Update imports for src/old_folder/ -> src/new_folder/"
    }
  ],
  "blast_radius": {
    "total_files": 8,
    "direct_dependents": 8,
    "confidence_score": 70
  }
}
```

## Safety

Warns if directory contains >50 files to prevent large-scale unintended changes.

## Algorithm

1. Validate directory exists
2. Walk all files recursively
3. For EACH file: find ALL importers via DB content search
4. Calculate per-file blast radius
5. Batch rename directory on disk
6. Update all import paths for every affected file
7. Git commit
8. Auto DB reindex

## Use Case

AI agents can reorganize module structure by renaming directories with comprehensive impact analysis and batch import updates.
