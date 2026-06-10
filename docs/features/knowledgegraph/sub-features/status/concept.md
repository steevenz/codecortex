# Status Action

**Purpose:** Show knowledge extraction coverage by type and source

## Why It Exists

Provides visibility into knowledge extraction coverage, enabling assessment of documentation completeness and knowledge balance across types.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be "status" |
| `repo_id` | string | ❌ | `null` | Scope to repository |

## Output Format

```json
{
  "success": true,
  "status_code": 200,
  "message": "Knowledge store: 47 chunks",
  "data": {
    "total_chunks": 47,
    "by_type": {
      "concept": 12,
      "constraint": 8,
      "decision": 6,
      "flow": 5,
      "risk": 4,
      "invariant": 3,
      "anti_pattern": 2,
      "principle": 7
    },
    "sources": [
      "docs/architecture/adr-001.md",
      "docs/architecture/adr-002.md",
      "docs/guides/payment-flow.md",
      "README.md"
    ]
  }
}
```

## Algorithm

1. **Count by Type:** Group chunks by knowledge_type and count (filtered by repo_id if provided)
2. **Count Total:** Sum all chunks
3. **List Sources:** Collect distinct source_file paths
4. **Relationship Count:** Count total relationship edges
5. **Average Scores:** Compute avg importance_score and confidence_score
6. **Last Extraction:** Get last extraction timestamp from extraction_log
7. **Repo Metadata:** Fetch repo_metadata if repo_id provided
8. **Return:** Return comprehensive status metrics

## Use Case

**Scenario:** Assess documentation completeness after extraction

**Workflow:**
1. Run extract on repository
2. Check status to see extraction coverage
3. Identify missing knowledge types (e.g., no risks documented)
4. Target documentation efforts to fill gaps

## Error Cases

| Error Code | Description |
|------------|-------------|
| KG_500 | Internal error |
