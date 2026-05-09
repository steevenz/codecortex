# Global Registry

> **Source:** `CodeRepositoryService` + `RegistryManager`

## Concept

The global registry (`~/.codecortex/registry.json`) persists repository state across sessions. This allows CodeCortex to know which repositories are indexed, their paths, and how stale they are — even after server restart.

## Registry Entry

```json
{
  "unique-repo-id": {
    "path": "C:/Projects/my-app",
    "remote_url": "https://github.com/user/my-app.git",
    "last_indexed_at": "2026-05-09T03:00:00Z",
    "last_commit": "abc123def456",
    "repo_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Operations

| Operation | Description |
|-----------|-------------|
| `RegistryManager.list_all()` | List all registered repos |
| `RegistryManager.check_staleness(path)` | Check commits_behind HEAD |
| `RegistryManager.remove(path)` | Remove from registry (on cleanup) |
