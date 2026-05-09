# Concurrent File Stat

**Domain:** Filesystem  
**Effort:** Low | **Impact:** Medium | **Priority:** 5

## Current State
CodeCortex stats files sequentially in `_discover_recursive`. For repos with 10K+ files, sequential stat dominates discovery time. Also, content is read eagerly for code files — memory intensive.

## Proposed Improvement
Implement two-phase scanning with concurrent batch stat:
1. **Phase 1 (Path Discovery)**: `glob` or `os.walk` to get paths only (already done)
2. **Phase 2 (Batch Stat)**: Process paths in batches of 32 using `asyncio.to_thread` + `os.stat`
3. **Phase 3 (Content Reading)**: Read content only for files < max_file_size, classification in ('code', 'doc', 'config')
4. **Skip large files**: Log warning and skip

## Architecture
```
batch_stat(paths, concurrency=32)
  ├── chunk paths into batches of 32
  ├── asyncio.gather(*[stat_one(p) for p in batch])
  └── return [ScannedFile(path, size)]

batch_read_content(files, max_size=1MB)
  ├── filter by classification & size
  ├── asyncio.gather(*[read_one(f) for f in batch])
  └── return [(path, content)]
```

## Key Changes in CodeCortex
- **`src/domain/filesystem/infrastructure/`**: New `batch_reader.py`  
- **Edit `service.py`**: Replace sequential stat/read with batch operations  
- **Config**: `CODECORTEX_READ_CONCURRENCY` env var (default 32)

## Dependencies
- Pure Python (asyncio, os, pathlib)

## Effort Breakdown
- `batch_reader.py`: ~80 lines  
- Edit service.py: ~40 lines  
- Tests: ~50 lines  
- **Total: ~2 hours**
