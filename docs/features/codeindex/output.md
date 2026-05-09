# CodeIndex: Output Data

> **Storage:** SQLite tables via `src/core/database.py`

## Database Tables Produced

| Table | Records Per File | Description |
|-------|-----------------|-------------|
| `files` | 1 row | File metadata (path, size, hash, classification) |
| `directories` | 1+ rows | Directory hierarchy (parent_id for nesting) |
| `symbols` | 5-50+ rows | Functions, classes, variables, imports |
| `edges` | 10-100+ rows | Relationships: CALLS, INHERITS, IMPORTS, USES, DEFINES |
| `manifest_entries` | 1 row | Hash + size for incremental sync tracking |
| `insights` | 0-5 rows | Framework detection results, pattern flags |

## Symbol Data Shape

```json
{
  "id": "uuid-v4",
  "repository_id": "repo-uuid",
  "file_id": "file-uuid",
  "parent_id": null,
  "code": "def process_payment(amount: Decimal) -> bool:",
  "name": "process_payment",
  "symbol_type": "function",
  "start_line": 42,
  "end_line": 67,
  "docstring": "Process a payment transaction.",
  "signature": "(amount: Decimal) -> bool",
  "metadata": "{\"decorators\": [\"@transactional\"], \"async\": false}"
}
```

## Edge Data Shape

```json
{
  "id": "uuid-v4",
  "repository_id": "repo-uuid",
  "source_id": "caller-symbol-uuid",
  "target_id": "callee-symbol-uuid",
  "relation_type": "CALLS",
  "line_number": 55,
  "weight": 1.0
}
```

## Manifest Entry Shape

```json
{
  "id": "uuid-v4",
  "repository_id": "repo-uuid",
  "file_path": "src/domain/service.py",
  "last_hash": "sha256:abc123...",
  "last_size_bytes": 2048,
  "last_mtime": 1712345678.0
}
```
