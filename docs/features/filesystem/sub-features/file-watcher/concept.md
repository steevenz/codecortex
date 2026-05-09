# File Watcher

> **Source:** `src/domain/filesystem/infrastructure/watcher.py`

## Concept

The file watcher uses `watchdog` to monitor the filesystem for changes and automatically trigger re-indexing. When a file is modified, created, or deleted, the watcher detects the event and queues the appropriate update.

## How It Works

```
Filesystem event (modify/create/delete)
    │
    ▼
  Watchdog observer ──> Event queue
    │
    ▼
  Debounce (2s) ──> Deduplicate rapid changes
    │
    ▼
  Trigger incremental sync or file update
```

## Events Handled

| Event | Action |
|-------|--------|
| `on_modified` | Re-index changed file |
| `on_created` | Index new file |
| `on_deleted` | Remove from index |
| `on_moved` | Update file path in index |
