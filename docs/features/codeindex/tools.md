# CodeIndex: MCP Tools

> **Source:** `src/domain/codeindex/api/tools.py`

## Tool Reference

### `index_repo`

Full semantic indexing of all code files in a repository.

```
Parameters:
  repo_id (str)        — Repository UUID from repo_init
  include_codemap (bool) — If True, returns structured symbol map (default: False)

Returns:
  repository_id, optional codemap

When to use:
  After repo_init to populate the symbol index.
  Required before graph_find_symbols, graph_query, or semantic_search.
```

**Example response:**
```json
{
  "success": true,
  "message": "Successfully indexed repository: abc-123",
  "data": {
    "repository_id": "abc-123",
    "codemap": { "src/domain/": [{"name": "service.py", "symbols": [...]}] }
  }
}
```

---

### `index_file`

Re-index a single file after a code change. Faster than full `index_repo`.

```
Parameters:
  repo_id (str)   — Repository UUID
  file_id (str)   — File UUID (obtain via fs_tree or fs_glob)

Returns:
  file_id, symbol_count

When to use:
  After editing a single file. Avoids full re-index.
```

---

### `semantic_search`

Natural language search across the codebase using vector embeddings.

```
Parameters:
  repo_id (str)  — Repository UUID
  query (str)    — Natural language query (e.g. "authentication logic")
  top_k (int)    — Max results (default: 10, max: 50)

Returns:
  List of matched chunks with similarity scores

When to use:
  Finding code by concept rather than exact name.
  Requires index_repo to have been run first.
```

---

## Tool Count

| Domain | Tool Count |
|--------|-----------|
| CodeIndex | 3 (index_repo, index_file, semantic_search) |
| Total (all domains) | 31+ MCP tools |
