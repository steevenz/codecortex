# Graph Timeline Example

## MCP Tool Call — AI Summary

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "codecortex:idegraph",
    "arguments": {
      "action": "timeline",
      "workspace_key": "ws-myapp",
      "limit": 10
    }
  }
}
```

## Response — AI-Optimized Summary

```json
{
  "success": true,
  "status_code": 200,
  "message": "Graph timeline retrieved",
  "data": {
    "workspace_key": "ws-myapp",
    "summary": {
      "total_conversations": 15,
      "total_relationships": 8,
      "active_sessions": 4,
      "date_range": {"from": "2026-05-28", "to": "2026-05-29"},
      "latest_conversation_id": "engram-015"
    },
    "recent_activity": [
      {
        "id": "engram-015",
        "title": "Setup PostgreSQL database",
        "source": "trae",
        "day": "2026-05-29",
        "depth": 0,
        "message_count": 25,
        "has_artifacts": true
      },
      {
        "id": "engram-014",
        "title": "Add OAuth2 login",
        "source": "cursor",
        "day": "2026-05-29",
        "depth": 2,
        "message_count": 8,
        "has_artifacts": true
      },
      {
        "id": "engram-013",
        "title": "Fix JWT authentication bug",
        "source": "cursor",
        "day": "2026-05-29",
        "depth": 1,
        "message_count": 12,
        "has_artifacts": true
      }
    ],
    "suggested_context": {
      "related_to_latest": [
        {"id": "engram-014", "title": "Add OAuth2 login", "relationship": "connected"}
      ],
      "recent_fixes": [
        {"id": "engram-013", "title": "Fix JWT authentication bug"}
      ]
    },
    "actions_available": [
      "get_timeline(engram_id) — chronological path to any conversation",
      "get_related(engram_id) — find connected conversations",
      "get_branch(session_id) — see all conversations in a session",
      "get_day_summary(day) — daily activity overview"
    ]
  },
  "meta": {
    "request_id": "req_timeline_001",
    "timestamp": "2026-05-29T10:30:00Z"
  }
}
```

## MCP Tool Call — Rich Context for LLM

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "codecortex:idegraph",
    "arguments": {
      "action": "related",
      "memory_id": "engram-014",
      "include_context": true
    }
  }
}
```

## Response — Rich Context Format

```json
{
  "success": true,
  "status_code": 200,
  "message": "Context retrieved",
  "data": {
    "target": {
      "id": "engram-014",
      "title": "Add OAuth2 login",
      "source": "cursor",
      "created_at": "2026-05-29T09:15:00Z",
      "message_count": 8,
      "project_name": "myapp"
    },
    "context": {
      "timeline_position": "3 of 3 in lineage",
      "ancestors": [
        {"id": "engram-012", "title": "Debug token refresh"},
        {"id": "engram-013", "title": "Fix JWT authentication bug"}
      ],
      "siblings_same_session": [
        {"id": "engram-013", "title": "Fix JWT authentication bug"}
      ],
      "related_conversations": [
        {
          "id": "engram-013",
          "title": "Fix JWT authentication bug",
          "source": "cursor",
          "reason": "continues conversation flow"
        },
        {
          "id": "engram-012",
          "title": "Debug token refresh",
          "source": "cursor",
          "reason": "continues conversation flow"
        }
      ]
    },
    "project_state": {
      "git_branch": "feature/oauth",
      "git_commit": "def4567890",
      "repo_path": "/projects/myapp",
      "repo_remote_url": "github.com/user/myapp",
      "open_files": ["auth.py", "oauth.py", "test_auth.py"],
      "active_file": "oauth.py",
      "ide_name": "cursor",
      "ide_version": "0.45.0"
    },
    "suggested_next_actions": [
      "Follow conversation lineage to understand auth implementation history",
      "Explore related conversations for OAuth2 context",
      "Link conversation to project 'myapp' for better organization"
    ]
  },
  "meta": {
    "request_id": "req_context_002",
    "timestamp": "2026-05-29T10:30:00Z"
  }
}
```

## CLI Command

```bash
# Get graph timeline for workspace
codecortex ig timeline --workspace ws-myapp --limit 10

# Get rich context for a specific conversation
codecortex ig context engram-014

# Get related conversations
codecortex ig related engram-014

# Get conversation branch (session)
codecortex ig branch sess_abc123

# Get day summary
codecortex ig day-summary 2026-05-29
```

## Use Case

The graph timeline helps AI coders answer questions like:
- "What was I working on before this conversation?" → `ancestors` in context
- "Which conversations are about the same topic?" → `related_conversations` with `reason`
- "What was my git branch when I fixed that bug?" → `project_state.git_branch`
- "How many conversations did I have today?" → `day_summary`
- "Did I already solve this problem?" → `recent_fixes` in summary

## Token Efficiency

| Format | Tokens | Use Case |
|--------|--------|----------|
| Full graph dump | ~15,000 | Debugging |
| `to_ai_summary()` | ~500 | Quick overview |
| `to_ai_context()` | ~1,200 | Deep context for LLM |
| **Savings** | **75-95%** | vs full dump |
