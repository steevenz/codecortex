# ORM Dataflow

> **Source:** Integrated into `CodeGraphService`

## Concept

ORM dataflow analysis extracts database models, their fields, relationships, and how they're queried. This bridges the gap between application code and database schema.

## Supported ORMs

| ORM | Framework | Detection |
|-----|-----------|-----------|
| **SQLAlchemy** | Python/FastAPI | `declarative_base()`, `mapped_column()`, `relationship()` |
| **Django ORM** | Python/Django | `models.Model`, `models.ForeignKey`, `models.CharField` |
| **Prisma** | TypeScript/Next.js | `model User { ... }` in schema.prisma |

## Output

```json
{
  "models": [
    {
      "name": "User",
      "file": "src/models/user.py",
      "orm": "sqlalchemy",
      "table": "users",
      "fields": [
        {"name": "id", "type": "Integer", "primary_key": true},
        {"name": "email", "type": "String", "unique": true, "index": true},
        {"name": "password_hash", "type": "String"},
        {"name": "created_at", "type": "DateTime", "default": "now()"}
      ],
      "relationships": [
        {"type": "one_to_many", "target": "Order", "back_populates": "user", "foreign_key": "user_id"}
      ]
    }
  ],
  "queries": [
    {
      "model": "User",
      "operation": "select",
      "function": "find_by_email",
      "file": "src/repositories/user_repo.py:23"
    }
  ]
}
```

---

## Error Codes

| Prefix | Tool | Description |
|--------|------|-------------|
| OD_001 | graph_audit (orm_dataflow) | ORM model extraction failed |
| OD_002 | graph_audit (orm_dataflow) | Query pattern not recognized |

---

## Performance

- **Time Complexity:** O(N) for scanning model files, O(M) for extracting relationships
- **Regex Cost:** Pattern matching is linear in file size, cached per file
- **Memory Usage:** O(M) for storing model metadata
- **Optimization:** Incremental scan based on file modification time
