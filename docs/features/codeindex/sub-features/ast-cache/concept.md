# AST Cache

> **Source:** LRU cache integrated into `TreeSitterManager`

## Concept

The AST Cache prevents re-parsing files whose content hasn't changed. Given that LLM-aided development often involves editing the same files repeatedly, this dramatically accelerates incremental indexing.

## How It Works

```
File read ──> SHA-256 hash ──> Cache lookup
                                    │
                          ┌─────────┴─────────┐
                          ▼                    ▼
                      Cache hit            Cache miss
                          │                    │
                     Return cached        Parse with
                     AST immediately       Tree-Sitter
                                            │
                                      Store in cache
                                      (keyed by hash)
```

- **Key:** SHA-256 content hash
- **Value:** Serialized AST node tree
- **Eviction:** LRU (Least Recently Used) — oldest entries dropped when cache is full
- **Size:** Configurable (default: 1000 files)
- **Thread-safe:** Concurrent reads during worker pool parallelization
