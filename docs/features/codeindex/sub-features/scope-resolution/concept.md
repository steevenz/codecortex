# Scope Resolution

> **Source:** `src/domain/codeindex/infrastructure/scope_resolution.py`

## Concept

Scope resolution is the pipeline that determines **which declaration a name reference resolves to**. In a codebase with multiple files, nested classes, and complex imports, this is non-trivial.

## The Challenge

```python
# file_a.py
from file_b import process

class Service:
    def run(self):
        process(data)  # Which 'process' is this?
```

The answer depends on: what's exported from `file_b`, whether there are wildcard imports, if `process` is shadowed by a local definition, etc.

## Implementation (3-Pass Pipeline)

| Pass | Phase | What It Does |
|------|-------|-------------|
| 0 | **Symbol Extraction** | `_parsed_to_symbols()` converts flat tree-sitter output (classes/functions/variables keys) into hierarchical symbol list with class->method nesting |
| 1 | **Scope Tree Building** | `ScopeExtractor.build_scope_tree()` creates a `ScopeTree` per file -- module -> class -> function hierarchy |
| 2 | **Reference Resolution** | `ReferenceResolver.resolve_all()` -- 3 sub-passes: local scope -> import resolution -> global index |

### Pass 0: Tree-Sitter -> Hierarchical Symbols

The tree-sitter parsers output flat lists (`classes: [], functions: [], variables: []`). `_parsed_to_symbols()` converts these into a hierarchical structure:

```
Input (flat):
  classes: [{name: "Calculator", line_number: 1}]
  functions: [{name: "add", line_number: 5, class_context: "Calculator"},
              {name: "run", line_number: 10}]

Output (hierarchical):
  [{type: "class", name: "Calculator", children: [
      {type: "method", name: "add"}
   ]},
   {type: "function", name: "run"}]
```

### Critical Fix: Dead Scope Resolution

Previously, `ScopeExtractor` used `parsed.get("symbols", [])` but tree-sitter parsers output `classes`/`functions` keys, not `symbols`. This meant scope resolution was always a no-op -- it never found any symbols to build a scope tree from. Fixed by implementing `_parsed_to_symbols()` converter that reads the standard `classes[]`/`functions[]`/`variables[]` keys and builds the hierarchical structure.

### Pass 1: Scope Tree Building

```
                        MODULE ("file_a")
                      /                 \
              CLASS ("Calculator")    FUNCTION ("run")
                 /
          METHOD ("add")
```

Each `ScopeNode` tracks:
- `symbols`: maps name -> `[def_id]` for local lookup
- `children`: nested scope IDs
- `parent_id`: parent scope ID

### Pass 2: Reference Resolution (3 Sub-Passes)

```
Reference: process(data) at line 6

Pass 1: Local scope
  +- Check file_a's scope tree for "process" -> Not found, skip

Pass 2: Import resolution
  +- Check file_a imports -> "from file_b import process"
  +- Found! -> resolved_def_id = "file_b::process", confidence = 0.8

Pass 3: Global index
  +- Not needed (Pass 2 already resolved)
```

## Data Structures

| Class | Role |
|-------|------|
| `ScopeNode` | A single scope in the hierarchy (module/class/function/block) |
| `SymbolDef` | A symbol definition with `full_name` (dot-qualified) |
| `Reference` | A usage site with `resolved_def_id` + `confidence` + `evidence` list |
| `ScopeTree` | Per-file scope tree with name lookup up the parent chain |
| `WorkspaceIndex` | Cross-file index: global symbol index, import map, export index |
| `ScopeExtractor` | Builds `ScopeTree` from parsed data (uses `_parsed_to_symbols()`) |
| `ReferenceResolver` | Multi-pass reference resolver with confidence scoring |

## Scope Kinds

| Kind | Example | Symbol Nesting |
|------|---------|----------------|
| MODULE | Top-level of a file | Root scope |
| CLASS | `class User:` | Contains method symbols |
| FUNCTION | `def process():` | Contains nested symbols |

## Integration with Indexing Pipeline

1. `build_workspace_index()` called after all files parsed
2. `ScopeExtractor._parsed_to_symbols()` converts flat parsed data using `class_context` from parsers (all 19 dedicated + 6 generic have class_context support)
3. `ScopeExtractor.build_scope_tree()` creates the tree
4. `resolve_workspace_references()` logs stats: `{total_references, resolved, unresolved, resolution_rate}`
5. Unresolved references stored as `insights` with category `lint`
