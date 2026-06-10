# Semantic Search

> **Not implemented in CodeIndex domain.**
> Semantic search belongs to the **CodeAnalysis** domain via `code_search(search_type="semantic")`.

## Clarification

CodeIndex focuses on **AST-based symbol indexing** -- functions, classes, variables, imports, and call edges. It does NOT generate or store vector embeddings.

Semantic search (natural language -> code matching via vector embeddings) is handled by:

| Component | Domain | Tool |
|-----------|--------|------|
| Semantic search execution | CodeAnalysis | `code_search(search_type="semantic")` |
| Embedding generation | CodeAnalysis | Internal embedding service |
| Symbol index (source of truth) | **CodeIndex** | `code_index(action="status")` |

CodeIndex provides the **symbol registry** that semantic search queries against. Without CodeIndex indexing a repo first, semantic search has no data to search.

## If You Need

- **Exact name search** -> `code_search(search_type="symbol")` (CodeAnalysis)
- **Regex pattern search** -> `code_search(search_type="regex")` (CodeAnalysis)
- **Natural language query** -> `code_search(search_type="semantic")` (CodeAnalysis)
- **Graph relationship query** -> `graph_query` (CodeGraph)
- **Index management** -> `code_index` (CodeIndex)
