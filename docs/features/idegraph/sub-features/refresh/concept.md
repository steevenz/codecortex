# Refresh

**Purpose:** Re-ingest a specific project path without running full ingestion

**Why It Exists:** AI coders make incremental changes — refresh allows updating specific projects efficiently

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | ✅ | — | Project path to refresh |
| `force` | bool | ❌ | `false` | Force re-ingestion (ignore cache) |

**Output Format:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Project refreshed",
  "data": {
    "result": {
      "request_id": "req_abc123",
      "project_path": "/path/to/project",
      "matched_engrams": 15,
      "persist": {
        "conversations_upserted": 15,
        "messages_upserted": 120
      },
      "timestamp": "2026-05-29T10:00:00Z"
    },
    "storage": {
      "total_conversations": 150,
      "total_messages": 1200
    }
  }
}
```

**Algorithm:**
1. Normalize project path for comparison
2. Filter cached engrams by matching project path
3. Persist filtered engrams to SQLite
4. Return ingestion statistics

**Use Case:** After making changes to a specific project, refresh only that project's conversations to keep the index current
