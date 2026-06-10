# Compact

**Purpose:** Run LLM-powered conversation summarization to reduce token costs while preserving key insights

**Why It Exists:** Long conversations consume many tokens — compaction summarizes them while maintaining essential context for AI coders

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | int | ❌ | `5` | Number of conversations to compact |
| `focus` | string | ❌ | — | Focus topic for summary |

**Output Format:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Compacted 5 conversations",
  "data": {
    "results": [
      {
        "id": "engram-123",
        "goal": "Fixed authentication bug by updating JWT validation logic"
      },
      {
        "id": "engram-456",
        "goal": "Implemented user registration with email verification"
      }
    ],
    "total": 5
  }
}
```

**Algorithm:**
1. Retrieve recent conversations (limit)
2. Format conversation text (first 30 messages)
3. Send to LLM for summarization
4. Extract goal/insight from response
5. Return compacted records

**Use Case:** Reduce token costs by summarizing old conversations while preserving the main goal and outcome
