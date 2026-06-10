# Rename Example

Rename a function across the codebase.

## Request

```json
{
  "repo_id": "uuid-1234",
  "action": "rename",
  "target_symbol": "src/utils.py::calculate_sum",
  "changes": {"new_name": "calculate_total"},
  "dry_run": true
}
```

## Response

```json
{
  "success": true,
  "status_code": 200,
  "data": {
    "status": "preview",
    "message": "Rename plan: 3 file(s)",
    "changes": [
      {
        "path": "src/utils.py",
        "action": "modify",
        "description": "Rename 'calculate_sum' → 'calculate_total'",
        "diff": "--- a/src/utils.py\n+++ b/src/utils.py\n@@ -10,7 +10,7 @@\n-def calculate_sum(a, b):\n+def calculate_total(a, b):\n     return a + b"
      }
    ],
    "blast_radius": {
      "total_files": 3,
      "direct_dependents": 3,
      "confidence_score": 100
    }
  }
}
```
