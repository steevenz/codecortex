# Worker Pool

> **Source:** `src/domain/codeindex/infrastructure/worker_pool.py`

## Concept

The Worker Pool parallelizes file parsing across CPU cores using a `ThreadPoolExecutor`. Since Tree-Sitter parsing is CPU-bound (each file requires a full AST/CST walk), spreading work across cores dramatically reduces indexing time for large repositories.

## Architecture

```
index_repository(repo_id)
    |
    v
  Count code files + total bytes
    |
    +-- total >= 15 files OR total >= 512KB ---> WorkerPool (parallel)
    |                                              |
    |                                  ThreadPoolExecutor(max_workers=cpu_count)
    |                                              |
    |                +-----------------+-----------+-----------+-----------------+
    |                v                 v           v           v                 v
    |            Worker 1          Worker 2    Worker 3    Worker 4         Worker N
    |            parse file        parse file  parse file  parse file       parse file
    |                |                 |           |           |                 |
    |                +-----------------+-----------+-----------+-----------------+
    |                                              |
    |                                              v
    |                                    Aggregate + Enrich + Write (async)
    |                                    _enrich_frameworks -> _write_parsed_to_sqlite
    |
    +-- total < 15 files AND total < 512KB ---> Sequential (async)
                                                   |
                                               asyncio.gather
                                               with semaphore(10)
                                                   |
                                               _process_file() per file
```

## Key Parameters

| Parameter | Value | Why |
|-----------|-------|-----|
| `MIN_FILES_FOR_PARALLEL` | 15 | Overhead of thread pool approx = 15 sequential parses |
| `MIN_BYTES_FOR_PARALLEL` | 512 KB | Small repos parse faster sequentially (no thread overhead) |
| `max_workers` | `os.cpu_count() or 4` | Optimal for CPU-bound parsing |
| `chunk_size` | 50 | Chunked processing (via `map_chunked`) for very large repos |
| `CODECORTEX_MAX_CONCURRENT_INDEXING` | 10 (env var) | Sequential path semaphore limit |

## Sequential vs Parallel Decision

```
if file_count >= 15 OR total_bytes >= 512KB:
    use WorkerPool (ThreadPoolExecutor)
else:
    use asyncio.gather with semaphore(10)
```

The sequential path:
- Avoids thread overhead for small repos
- Uses `asyncio.gather` for concurrent I/O (file reads)
- `asyncio.Semaphore(10)` prevents memory pressure
- Each file processed by `_process_file()` which handles enrichment + SQLite write

The WorkerPool path:
- CPU-bound parsing dispatched to threads
- Results collected, then enrichment + SQLite write done asynchronously via `asyncio.gather(_write_parsed(...))`

## Error Isolation

- One file failure does not halt the entire index
- Errors are logged via `_log_event("ERROR", "FILE_INDEX_FAILED", ...)`
- Failed files recorded as `insights` with category `lint`
- Worker pool catches exceptions per-item in `_parse_single()`

## Critical Fix: Missing SQLite Write

Previously, the WorkerPool path parsed files but **never wrote to SQLite** -- symbols were collected in memory (`parsed_files`) but never persisted. This was fixed by adding `_enrich_frameworks` + `_write_parsed_to_sqlite` in the post-pool async step.

## Fix: Parser Cache Thread Safety

The `_parser_cache` dictionary had a race condition when multiple WorkerPool threads initialized parsers concurrently. Added `threading.Lock` to ensure parser instances are created exactly once. The lock wraps the `tree_sitter_manager.get_language_safe()` call so that concurrent workers do not double-create or corrupt parser instances.
