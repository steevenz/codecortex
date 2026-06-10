# List

**Purpose:** List memories with optional filtering by project, workspace, and IDE

**Why It Exists:** AI coders need to browse available conversations across projects and IDEs to discover relevant context

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_name` | string | ❌ | — | Filter by project name |
| `workspace_key` | string | ❌ | — | Filter by workspace key hash |
| `ide_name` | string | ❌ | — | Filter by IDE name |
| `limit` | int | ❌ | `20` | Max results (max 200) |
| `offset` | int | ❌ | `0` | Offset for pagination |

**Output Format:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Returned 20 memories",
  "data": {
    "items": [{
      "id": "engram-123",
      "title": "Fix authentication bug",
      "source": "cursor",
      "project_name": "my-project",
      "created_at": "2026-05-29T10:00:00Z"
    }],
    "limit": 20,
    "offset": 0
  }
}
```

**Algorithm:**
1. Query SQLite database with optional filters
2. Apply pagination with limit/offset
3. Return summary records (not full message history)

**Use Case:** Browse all conversations in a specific project to find relevant past work
