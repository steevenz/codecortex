# Symbol Rename

> **Source:** `CodeRefactorService.rename_symbol()`

## Concept

Multi-file coordinated rename using the Knowledge Graph. Instead of a simple text replace (which would rename variables in strings, comments, and unrelated namespaces), this uses Tree-Sitter to identify the actual symbol definition and all its references.

## How It Works

1. **Find definition:** Locate the symbol's definition node in the AST
2. **Query Knowledge Graph:** Find all references to this symbol (callers, imports, usages)
3. **Filter scope:** Only rename references within the same scope/namespace
4. **Skip non-code:** Strings, comments, and docstrings are preserved
5. **Apply changes:** File-by-file edit with Git commit

## Example

```python
# Before:
def process_data(items): ...   # rename → calculate_metrics
result = process_data(input)

# After:
def calculate_metrics(items): ...
result = calculate_metrics(input)

# NOT changed (strings, different scope):
description = "how to process_data()"
other_module.process_data(x)
```

## Language Support

Works with all 20+ Tree-Sitter supported languages. Renaming correctly handles:
- Python: module-level, class methods, nested functions
- TypeScript: exported functions, class methods, arrow functions
- Java: static methods, instance methods, constructors
- Go: exported (capitalized) and unexported functions
