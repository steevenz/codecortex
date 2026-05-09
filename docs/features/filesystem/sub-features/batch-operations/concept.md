# Batch Operations

> **Source:** `src/domain/filesystem/infrastructure/watcher.py`

## Concept

Batch operations allow executing multiple file operations (create, write, delete, move, copy) in a single MCP call. This reduces round-trips and enables atomic-like semantics.

## Operation Types

| Action | Parameters | Description |
|--------|-----------|-------------|
| `create` | `path` | Create an empty file |
| `write` | `path`, `content` | Write content to a file (overwrites) |
| `delete` | `path` | Delete a file |
| `move` | `path`, `dest` | Move/rename a file |
| `copy` | `path`, `dest` | Copy a file |

## Example

```json
{
  "operations": [
    {"action": "create", "path": "src/new_feature.py"},
    {"action": "write", "path": "src/new_feature.py", "content": "def hello(): pass"},
    {"action": "delete", "path": "src/old_file.py"}
  ],
  "repo_id": "uuid",
  "dry_run": false
}
```
