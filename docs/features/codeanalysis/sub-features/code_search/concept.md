# Code Search Tool

**Tool:** `code_search`  
**Category:** Code Search  
**Domain:** CodeAnalysis  
**Version:** 2.0.0  
**AI Coder Impact:** 10/10 ⭐

---

## Overview

The `code_search` tool provides multi-layer code search combining full-text search, semantic embedding similarity, and graph relationship traversal. It supports five search strategies for different use cases.

## Search Types

| Type | Description | Use Case |
|------|-------------|----------|
| `multi` | Multi-layer: FTS + optional semantic + graph | Default, comprehensive search |
| `symbol` | Exact symbol name matching | Find specific class/function |
| `regex` | Regex pattern matching | Pattern-based code search |
| `semantic` | Embedding similarity | Find related concepts |
| `graph` | Graph relationship traversal | Trace relationships |

## Capabilities

### Search Layers

1. **FTS5 Text Search** (always active in multi mode)
   - Fast symbol name matching
   - SQLite FTS5 indexing
   - Case-insensitive by default

2. **Semantic Enrichment** (optional)
   - Sentence-transformers embeddings
   - Concept similarity matching
   - Language-agnostic

3. **Graph Enrichment** (optional)
   - Relationship discovery
   - Calls, inherits, imports
   - Multi-hop traversal

### Key Features

- **5 Search Types** — Different strategies for different needs
- **Smart Caching** — Query hash-based cache with 5-minute TTL
- **Pagination** — Cursor-based pagination for large result sets
- **Repo Scoping** - Limit search to specific repository
- **File Pattern Filtering** - Glob-based file filtering
- **Content Inclusion** - Include code snippets in results

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query string |
| `search_type` | string | No | "multi" | Search type: multi, symbol, regex, semantic, graph |
| `limit` | int | No | 50 | Max results per layer (max 200) |
| `cursor` | int | No | - | Pagination cursor |
| `repo_id` | string | No | - | Repository UUID for scope |
| `file_pattern` | string | No | "*" | Glob filter for files |
| `include_content` | bool | No | false | Include code snippets in results |
| `semantic` | bool | No | false | Enable semantic embedding enrichment |
| `graph` | bool | No | false | Enable graph relationship enrichment |
| `graph_relations` | string[] | No | ["calls", "inherits", "imports"] | Relation types to include |

## Output

### Result Structure

```json
{
  "total_matches": 42,
  "total_semantic": 15,
  "total_relationships": 8,
  "matches": [
    {
      "symbol": "PaymentProcessor",
      "kind": "class",
      "file": "src/payment/processor.py",
      "line": 15,
      "signature": "class PaymentProcessor(ABC):",
      "docstring": "Processes payment transactions",
      "confidence": 1.0,
      "repo_id": "uuid"
    }
  ],
  "semantic_hits": [
    {
      "symbol": "TransactionValidator",
      "similarity": 0.85,
      "file": "src/payment/validator.py"
    }
  ],
  "relationships": [
    {
      "from": "PaymentProcessor",
      "to": "validate",
      "relation": "calls",
      "weight": 1.0
    }
  ],
  "next_cursor": null
}
```

## Search Type Details

### Multi Search (Default)

Combines FTS, semantic, and graph layers for comprehensive results.

### Symbol Search

Exact symbol name matching with case-insensitive comparison.

### Regex Search

Pattern-based search with validation and graceful error handling.

```python
# Find all handlers matching pattern
result = code_search(
    query="payment.*handler",
    search_type="regex",
)
```

### Semantic Search

Embedding-based similarity for finding related concepts.

### Graph Search

Relationship traversal for discovering connections between symbols.

## Caching

- **Cache Key** — Query hash + search_type + repo_id
- **TTL** — 5 minutes
- **Invalidation** — Sync metadata for staleness detection

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| CA_010 | high | Query is required |
| CA_011 | high | Invalid search type |
| CA_500 | critical | Internal error |

## Examples

### Basic Search

```python
# Full-text search
result = code_search(query="payment")

# Exact symbol search
result = code_search(query="PaymentProcessor", search_type="symbol")
```

### Regex Search

```python
# Pattern matching
result = code_search(
    query="payment.*handler",
    search_type="regex",
)
```

### Multi-Layer Search

```python
# FTS + semantic + graph
result = code_search(
    query="payment",
    semantic=True,
    graph=True,
    graph_relations=["calls", "inherits"],
)
```

### Repo-Scoped Search

```python
# Search within specific repository
result = code_search(
    query="payment",
    repo_id="repo-uuid",
)
```

## Performance

- **FTS5 Indexing** — Fast full-text search
- **Embedding Cache** — Reuse computed embeddings
- **Graph Traversal** — Optimized with depth limits
- **Pagination** — Cursor-based for large result sets

## Dependencies

- **SQLite FTS5** — Full-text search engine
- **Sentence-Transformers** — Semantic embeddings (optional)
- **Graph Database** — Relationship storage
- **Database** — Symbol and metadata storage

## See Also

- [Analyze Tool](../sub-features/code_analyze/concept.md)
- [Audit Tool](../sub-code_audit/concept.md)
- [Status Tool](../sub-features/code_status/concept.md)
