# Scope Resolution

> **Source:** `src/domain/codeindex/infrastructure/scope_resolution.py`

## Concept

Scope resolution is the multi-pass pipeline that determines **which declaration a name reference resolves to**. In a codebase with multiple files, nested classes, and complex imports, this is non-trivial.

## The Challenge

```python
# file_a.py
from file_b import process

class Service:
    def run(self):
        process(data)  # Which 'process' is this?
```

The answer depends on: what's exported from `file_b`, whether there are wildcard imports, if `process` is shadowed by a local definition, etc.

## Pipeline (6 Passes)

| Pass | Phase | What It Does |
|------|-------|-------------|
| 1 | **Scope Extraction** | Builds scope tree from AST — module → class → function → block |
| 2 | **Import Resolution** | Resolves cross-file imports to specific symbols |
| 3 | **Local Binding** | Matches references to declarations within the same scope |
| 4 | **Cross-File Binding** | Resolves references that cross file boundaries |
| 5 | **Evidence Collection** | Gathers evidence for ambiguous references (type hints, usage patterns) |
| 6 | **Finalize** | Combines evidence to resolve ambiguity |

## Scope Kinds

| Scope Kind | Example |
|-----------|---------|
| MODULE | Top-level of a file |
| NAMESPACE | `package/__init__.py` aggregations |
| CLASS | `class User:` block |
| FUNCTION | `def process():` block |
| BLOCK | `if`, `for`, `with` blocks |
| EXPRESSION | Lambda, list comprehension |
