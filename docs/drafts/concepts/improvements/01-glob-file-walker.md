# Glob-based File Walker

**Domain:** Filesystem  
**Effort:** Low | **Impact:** High | **Priority:** 1

## Current State
CodeCortex uses `os.walk()` in `CodeRepositoryService._discover_recursive()` for file discovery. This is slow on large repos because:
- `os.walk` is single-threaded, pure Python iteration
- Filtering via `.gitignore`/`.codecortexignore` happens after listing, wasting I/O
- No concurrent stat — each file is stat'd sequentially
- Memory: retains all file paths + content in one pass

## Proposed Improvement
Replace `os.walk` with `glob`-based scanning using the `glob` library (via `pathspec` for ignore patterns), matching GitNexus's approach:
1. Phase 1: `glob('**/*', nodir=True, dot=False)` — fast path-only scan
2. Filter via `pathspec.PathSpec` on the glob results (before stat)
3. Batch stat with `asyncio.gather` (concurrency=32)
4. Phase 2: Read content only for code/doc/config files under 1MB

## Architecture
```
walkRepositoryPaths(repo_path)
  ├── createIgnoreFilter() → PathSpec
  ├── glob('**/*', ignore=spec) → [paths]
  ├── batch_stat(paths, concurrency=32) → [(path, size)]
  └── filter_and_sort() → [ScannedFile]
```

## Key Changes in CodeCortex
- **`src/domain/filesystem/`**: New `glob_walker.py` with `walk_repository_paths()` and `batch_stat()`  
- **`src/domain/coderepository/application/service.py`**: Replace `_discover_recursive` with glob-based walker  
- **`src/core/`**: Add `max_file_size_mb` config (default 1MB, was 5MB hardcoded)

## Dependencies
- `glob` (stdlib, Python 3.12+)
- `pathspec` (already in pyproject.toml)
- `asyncio` (already used)

## Effort Breakdown
- `glob_walker.py`: ~80 lines  
- Edit `service.py`: ~30 lines  
- Tests: ~50 lines  
- **Total: ~2 hours**
