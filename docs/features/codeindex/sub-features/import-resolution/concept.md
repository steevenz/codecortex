# Import Resolution

> **Source:** Embedded in each language parser (e.g., `python.py:_imports()`) + scope resolution (`scope_resolution.py:WorkspaceIndex`)

## Concept

Import resolution maps import statements to the actual files and symbols they refer to. CodeIndex handles import extraction at three levels:

1. **Parse-level** -- Each language parser extracts import statements as structured data
2. **Cross-file** -- Scope resolution's `WorkspaceIndex.register_import()` connects files via imports
3. **Edge-level** -- `_resolve_edges_sqlite()` creates `IMPORTS` edges from `__file__` symbol metadata, linking files to imported symbols in the `edges` table

## Per-Language Extraction

Each parser's `_imports()` method extracts imports in a uniform schema:

```python
# Output of parser._imports()
[
    {"name": "os", "full_import_name": "os", "line_number": 1, "alias": None, "lang": "python"},
    {"name": "process", "full_import_name": "file_b.process", "line_number": 2, "alias": None, "lang": "python"},
    {"name": "Order", "full_import_name": "models.Order", "line_number": 3, "alias": "Ord", "lang": "python"}
]
```

### Python Import Extraction (tree-sitter)

Tree-sitter query captures `import_statement` and `import_from_statement`:

- `import os` -> `{name: "os", full_import_name: "os"}`
- `from file_b import process` -> `{name: "process", full_import_name: "file_b.process"}`
- `import numpy as np` -> `{name: "np", full_import_name: "numpy", alias: "np"}`

### Python Builtin Fallback

When tree-sitter is unavailable, `_parse_python_builtin()` uses `ast.walk()` (single pass -- was 3x) to extract `ast.Import` and `ast.ImportFrom` nodes with identical output schema.

## Cross-File Import Resolution (Scope Resolution)

The `WorkspaceIndex` (scope_resolution.py) maintains:

| Structure | Maps |
|-----------|------|
| `_global_sym_index` | Symbol name -> [(file_path, def_id)] |
| `_import_map` | File -> {imported_name -> target_file} |
| `_export_index` | File -> [(name, def_id, kind)] |

```
WorkspaceIndex.resolve_name("process", "file_a.py")
    |
    +-- 1. Local scope -> "process" not in file_a's scope tree
    |
    +-- 2. Import map -> file_a imports "process" from "file_b"
    |   +-- target = "file_b", confidence = 0.8
    |
    +-- 3. Global index -> "process" found in file_b.py
        +-- (file_b.py, def_id, 0.6)
```

## Pre-Scan for Graph Sync

Before full indexing, `pre_scan_repository()` runs a lightweight pass:
- Queries all Python files for class/function definitions using tree-sitter
- Builds `imports_map: Dict[str, List[str]]` -- maps symbol name -> file paths
- This feeds into `codegraph_service.write_repository_graph()` for cross-file edge building

## IMPORTS Edge Resolution

In addition to scope resolution, CodeIndex creates **IMPORTS edges** in the `edges` table:

1. Each file's imports are stored in the `__file__` sentinel symbol's metadata JSON
2. `_resolve_edges_sqlite()` reads the `imports` list from metadata
3. For each imported symbol, looks up the target symbol in the global symbol table
4. Creates an edge with `relation_type='IMPORTS'` linking the file symbol to the imported symbol

This enables graph queries like "find all files that import this symbol" without re-parsing.

## Python `__file__` Sentinel

After parsing, file-level imports are stored in the `__file__` sentinel symbol's `metadata` JSON:

```json
{
  "id": "file-symbol-uuid",
  "code": "file_b.py:file:__file__@1",
  "name": "__file__",
  "symbol_type": "file",
  "metadata": "{\"variables\":[],\"function_calls\":[],\"imports\":[{\"name\":\"os\",...}],\"language\":\"python\"}"
}
```

This enables `code_search` to return import information for any file without re-parsing, and powers the IMPORTS edge resolution.
