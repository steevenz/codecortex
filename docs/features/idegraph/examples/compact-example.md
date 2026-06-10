# Compact Example

## MCP Tool Call

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "codecortex:idegraph",
    "arguments": {
      "action": "compact",
      "limit": 5,
      "focus": "authentication"
    }
  }
}
```

## Response

```json
{
  "success": true,
  "status_code": 200,
  "message": "Compacted 5 conversations",
  "data": {
    "results": [
      {
        "id": "engram-abc123",
        "goal": "Fixed JWT authentication bug by updating token validation logic and adding proper error handling for expired tokens"
      },
      {
        "id": "engram-def456",
        "goal": "Implemented OAuth2 login flow with Google provider, including token refresh and user profile retrieval"
      },
      {
        "id": "engram-ghi789",
        "goal": "Debugged session token refresh issue by fixing race condition in token renewal process"
      },
      {
        "id": "engram-jkl012",
        "goal": "Added multi-factor authentication support with TOTP implementation and backup codes"
      },
      {
        "id": "engram-mno345",
        "goal": "Refactored authentication middleware to support multiple auth providers with unified interface"
      }
    ],
    "total": 5
  },
  "meta": {
    "request_id": "req_xyz789",
    "timestamp": "2026-05-29T10:30:00Z"
  }
}
```

## CLI Command

```bash
codecortex ig compact --limit 5
```

## Use Case

Reduce token costs by summarizing the 5 most recent conversations about authentication, preserving the main goal and outcome while discarding verbose message history.
