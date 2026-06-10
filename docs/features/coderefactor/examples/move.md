# Move Example

Move a class to another file with smart placement.

## Request

```json
{
  "repo_id": "uuid-1234",
  "action": "move",
  "target_symbol": "PaymentProcessor",
  "changes": {
    "source_file": "src/utils.py",
    "target_file": "src/payment/processor.py"
  },
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
}
```
