# Impact Analysis

> **Source:** `CodeRefactorService.analyze_refactor_impact()`

## Concept

Impact analysis predicts the **blast radius** of renaming or modifying a symbol: all affected files, call sites, import sites, and breaking changes. Essential for large codebases where a single rename could touch dozens of files.

## Output

```json
{
  "symbol": "process_payment",
  "type": "function",
  "file": "src/domain/payments/service.py:42",
  "impact_score": 0.85,
  "total_references": 12,
  "affected_files": [
    {"path": "src/api/checkout.py", "references": 3, "lines": [15, 22, 45]},
    {"path": "src/domain/orders/handler.py", "references": 2, "lines": [78, 90]},
    {"path": "src/domain/payments/retry.py", "references": 1, "lines": [55]}
  ],
  "breaking_changes": [
    {"file": "src/api/checkout.py", "line": 15, "description": "Public API export"}
  ],
  "risk_level": "high"
}
```

## Risk Levels

| Score | Level | Meaning |
|-------|-------|---------|
| 0-0.3 | Low | Internal symbol, few references |
| 0.3-0.6 | Medium | Multiple references, single module |
| 0.6-0.9 | High | Cross-module, public API, many references |
| 0.9-1.0 | Critical | Exported public interface, many dependents |
