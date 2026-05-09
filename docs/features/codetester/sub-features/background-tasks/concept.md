# Background Tasks

> **Source:** `QAService`

## Concept

QA tasks run asynchronously to avoid blocking the MCP server. Tasks are queued, executed in a thread pool, and can be polled for status or notified via webhook.

## Task Lifecycle

```
pending ──> running ──> completed
                │
                └──> failed
```

## Webhook Integration

When a webhook URL is provided, CodeTester POSTs results to the URL on completion:

```
POST /webhook-endpoint
Content-Type: application/json

{
  "task_id": "uuid",
  "status": "completed",
  "tool": "pytest",
  "exit_code": 0,
  "stdout": "...",
  "duration_ms": 1234
}
```
