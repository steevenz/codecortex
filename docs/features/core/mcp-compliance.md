# MCP Compliance: Annotations & Progress & Resources & Logging

> **Status:** Implemented in v1.2
> **AI Coder Impact:** 8/10 ⭐
> **Spec Ref:** MCP Specification 2025-2026

## Overview

CodeCortex implements **5 MCP enhancement layers** beyond basic JSON-RPC compliance:

| Layer | Feature | Status | File |
|-------|---------|--------|------|
| 1 | **Tool Annotations** | ✅ Done | `src/api/tools.py` |
| 2 | **Progress Notifications** | ✅ Done | `src/api/tools.py` |
| 3 | **Duration in Meta** | ✅ Done | `src/core/errors/errors.py` |
| 4 | **MCP Resources** | ✅ Done | `src/api/resources.py` |
| 5 | **Logging Notifications** | ✅ Done | `src/api/tools.py` |

---

## Layer 1: Tool Annotations

Each MCP tool declares `annotations` so LLMs know capabilities:

```python
@mcp.tool(
    annotations=ToolAnnotations(
        title="CodeCortex Repository",
        readOnlyHint=False,      # modifies env
        destructiveHint=True,    # can make destructive changes
        idempotentHint=False,    # repeated calls may have different effects
        openWorldHint=False,     # operates within defined bounds
    )
)
```

### Annotation Matrix

| Tool | readOnlyHint | destructiveHint | idempotentHint | openWorldHint |
|------|:---:|:---:|:---:|:---:|
| `codecortex:repository` | ❌ | ✅ | ❌ | ❌ |
| `codecortex:filesystem` | ❌ | ✅ | ❌ | ❌ |
| `codecortex:codebase` | ❌ | ✅ | ❌ | ❌ |
| `codecortex:scaffolder` | ✅ | ❌ | ✅ | ❌ |
| `codecortex:knowledge` | ✅ | ❌ | ✅ | ❌ |
| `codecortex:idegraph` | ✅ | ❌ | ✅ | ❌ |

---

## Layer 2: Progress Notifications

Long-running operations send MCP progress updates via `ctx.report_progress()`:

| Tool | Actions with Progress |
|------|----------------------|
| `codecortex:repository` | analyze, sync, audit |
| `codecortex:codebase` | analyze, audit, test, graph/build |

Pattern:
```python
if hasattr(ctx, "report_progress"):
    await ctx.report_progress(current, total, "Message")
```

---

## Layer 3: Duration in Meta

Every API response includes `meta.duration_ms`:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2026-06-12T07:00:00.000Z",
    "request_id": "req_abc123",
    "duration_ms": 342
  }
}
```

---

## Layer 4: MCP Resources

Structured read-only access via `codecortex://` URIs:

| URI | Description | Returns |
|-----|-------------|---------|
| `codecortex://repos/{repo_id}/status` | Repo health snapshot | files, symbols, edges, sync times |
| `codecortex://repos/{repo_id}/symbols` | All indexed symbols | grouped by type with file/line |
| `codecortex://repos/{repo_id}/graph` | Graph statistics | nodes, edges, density, hub candidates |
| `codecortex://repos/{repo_id}/metrics` | Code metrics | LOC, language breakdown |

Implementation: `src/api/resources.py` — registered in `src/main.py`.

---

## Layer 5: Logging Notifications

Tools log start/finish via MCP logging protocol:

```python
if hasattr(ctx, "info"):
    await ctx.info(f"codebase.analyze started")
```

Severities used: `info`, `warning`, `error` via `ctx.info()`, `ctx.warning()`, `ctx.error()`.

---

## Verification

1. `tools/list` → check `annotations` field on each tool
2. Long operations (analyze, sync) → observe `notifications/progress` from client
3. Any response → verify `meta.duration_ms` present
4. `resources/list` → verify `codecortex://` URIs appear
5. Tool calls → check stderr for `[info]` log lines
