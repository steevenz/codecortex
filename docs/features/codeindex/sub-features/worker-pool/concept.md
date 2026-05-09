# Worker Pool

> **Source:** `src/domain/codeindex/infrastructure/worker_pool.py`

## Concept

The Worker Pool parallelizes file parsing across CPU cores using a `ThreadPoolExecutor`. Since Tree-Sitter parsing is CPU-bound (each file requires a full AST walk), spreading work across cores dramatically reduces indexing time.

## Architecture

```
index_repo(path)
    │
    ▼
  Collect all code files ─────> Worker Pool (n workers)
                                      │
                          ┌───────────┼───────────┐
                          ▼           ▼           ▼
                      Worker 1    Worker 2    Worker N
                      parse file  parse file  parse file
                          │           │           │
                          └───────────┼───────────┘
                                      ▼
                              Aggregate results
                                      │
                                      ▼
                              Write to SQLite
```

- **Pool size:** `min(32, os.cpu_count() + 4)` — auto-scales to available cores
- **Backpressure:** Queue limits prevent memory exhaustion on large repos
- **Error isolation:** One file failure doesn't halt the entire index
- **Progress reporting:** Files indexed count emitted every 100 files
