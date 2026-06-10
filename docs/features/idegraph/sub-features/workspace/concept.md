# Workspace

**Purpose:** Get workspace details by workspace key

**Why It Exists:** AI coders need to understand workspace configuration and project grouping across IDEs

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `workspace_key` | string | ✅ | — | Workspace key hash |

**Output Format:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Workspace found",
  "data": {
    "id": "ws_abc123",
    "project_name": "my-project",
    "project_path": "/path/to/project",
    "workspace_key": "abc123...",
    "conversation_count": 15,
    "ide_count": 3
  }
}
```

**Algorithm:**
1. Query SQLite database by workspace key
2. Return workspace details with aggregated statistics

**Use Case:** Understand which projects and IDEs are grouped together in a workspace
