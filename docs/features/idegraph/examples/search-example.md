# Search Example

## MCP Tool Call

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "codecortex:idegraph",
    "arguments": {
      "action": "search",
      "query": "authentication",
      "project_name": "my-project",
      "ide_name": "cursor",
      "limit": 10
    }
  }
}
```

## Response

```json
{
  "success": true,
  "status_code": 200,
  "message": "Found 3 matches",
  "data": {
    "items": [
      {
        "id": "engram-abc123",
        "title": "Fix JWT authentication bug",
        "source": "cursor",
        "project_name": "my-project",
        "workspace_key": "a1b2c3d4e5f6...",
        "created_at": "2026-05-29T10:00:00Z"
      },
      {
        "id": "engram-def456",
        "title": "Add OAuth2 login flow",
        "source": "cursor",
        "project_name": "my-project",
        "workspace_key": "a1b2c3d4e5f6...",
        "created_at": "2026-05-28T15:30:00Z"
      },
      {
        "id": "engram-ghi789",
        "title": "Debug session token refresh",
        "source": "cursor",
        "project_name": "my-project",
        "workspace_key": "a1b2c3d4e5f6...",
        "created_at": "2026-05-27T09:15:00Z"
      }
    ],
    "count": 3
  },
  "meta": {
    "request_id": "req_xyz789",
    "timestamp": "2026-05-29T10:30:00Z"
  }
}
```

## CLI Command

```bash
codecortex ig search "authentication" --project my-project --ide cursor --limit 10
```

## Use Case

Searching for previous authentication-related conversations in the my-project project when working on a new auth feature to avoid repeating work and understand previous solutions.
