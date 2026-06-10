# CodeIndex: LLM Impact

> How CodeIndex enriches LLM code understanding via structured symbol data

## Before CodeIndex

An LLM with only file content can:
- Read individual files sequentially
- Guess at cross-file relationships
- Miss symbols defined in other files
- Not know which functions call which, or which classes inherit from what

## After CodeIndex

The LLM gains structured knowledge:

1. **Symbol Registry** -- All functions, classes, methods, and variables with exact locations (`start_line`, `end_line`), signatures, and docstrings. Docstrings are extracted via JSDoc comment walking (JS/TS/TSX), Python `ast.get_docstring()`, and tree-sitter comment adjacency for all other languages. No more guessing where a symbol is defined or what it does.

2. **Class Hierarchy** -- `symbols.parent_id` FK chain allows walking from class -> methods. INHERITS edges connect each method to its parent class. CLASS_INHERITS edges connect each class to its base classes (e.g., `class A extends B` -> A INHERITS B). Scope resolution builds `ScopeTree` (module -> class -> function -> block) for any file.

3. **Call Graph** -- `edges` table with `relation_type='CALLS'` connects callers to callees across files. Edge weight tracks call frequency. Combined with INHERITS edges, the LLM can trace method dispatch through inheritance chains.

4. **Import Graph** -- `edges` table with `relation_type='IMPORTS'` connects files to the symbols they import. The `__file__` sentinel symbols store file-level imports in metadata JSON. Scope resolution's `WorkspaceIndex` maps imported names to target files. Together these give the LLM a complete dependency graph.

5. **Framework Awareness** -- Framework detection tags symbols with their framework context (React component, FastAPI route, Flutter widget, etc.). Framework tags are stored in symbol metadata and are queryable via `code_search`.

6. **Type Information** -- Signatures, docstrings, decorators, and generics are preserved in `signature` and `metadata` columns. JSDoc for TypeScript/TSX provides additional type context from `@param`, `@returns`, `@type` tags.

## Concrete Improvements

| Capability | Without CodeIndex | With CodeIndex |
|-----------|------------------|----------------|
| Find function definition | Grep entire codebase | SQL query on `symbols` table |
| Find all callers | Manual grep | `edges` table query (source_id -> target_id) with CALLS relation |
| Understand inheritance | Read all parent classes manually | `symbols.parent_id` chain + INHERITS + CLASS_INHERITS edges |
| Trace call chain | Manual file-by-file | `edges` graph walk across CALLS + INHERITS edges |
| Find imports of a file | Read file headers | IMPORTS edge query on `edges` table |
| Refactor safety | Guess impact zone | Impact analysis via call graph + inheritance graph |
| Code generation context | Limited to open files | Full symbol registry via `code_search` with docstrings |
| Know if a function is a route | Read decorators from source | Framework tag in enriched metadata |
| Understand method dispatch | Manual class hierarchy reading | INHERITS edges + CLASS_INHERITS edges in a single query |
