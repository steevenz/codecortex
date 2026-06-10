# Inline Function

> **Sub-Feature:** Inline Function
> **Action:** `inline_function`
> **Rating:** 5/5 (Essential) ⭐⭐⭐⭐⭐

## Purpose

Inline a function at all call sites by substituting the function body and removing the definition. Simplifies over-engineered code across the entire codebase.

## Why This Exists

- **Code Simplification:** AI can simplify over-engineered code
- **Call Site Analysis:** Identifies all call sites for substitution
- **Parameter Substitution:** Replaces function calls with body and arguments
- **Definition Removal:** Removes the function definition after inlining

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_id` | string | ✅ | — | Repository UUID |
| `target_symbol` | string | ✅ | — | Function to inline (format: `file::function`) |
| `dry_run` | bool | ❌ | `true` | Preview without applying |

## Output

```json
{
  "status": "preview",
  "message": "Inline plan: 3 change(s)",
  "changes": [
    {
      "path": "src/handler.py",
      "action": "modify",
      "description": "Inline validate_input() at call site"
    },
    {
      "path": "src/utils.py",
      "action": "modify",
      "description": "Remove validate_input() definition"
    }
  ]
}
```

## Algorithm

1. Parse file with Tree-Sitter to find function definition
2. Extract function body and parameter list
3. Find all call sites via Knowledge Graph
4. For each call site:
   - Replace call with function body
   - Substitute parameters with actual arguments
5. Remove function definition from source file
6. Generate unified diff for all changes

## Use Case

AI agents can simplify over-engineered code by inlining small functions that are only called in a few places.
