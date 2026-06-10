# Get

**Purpose:** Retrieve a single memory/conversation by its unique ID with optional summary mode for token efficiency

**Why It Exists:** AI coders need to access complete conversation history including all messages, code context, and tool use for detailed analysis. The summary mode provides a token-efficient alternative when full history isn't needed.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_id` | string | ✅ | — | Memory ID to retrieve |
| `summary_mode` | bool | ❌ | `false` | Return summary without full messages (70% token savings) |

**Output Format (Full Mode):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Memory retrieved",
  "data": {
    "type": "engram",
    "id": "engram-123",
    "attributes": {
      "source": "cursor",
      "source_file": "/path/to/file.py",
      "title": "Fix authentication bug",
      "project_name": "my-project",
      "ide_info": {
        "name": "cursor",
        "type": "vscode-extension",
        "installation_path": "/path/to/cursor"
      },
      "messages": [
        {
          "role": "user",
          "content": "Help me fix the auth bug",
          "timestamp": "2026-05-29T10:00:00Z"
        },
        {
          "role": "assistant",
          "content": "I'll help you fix the authentication bug...",
          "timestamp": "2026-05-29T10:00:05Z"
        }
      ]
    }
  }
}
```

**Output Format (Summary Mode):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Memory retrieved (summary)",
  "data": {
    "type": "engram_summary",
    "id": "engram-123",
    "attributes": {
      "source": "cursor",
      "source_file": "/path/to/file.py",
      "title": "Fix authentication bug",
      "project_name": "my-project",
      "ide_info": { ... },
      "message_count": 15,
      "first_message_snippet": "Help me fix the auth bug..."
    }
  }
}
```

**Algorithm:**
1. Query SQLite database by conversation ID
2. If summary_mode=True:
   - Return summary with message_count and first 100 chars of first message
   - Skip full message history (~70% token savings)
3. If summary_mode=False (default):
   - Hydrate full message history with metadata
   - Include IDE info and workspace details
4. Return standardized export or summary record

**Token Efficiency:**
- Full mode: ~8,000 tokens (includes all messages)
- Summary mode: ~500 tokens (70% savings)

**Use Case:** Retrieve complete conversation history for a specific bug fix (full mode), or quickly check conversation metadata across multiple memories (summary mode)
