# AST Cache

**Domain:** CodeIndexing  
**Effort:** Low | **Impact:** Medium | **Priority:** 6

## Current State
CodeCortex parses every file with TreeSitter on every `index_repo` run. No caching means:
- Full re-parse even when files haven't changed
- High CPU usage on re-index
- Slow incremental updates

## Proposed Improvement
Implement an in-memory AST cache with invalidation via content_hash:
1. **Cache key**: `(file_path, content_hash)` — only re-parse when hash changes
2. **Storage**: LRU dict (max 1000 entries) in-memory
3. **Integration**: Wire into `TreeSitterManager` and `CodeIndexService`
4. **Persistence**: Optional via SQLite blob (for large projects)

## Architecture
```
class ASTCache:
    cache: OrderedDict[str, tuple[str, ParsedTree]]  # LRU, max 1000

    get(file_path, content_hash) → ParsedTree | None
    set(file_path, content_hash, tree) → void
    invalidate(file_path) → void
    clear() → void
```

## Key Changes in CodeCortex
- **`src/domain/codeindex/infrastructure/`**: New `ast_cache.py`  
- **Edit `tree_sitter_manager.py`**: Wrap parse with cache check  
- **Edit `index_service.py`**: Wire cache into indexing pipeline

## Dependencies
- Pure Python (collections.OrderedDict or cachetools)

## Effort Breakdown
- `ast_cache.py`: ~60 lines  
- Edit `tree_sitter_manager.py`: ~30 lines  
- Tests: ~40 lines  
- **Total: ~2 hours**
