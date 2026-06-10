# CodeIndex: Output Data

> **Storage:** SQLite tables via `src/core/database.py`

## Database Tables Produced

| Table | Records Per File | Description |
|-------|-----------------|-------------|
| `directories` | 1+ rows | Directory hierarchy (parent_id for nesting) |
| `files` | 1 row | File metadata (path, size, hash, classification) |
| `symbols` | 5-50+ rows | Functions, classes, variables, imports (via `__file__` sentinel) |
| `edges` | 0-200+ rows | 4 relation types: CALLS, INHERITS, CLASS_INHERITS, IMPORTS |
| `insights` | 0-5 rows | Lint insights (syntax errors, unresolved references, index failures) |
| `manifest_entries` | 1 row | Content hash + size + mtime for incremental sync tracking |

## Symbol Data Shape

```json
{
  "id": "uuid-v4",
  "repository_id": "repo-uuid",
  "file_id": "file-uuid",
  "parent_id": "parent-symbol-uuid-or-null",
  "code": "src/domain/service.py:function:process_payment@42",
  "name": "process_payment",
  "symbol_type": "function",
  "start_line": 42,
  "end_line": 67,
  "docstring": "Process a payment transaction.",
  "signature": "(amount)",
  "metadata": "{\"variables\":[],\"function_calls\":[{\"name\":\"validate\"}],\"imports\":[],\"language\":\"python\",\"framework\":\"fastapi\"}"
}
```

### Fields Explained

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Stable symbol identifier |
| `code` | TEXT | `code_ref` format: `{file_rel_path}:{symbol_type}:{qualified_name}@{line}` |
| `parent_id` | UUID or null | Links method -> class, inner -> outer (resolved in 2nd pass) |
| `symbol_type` | TEXT | `file`, `class`, `function`, `method`, `variable` |
| `docstring` | TEXT or null | Extracted docstring via tree-sitter JSDoc (JS/TS/TSX) or Python `ast.get_docstring()` |
| `signature` | TEXT or null | Args list: `"(arg1,arg2)"` for functions/methods; bases for classes |
| `metadata` | JSON | Variables, function_calls, imports, language, framework tags -- preserved for graph sync |

### Docstring Extraction Across Languages

| Language | Extraction Method |
|----------|-----------------|
| Python | `ast.get_docstring()` (module-level) + tree-sitter expression_statement string parent check |
| JavaScript | JSDoc comment from `prev_sibling` walk (`_get_jsdoc_comment()`) |
| TypeScript | JSDoc comment from `prev_sibling` walk (`_get_jsdoc_comment()`) |
| TSX | JSDoc comment from `prev_sibling` walk (`_get_jsdoc_comment()`) |
| Other languages | Docstring from tree-sitter comment nodes adjacent to definitions |

### Method Hierarchy (`parent_id`)

For methods inside classes, the converter sets `parent_id` to the parent class's `code_ref`:

```json
// Class symbol
{ "id": "C_UUID", "code": "x.py:class:Calculator@1", "name": "Calculator", "symbol_type": "class" }

// Method symbol -- parent_id resolved to class UUID in 2nd pass
{ "id": "M_UUID", "code": "x.py:method:Calculator.add@5", "name": "add", "symbol_type": "method", "parent_id": "C_UUID" }
```

## Edge Data Shapes

CodeIndex produces 4 edge types. All edges use a deterministic ID format `{source_id}--{target_id}--{relation_type}`.

### CALLS Edge

```json
{
  "id": "caller-uuid--callee-uuid--CALLS",
  "repository_id": "repo-uuid",
  "source_id": "caller-symbol-uuid",
  "target_id": "callee-symbol-uuid",
  "relation_type": "CALLS",
  "line_number": null,
  "weight": 1.0
}
```

Built from `function_calls` metadata on each function/method. `ON CONFLICT(id) DO UPDATE weight = weight + 1` handles duplicate calls.

### INHERITS Edge (Method -> Class)

```json
{
  "id": "method-uuid--class-uuid--INHERITS",
  "repository_id": "repo-uuid",
  "source_id": "method-symbol-uuid",
  "target_id": "parent-class-uuid",
  "relation_type": "INHERITS",
  "line_number": null,
  "weight": 1.0
}
```

Built from the `parent_id` chain on symbols. If a method has a `parent_id`, an INHERITS edge is created from the method to the parent class.

### CLASS_INHERITS Edge (Class -> Base)

```json
{
  "id": "class-uuid--base-uuid--CLASS_INHERITS",
  "repository_id": "repo-uuid",
  "source_id": "class-symbol-uuid",
  "target_id": "base-class-uuid",
  "relation_type": "CLASS_INHERITS",
  "line_number": null,
  "weight": 1.0
}
```

Built from the class `signature` column, which stores base class names (e.g., `"User(BaseModel)"` -> base is `BaseModel`). Looks up the base class in the symbol table.

### IMPORTS Edge (File -> Import)

```json
{
  "id": "file-uuid--import-uuid--IMPORTS",
  "repository_id": "repo-uuid",
  "source_id": "file-sentinel-uuid",
  "target_id": "imported-symbol-uuid",
  "relation_type": "IMPORTS",
  "line_number": null,
  "weight": 1.0
}
```

Built from the `__file__` sentinel symbol's metadata JSON, which stores the file's imports. Links the file to each symbol it imports.

### Edge Count Estimates

| Repository Size | CALLS Edges | INHERITS Edges | CLASS_INHERITS Edges | IMPORTS Edges | Total |
|----------------|-------------|----------------|---------------------|---------------|-------|
| Small (10 files) | 0-30 | 0-10 | 0-5 | 10-50 | 10-95 |
| Medium (100 files) | 50-500 | 20-100 | 10-50 | 100-500 | 180-1150 |
| Large (1000 files) | 500-5000 | 200-1000 | 100-500 | 1000-5000 | 1800-11500 |

## Compatibility Views

Three SQLite views bridge column name differences between the actual DB schema and codebase queries:

| View | Purpose |
|------|---------|
| `symbols_v` | Aliases `symbol_type` -> `kind`, `start_line` -> `line_start`, `end_line` -> `line_end` |
| `files_v` | Aliases `repository_id` -> `repo_id`, computes `path = relative_path || '/' || name` |
| `edges_v` | Aliases `source_id` -> `from_symbol_id`, `target_id` -> `to_symbol_id`, `relation_type` -> `relation` |

These views fixed CTE recursive SQL queries in `code_searcher.py` that were referencing non-existent column names (`from_symbol_id`, `line_start`, `path`).

## Manifest Entry Shape

```json
{
  "id": "uuid-v4",
  "repository_id": "repo-uuid",
  "file_path": "src/domain/service.py",
  "last_hash": "sha256:abc123...",
  "last_size_bytes": 2048,
  "last_mtime": 1712345678.0,
  "last_processed_at": "2026-05-25 10:30:00"
}
```

## Insight Shapes

```json
// Syntax error
{ "category": "lint", "insight_type": "syntax_error", "metadata": "{\"path\":\"x.py\",\"error\":\"unexpected indent\"}" }

// Parser unavailable
{ "category": "lint", "insight_type": "parser_unavailable", "metadata": "{\"path\":\"x.rs\",\"error\":\"No grammar available for rust\"}" }

// Index failed
{ "category": "lint", "insight_type": "index_failed", "metadata": "{\"path\":\"x.py\",\"error\":\"timeout after 15s\"}" }

// Unresolved references
{ "category": "lint", "insight_type": "unresolved_references", "metadata": "{\"count\":3,\"total\":10}" }
```
