# Extract Function

> **Sub-Feature:** Extract Function
> **Action:** `extract_function`
> **Rating:** 5/5 (Essential) ⭐⭐⭐⭐⭐

## Purpose

Extract selected code lines into a new function with variable-scope-aware parameter detection and automatic call insertion.

## Why This Exists

- **Code Organization:** AI can improve code organization by extracting reusable logic
- **Variable Scope Analysis:** Automatically detects variables from outer scope
- **Parameter Detection:** Adds necessary parameters to the new function
- **Call Insertion:** Replaces extracted code with function call

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_id` | string | ✅ | — | Repository UUID |
| `target_symbol` | string | ✅ | — | File containing code to extract |
| `changes.new_name` | string | ✅ | — | Name of new function |
| `changes.start_line` | int | ✅ | — | Start line (1-indexed, inclusive) |
| `changes.end_line` | int | ✅ | — | End line (1-indexed, inclusive) |
| `dry_run` | bool | ❌ | `true` | Preview without applying |

## Output

```json
{
  "status": "preview",
  "message": "Extract plan: 2 change(s)",
  "changes": [
    {
      "path": "src/utils.py",
      "action": "modify",
      "description": "Extract lines 10-20 into validate_input()"
    }
  ]
}
```

## Algorithm

1. Parse file with Tree-Sitter
2. Extract code lines from start_line to end_line
3. Detect variables used in extracted code
4. Detect variables defined in outer scope but used in extracted code
5. Create function with parameters for outer-scope variables
6. Replace extracted code with function call
7. Generate unified diff

## Use Case

AI agents can improve code organization by extracting reusable logic into named functions with automatic parameter detection.
