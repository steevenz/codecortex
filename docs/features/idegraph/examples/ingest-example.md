# Ingest Example

## MCP Tool Call

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "codecortex:idegraph",
    "arguments": {
      "action": "ingest"
    }
  }
}
```

## Response

```json
{
  "success": true,
  "status_code": 200,
  "message": "Ingestion completed",
  "data": {
    "output_path": "/outputs/sidecortex_ingest_20260529_100000.jsonl",
    "summary": {
      "total_engrams": 150,
      "breakdown": {
        "by_ide": {
          "cursor": 50,
          "trae": 30,
          "claude": 40,
          "gemini": 30
        },
        "by_type": {
          "vscode-extension": 120,
          "desktop": 30
        }
      },
      "total_messages": 1200
    },
    "storage": {
      "total_conversations": 150,
      "total_messages": 1200,
      "failed_runs": 0
    }
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-05-29T10:00:00Z"
  }
}
```

## CLI Command

```bash
codecortex ig ingest
```

## Use Case

Initial setup or periodic refresh to ensure all IDE conversations from Cursor, Trae, Claude, and Gemini are indexed and searchable in the unified memory graph.
