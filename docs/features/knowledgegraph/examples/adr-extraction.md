# KnowledgeGraph: Example — Extraction Pipeline

## Input: `docs/architecture/adr-001.md`

```markdown
# ADR-001: Database Access Strategy

## Decision
Use Repository pattern for all database access.

## Constraint
**No direct DB access from Controllers.**

## Risk
**Single point of failure in the UserService** — currently handles both
business logic and data access. Must refactor into separate layers.

## Principle
Modular-first design with loose coupling.
```

## CLI Extraction

```bash
codecortex knowledge extract /path/to/project
```

## Result

```json
{
  "documents_scanned": 1,
  "chunks_extracted": 4,
  "relationships_built": 3,
  "summary": "1 decision, 1 constraint, 1 risk, 1 principle"
}
```

### Extracted Chunks

| Type | Content | Score |
|------|---------|-------|
| **decision** | Use Repository pattern for all database access | 0.70 |
| **constraint** | No direct DB access from Controllers | 0.90 |
| **risk** | Single point of failure in the UserService | 0.80 |
| **principle** | Modular-first design with loose coupling | 0.70 |

### Built Relationships

- **Decision** → introduces → **Constraint**
- **Principle** → refines → **Decision**
- **Risk** → affects → `src/domain/services/user_service.py`

## Query Example

```bash
codecortex knowledge query "how should I implement a new controller"
```

Returns the constraint chunk about "No direct DB access" as the top result,
ensuring the developer (or AI) knows the rule before writing code.
