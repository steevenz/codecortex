# Index Export Example

Demonstrates exporting symbol table as structured JSON for external tooling, auditing, and debugging.

## Basic Export

```python
from src.modules.codeindex.api.tools import code_index

# Export symbol table with default limit (500 symbols)
result = code_index(
    action="export",
    repo_id="abc-123",
)

print(f"Exported {result['data']['symbol_count']} symbols")
print(f"Files: {result['data']['file_count']}")
print(f"Edges: {result['data']['edge_count']}")
print(f"Truncated: {result['data']['truncated']}")
```

**Output:**
```json
{
  "success": true,
  "message": "Exported 500 symbols from repo abc-123",
  "data": {
    "repo_id": "abc-123",
    "symbol_count": 500,
    "file_count": 45,
    "edge_count": 1000,
    "truncated": false,
    "limit_applied": 500,
    "symbols": [
      {
        "id": "sym_001",
        "name": "PaymentProcessor",
        "kind": "class",
        "file": "src/service.py",
        "line_start": 1,
        "line_end": 50,
        "signature": "class PaymentProcessor:",
        "parent_id": null
      }
    ],
    "files": [
      {
        "id": "file_001",
        "path": "src/service.py",
        "language": "python",
        "size_bytes": 2048
      }
    ],
    "edges": [
      {
        "source_id": "sym_002",
        "target_id": "sym_003",
        "relation": "CALLS"
      }
    ]
  }
}
```

## Custom Limit

```python
# Export up to 1000 symbols
result = code_index(
    action="export",
    repo_id="abc-123",
    limit=1000,
)

print(f"Limit Applied: {result['data']['limit_applied']}")
print(f"Truncated: {result['data']['truncated']}")
```

## CLI Export

```bash
# Export to stdout
codecortex ci export --repo-id abc-123

# Export to file with custom limit
codecortex ci export --repo-id abc-123 --limit 1000 --output symbols.json
```

## Use Cases

### External Auditing

```python
# Export for compliance audit
result = code_index(
    action="export",
    repo_id="abc-123",
    limit=5000,
)

# Write to file for external audit tool
import json
with open("audit/symbols.json", "w") as f:
    json.dump(result['data'], f, indent=2)
```

### Debugging

```python
# Export to inspect symbol resolution
result = code_index(
    action="export",
    repo_id="abc-123",
    limit=100,
)

# Check if specific symbol exists
symbol_names = [s['name'] for s in result['data']['symbols']]
if "PaymentProcessor" in symbol_names:
    print("Symbol found in index")
```

### Backup

```python
# Export full symbol table as backup
result = code_index(
    action="export",
    repo_id="abc-123",
    limit=5000,  # Max limit
)

# Store timestamped backup
from datetime import datetime
timestamp = datetime.now().isoformat()
backup_file = f"backups/symbols_{timestamp}.json"

with open(backup_file, "w") as f:
    json.dump(result['data'], f, indent=2)
```

## Error Handling

```python
try:
    result = code_index(
        action="export",
        repo_id="invalid-uuid",
    )
except Exception as e:
    print(f"Error: {e}")
    # Check error code
    if result.get("error_code") == "CI_007":
        print("Missing repo_id")
```
