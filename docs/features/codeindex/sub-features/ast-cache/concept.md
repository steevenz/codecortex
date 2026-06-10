# AST Cache

> **Source:** `src/core/ast_cache.py` -> `AstCache` (LRU singleton via `get_ast_cache()`)

## Concept

The AST Cache prevents re-parsing files whose content hasn't changed. Given that LLM-aided development often involves editing the same files repeatedly, this dramatically accelerates incremental indexing.

## How It Works

```
File read ---> content string ---> SHA-256 hash ---> Cache lookup
                                                        |
                                              +---------+---------+
                                              v                    v
                                          Cache hit            Cache miss
                                              |                    |
                                         Return cached        Parse with
                                         AST (parsed dict)    Tree-Sitter
                                                                   |
                                                             Store in cache
                                                             (key: file_rel_path)
```

## Key Design

| Aspect | Implementation |
|--------|---------------|
| **Key** | `file_rel_path` (relative path string) |
| **Cache Invalidation** | Content hash comparison -- `ast_cache.get(file_rel_path, content)` |
| **Value** | Parsed dict (the full TreeSitterParser output) |
| **Eviction** | LRU (Least Recently Used) -- fixed max size |
| **Thread-safety** | Thread-safe for concurrent reads during WorkerPool parallelization |
| **Singleton** | `get_ast_cache()` returns module-level singleton instance |

## Usage in Pipeline

```python
# service.py -- _process_file()
content = await asyncio.to_thread(lambda: file_path.read_text(encoding="utf-8", errors="ignore"))
ast_cache = get_ast_cache()
cached = ast_cache.get(file_rel_path, content)
if cached is not None:
    parsed = cached              # Skip parse, use cached result
else:
    parsed = await self._parse_with_timeout(parser, file_path, ...)
    ast_cache.set(file_rel_path, content, parsed)  # Store for next time
```

## When It Helps Most

- **Re-indexing** the same repo after small changes
- **`code_index(action="files")`** -- indexing specific files that may overlap with previous runs
- **Single-file re-index** via `index_file_with_tree_sitter()` -- adjacent files may still be cached
- **CI/CD pipelines** where the same commit is indexed multiple times
