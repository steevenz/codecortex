# Health

**Purpose:** Check database health and ingestion status

**Why It Exists:** AI coders need to verify the IDE graph system is functioning correctly and data is being ingested properly

**Parameters:**
None

**Output Format:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "healthy",
  "data": {
    "status": "healthy",
    "total_conversations": 150,
    "total_messages": 1200,
    "failed_runs": 0,
    "last_ingestion": "2026-05-29T10:00:00Z"
  }
}
```

**Algorithm:**
1. Query SQLite database for statistics
2. Check for failed ingestion runs
3. Return health snapshot with status

**Use Case:** Verify the IDE graph system is operational before starting a new coding session
