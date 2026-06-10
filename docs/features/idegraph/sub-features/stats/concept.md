# Stats

**Purpose:** Get ingestion statistics broken down by IDE and time period

**Why It Exists:** AI coders need to understand which IDEs are being used most and track ingestion patterns over time

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `ide_name` | string | ❌ | — | Filter by IDE name |
| `since` | string | ❌ | — | ISO timestamp filter |

**Output Format:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Ingestion stats",
  "data": {
    "total_conversations": 150,
    "total_messages": 1200,
    "by_ide": {
      "cursor": 50,
      "trae": 30,
      "claude": 40,
      "gemini": 30
    },
    "by_date": {
      "2026-05-29": 50,
      "2026-05-28": 100
    }
  }
}
```

**Algorithm:**
1. Query SQLite database with optional filters
2. Aggregate statistics by IDE and date
3. Return breakdown

**Use Case:** Analyze IDE usage patterns to understand which tools are most productive
