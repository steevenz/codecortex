# Impact Analysis Example

Analyze blast radius before a destructive change.

## Request

```json
{
  "repo_id": "uuid-1234",
  "action": "impact",
  "target_symbol": "src/models/user.py::User"
}
```

## Response

```json
{
  "success": true,
  "status_code": 200,
  "data": {
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
}
```
