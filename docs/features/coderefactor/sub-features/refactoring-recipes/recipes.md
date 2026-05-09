# Refactoring Recipes

> **Source:** `CodeRefactorService.apply_refactor_recipe()`

## Concept

Refactoring recipes are predefined, idempotent transformations that bring files to a coding standard. Recipes can be applied to any file.

## Available Recipes

| Recipe | Description |
|--------|-------------|
| `standardize_docstrings` | Normalize all docstrings to a consistent format (Google-style) |
| `add_type_hints` | Add type hints to function signatures (where inferrable) |
| `remove_unused_imports` | Remove imports that have no references in the file |
| `sort_imports` | Organize imports by standard library / third-party / local |

## Execution

```
refactor_apply(path, recipe="add_type_hints", dry_run=True)
    │
    ▼
  Preview changes ──> dry_run=False ──> Apply + git commit
```

All recipes are designed to be **idempotent** — applying twice produces the same result as applying once.
