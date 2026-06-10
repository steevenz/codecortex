# Impact Analysis

> **Sub-Feature:** Impact Analysis
> **Action:** `impact`
> **Rating:** 5/5 (Essential) ⭐⭐⭐⭐⭐

## Purpose

Blast radius analysis using the Knowledge Graph — calculates direct + transitive callers, test files, core modules, and risk level before any destructive refactoring operation.

## Why This Exists

- **Safety First:** AI must assess impact before any destructive change
- **Risk Assessment:** Classifies risk level (low/medium/high) based on affected files
- **Transitive Analysis:** BFS traversal for full dependency chain
- **Test Coverage:** Identifies test files affected by the change
- **Confidence Scoring:** Provides confidence score (0–100) for AI decision-making

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_id` | string | ✅ | — | Repository UUID |
| `symbol_name` | string | ✅ | — | Symbol name to analyze |
| `source_file` | string | ✅ | — | File containing the symbol |

## Output

```json
{
  "blast_radius": {
    "total_files": 15,
    "direct_dependents": 8,
    "transitive_dependents": 7,
    "test_files": 3,
    "core_modules": 12,
    "affected_symbols": 42,
    "confidence_score": 85
  },
  "risk_level": "medium",
  "summary": "Symbol 'User' affects 15 file(s) (8 direct, 7 transitive).",
  "recommendation": "Review each affected file before applying."
}
```

## Risk Levels

| Total Files | Risk Level | Recommendation |
|-------------|-----------|----------------|
| 0–3 | low | Safe to apply |
| 4–10 | medium | Review each affected file |
| 11+ | high | Run integration tests, consider incremental refactoring |

## Blast Radius Fields

| Field | Description |
|-------|-------------|
| `total_files` | Total unique files affected (direct + transitive) |
| `direct_dependents` | Files that directly call the symbol |
| `transitive_dependents` | Files that call callers (indirect) |
| `test_files` | Test files affected |
| `core_modules` | Non-test files affected |
| `affected_symbols` | Total symbols in affected files |
| `confidence_score` | Confidence in analysis (85 if affected, 100 if not) |

## Algorithm

1. Query Knowledge Graph for direct callers of the symbol
2. BFS traversal for transitive callers (max depth 3)
3. Deduplicate affected files
4. Count test files (contains `/test/`, `/tests/`, or starts with `test_`)
5. Calculate core modules = total - test files
6. Classify risk level based on total files
7. Return recommendation based on risk level

## Use Case

AI agents must call `impact` before any `rename`, `move`, or `change_signature` operation to assess the scope of change and prevent cascading breakage.
