# Validate Action

**Purpose:** Validate code against extracted constraints from documentation

## Why It Exists

Provides automated compliance checking by comparing extracted constraints (from ADRs, standards docs) against the actual codebase. This bridges the gap between documented rules and code reality, enabling AI coders to ensure constraint compliance during implementation.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be "validate" |
| `repo_path` | string | ✅ | — | Repository path to validate |
| `repo_id` | string | ❌ | `null` | Filter constraints by repository |

## Output Format

```json
{
  "success": true,
  "status_code": 200,
  "message": "Validated 12 constraints",
  "data": {
    "constraints_checked": 12,
    "violations_found": 3,
    "violations": [
      {
        "constraint_id": "abc123",
        "constraint": "Constraint: No direct DB access from Controllers",
        "keywords": ["controller", "database", "access"],
        "source_file": "docs/architecture/adr-001.md",
        "validated": true
      }
    ]
  }
}
```

## Algorithm

1. **Fetch constraints:** Query knowledge store for constraint-type chunks
2. **Extract keywords:** Parse constraint content for domain keywords
3. **Code scanning:** Search codebase for keyword patterns
4. **Violation detection:** Flag code locations that violate constraint keywords
5. **Report generation:** Return structured violation report with source attribution

## Use Case

**Scenario:** Ensure payment service follows documented constraints

**Workflow:**
1. Extract constraints from docs/
2. Run validate against payment service code
3. AI coder receives violation report
4. AI coder fixes violations before merge

## Error Cases

| Error Code | Description |
|------------|-------------|
| KG_006 | repo_path required for validate |
| KG_500 | Internal error |
