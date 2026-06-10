# Move

> **Sub-Feature:** Move
> **Action:** `move`
> **Rating:** 5/5 (Essential) ⭐⭐⭐⭐⭐

## Purpose

Move a class or function from source file to target file with smart placement detection, multi-language import updates, and full blast radius analysis.

## Why This Exists

- **Code Organization:** AI can reorganize code structure without manual tracking
- **Smart Placement:** Optimal insertion position based on language patterns
- **Multi-Language Imports:** Updates imports across Python, JS/TS, Go, PHP, Rust
- **Blast Radius:** Full impact analysis before moving

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_id` | string | ✅ | — | Repository UUID |
| `element_name` | string | ✅ | — | Class/function name to move |
| `source_file` | string | ✅ | — | Source file path |
| `target_file` | string | ✅ | — | Target file path |
| `dry_run` | bool | ❌ | `true` | Preview without applying |

## Output

```json
{
  "status": "preview",
  "message": "Move plan: 2 change(s), risk=low, 3 direct dependents",
  "changes": [
    {
      "path": "src/utils.py",
      "action": "modify",
      "description": "Delete PaymentProcessor (L10-50)"
    },
    {
      "path": "src/payment/processor.py",
      "action": "modify",
      "description": "Insert PaymentProcessor at line 5 (smart placement)"
    }
  ],
  "blast_radius": {
    "total_files": 3,
    "direct_dependents": 3,
    "confidence_score": 85
  }
}
```

## Smart Placement Detection

Algorithm for optimal insertion position:
1. Find last import statement using language-specific patterns
2. If no imports, find first class/function definition
3. Insert after imports or before first definition

## Multi-Language Import Updates

| Language | Import Pattern |
|----------|---------------|
| Python | `from module import`, `import module` |
| JavaScript/TypeScript | `import ... from`, `require(...)` |
| Go | `"module/path"` |
| PHP | `use Namespace\Class`, `include/require` |
| Rust | `use module::`, `mod name` |

## Use Case

AI agents can reorganize code structure by moving classes/functions to appropriate files with zero manual tracking of dependencies.
