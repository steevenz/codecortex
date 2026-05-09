# CodeRefactor: Code Transformation

> **Domain:** CodeRefactor
> **Package:** `src/domain/coderefactor/`

## Concept

CodeRefactor provides safe, semantic code transformations. Unlike simple search-and-replace, refactoring operations understand code structure (via Tree-Sitter) and can rename symbols across multiple files while respecting scope boundaries.

## MCP Tools

| Tool | Function |
|------|----------|
| `search_code` | Text/regex search across indexed files (DB cache, not disk) |
| `search_replace` | Global find and replace (regex supported) |
| `refactor_symbol` | Semantic rename or move of a code element |
| `refactor_impact` | Predict blast radius of renaming/modifying a symbol |
| `refactor_apply` | Apply a predefined refactoring recipe |
| `refactor_rename` | Multi-file coordinated rename via Knowledge Graph |

## Safety

- **Dry-run first:** Every destructive operation defaults to `dry_run=True`
- **Impact preview:** `refactor_impact` shows all affected files before changes
- **Tree-Sitter semantic analysis:** Renames skip strings and comments to avoid false positives
- **Git integration:** Applied changes are auto-committed with descriptive messages

## Flow

```
refactor_rename(path, old_name, new_name, dry_run=True)
    │
    ▼
  refactor_impact ──> Find all references via Knowledge Graph
    │
    ▼
  Preview: [file1.py:42, file2.ts:15, ...]
    │
    ▼
  dry_run=False ──> Apply changes ──> git commit
```

## Sub-Features

- [Symbol Rename](sub-features/symbol-rename/concept.md)
- [Impact Analysis](sub-features/impact-analysis/concept.md)
- [Refactoring Recipes](sub-features/refactoring-recipes/recipes.md)
