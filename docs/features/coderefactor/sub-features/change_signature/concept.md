# Change Signature

> **Sub-Feature:** Change Signature
> **Action:** `change_signature`
> **Rating:** 5/5 (Essential) ⭐⭐⭐⭐⭐

## Purpose

Add, remove, or reorder function parameters with full blast radius analysis and multi-language call site updates (Python, JS/TS, Go).

## Why This Exists

- **API Evolution:** AI can evolve function signatures safely
- **Call Site Updates:** Automatic update of all call sites
- **Blast Radius:** Full impact analysis before signature change
- **Multi-Language:** Supports Python, JavaScript, TypeScript, Go

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_id` | string | ✅ | — | Repository UUID |
| `target_symbol` | string | ✅ | — | Function to modify (format: `file::function`) |
| `changes.add_params` | array | ❌ | `[]` | Parameters to add with default values |
| `changes.remove_params` | array | ❌ | `[]` | Parameter names to remove |
| `changes.reorder` | array | ❌ | — | New parameter name order |
| `dry_run` | bool | ❌ | `true` | Preview without applying |

## Output

```json
{
  "status": "preview",
  "message": "Signature change plan: 5 changes, risk=medium, 3 call sites",
  "changes": [
    {
      "path": "src/utils.py",
      "action": "modify",
      "description": "Change signature of calculate"
    },
    {
      "path": "src/handler.py",
      "action": "modify",
      "description": "Update call to calculate"
    }
  ],
  "blast_radius": {
    "total_files": 3,
    "direct_dependents": 3,
    "confidence_score": 85
  }
}
```

## Signature Operations

### Add Parameters
```json
{
  "add_params": [
    {"name": "debug", "default_value": "False"},
    {"name": "timeout", "default_value": "30"}
  ]
}
```

### Remove Parameters
```json
{
  "remove_params": ["verbose", "legacy_param"]
}
```

### Reorder Parameters
```json
{
  "reorder": ["c", "a", "b"]
}
```

## Multi-Language Call Site Updates

| Language | Call Pattern |
|----------|-------------|
| Python | `function_name(args)` |
| JavaScript/TypeScript | `functionName(args)` |
| Go | `functionName(args)` |

## Use Case

AI agents can evolve function signatures (add optional parameters, remove deprecated ones, reorder for clarity) with automatic call site updates across the codebase.
