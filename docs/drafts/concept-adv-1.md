## 📄 SideCortex MCP Tools – Standardized Concept (v2)

**Repository:** `c:\Users\steevenz\.aicoders\scripts\pythons\sidecortex`  
**Based on:** Hybrid Architecture Standard + trae-memory patterns  
**Goal:** Define a complete, production‑ready MCP toolset for SideCortex with typed contracts, session/context/task management, operational tooling, and full alignment with the unified conversation JSON contract.

---

### 1. Overview & Design Principles

SideCortex’s core value is **multi‑IDE conversation ingestion** into a unified `Engram` DTO with explicit provenance. The MCP layer must expose that value while adding **runtime state management** (sessions, contexts, tasks) and **operational safety** (health, rotation, diagnostics).

**Design Principles**
1. **Typed input/output** – every tool uses explicit request/response schemas.
2. **Separation of concerns** – ingestion (raw exports) vs MCP runtime (`data/`) vs queries.
3. **Observability first** – structured logs, `request_id`, health endpoint.
4. **Backward compatible** – existing tool names may be kept as aliases.
5. **Security** – session tokens for sensitive operations, no secrets in logs.

**Tool Naming Convention**  
`verb_noun` – clear, predictable, aligned with both SideCortex and ExoCortex ecosystems.  
Example: `search_conversations`, `create_session`, `trigger_ingestion`.

---

### 2. Tool Categories

| Category | Tools | Purpose |
|----------|-------|---------|
| **Conversation Query** | `search_conversations`, `list_workspaces`, `get_conversation` | Retrieve ingested Engrams and workspaces |
| **Ingestion Control** | `trigger_ingestion`, `get_ingestion_status`, `rotate_storage` | Manage the parsing pipeline and data lifecycle |
| **Cognitive Runtime** | `create_session`, `continue_session`, `get_session`, `list_sessions` | Session/context/task management (trae-memory style) |
| **Task Management** | `create_task`, `list_tasks`, `update_task`, `get_task` | Track work items linked to sessions |
| **Operational** | `health`, `diagnose`, `get_storage_info` | Monitor and debug the MCP server |

---

### 3. Detailed Tool Specifications

#### 3.1 Conversation Query Tools

##### `search_conversations`

**Purpose:** Search across ingested `Engram` records (JSONL) by content, workspace, IDE, time range, or metadata.

**Parameters (JSON Schema):**
```json
{
  "query": { "type": "string", "description": "Natural language or keyword search" },
  "workspace_key": { "type": "string", "optional": true },
  "project_name": { "type": "string", "optional": true },
  "ide_name": { "type": "string", "enum": ["trae","cursor","windsurf","claude","codex","continue","opencode","gemini","antigravity"], "optional": true },
  "start_date": { "type": "string", "format": "date-time", "optional": true },
  "end_date": { "type": "string", "format": "date-time", "optional": true },
  "limit": { "type": "integer", "default": 20, "minimum": 1, "maximum": 100 }
}
```

**Workflow:**
1. Validate input (reject empty query if no filters).
2. Use `SearchService` (existing) with BM25 + keyword filtering.
3. Return results as a list of Engram summaries (not full messages, to save tokens).

**Return Schema:**
```json
{
  "status": "success",
  "data": {
    "conversations": [
      {
        "engram_id": "sha256...",
        "title": "Fix JWT refresh",
        "ide_name": "cursor",
        "project_name": "C--Users-steevenz-Projects-my-api",
        "workspace_key": "sha256...",
        "created_at": "2026-05-01T10:00:00Z",
        "message_count": 12,
        "snippet": "first user message preview..."
      }
    ],
    "total": 42
  },
  "meta": { "request_id": "req_...", "timestamp": "..." }
}
```

**Replaces:** existing `search_memories` (but keep alias for compatibility).

---

##### `list_workspaces`

**Purpose:** Return all distinct workspaces (aggregated from Engrams) with their IDEs and date ranges.

**Parameters:** none

**Return:**
```json
{
  "status": "success",
  "data": {
    "workspaces": [
      {
        "workspace_key": "sha256...",
        "project_name": "my-api",
        "project_path": "C:/Users/.../my-api",
        "ides": ["cursor", "trae"],
        "first_seen": "2026-04-01T08:00:00Z",
        "last_seen": "2026-05-01T12:00:00Z",
        "engram_count": 47
      }
    ]
  },
  "meta": { ... }
}
```

**Replaces:** `list_projects` (keep alias).

---

##### `get_conversation`

**Purpose:** Retrieve a full Engram (all messages) by ID, with optional token‑limited excerpts.

**Parameters:**
```json
{
  "engram_id": { "type": "string", "required": true },
  "max_messages": { "type": "integer", "default": 50, "maximum": 200 }
}
```

**Return:** The full Engram DTO (as defined in the unified contract) but with `messages` truncated if `max_messages` is less than total.

**Replaces:** `get_interaction_detail` (keep alias).

---

#### 3.2 Ingestion Control Tools

##### `trigger_ingestion`

**Purpose:** Manually run the ingestion pipeline (parses all configured IDEs and writes JSONL). Optionally specify a single IDE.

**Parameters:**
```json
{
  "ide_name": { "type": "string", "enum": [...], "optional": true },
  "force_reparse": { "type": "boolean", "default": false }
}
```

**Workflow:**
1. Call `SideCortexOrchestrator.run_all` (or single IDE).
2. Write results to `outputs/sidecortex_ingest_<timestamp>.jsonl`.
3. Emit structured logs (aligned with logging standard).
4. Return summary.

**Return:**
```json
{
  "status": "success",
  "data": {
    "execution_id": "ingest_20260501_150204",
    "output_file": "outputs/sidecortex_ingest_20260501_150204.jsonl",
    "by_ide": { "cursor": 12, "trae": 8 },
    "total_engrams": 20,
    "duration_ms": 1234
  },
  "meta": { ... }
}
```

**Existing tool** – keep name, but enhance return structure.

---

##### `get_ingestion_status`

**Purpose:** Retrieve the last ingestion run(s) status, including any errors or performance metrics.

**Parameters:** none

**Return:** list of recent ingestion runs (from a small history file or log analysis).

---

##### `rotate_storage`

**Purpose:** Manually rotate the MCP runtime files (`sessions.json`, `tasks.json`, `context.json`) based on size or age. Also archive old ingestion outputs.

**Parameters:**
```json
{
  "target": { "type": "string", "enum": ["runtime", "outputs", "all"], "default": "runtime" },
  "max_age_days": { "type": "integer", "default": 30 }
}
```

**Return:** summary of rotated/archived files.

---

#### 3.3 Cognitive Runtime Tools (Session + Context)

These implement the trae‑memory pattern: a session represents a continuous reasoning thread, with context window tracking and auto‑saving.

##### `create_session`

**Purpose:** Start a new cognitive session linked to a workspace/project.

**Parameters:**
```json
{
  "workspace_key": { "type": "string", "optional": true },
  "project_name": { "type": "string", "optional": true },
  "title": { "type": "string", "optional": true },
  "config": {
    "context_threshold_tokens": { "type": "integer", "default": 8000 },
    "auto_save": { "type": "boolean", "default": true }
  }
}
```

**Return:**
```json
{
  "status": "success",
  "data": {
    "session_id": "sess_abc123",
    "session_token": "sec_...",
    "created_at": "...",
    "context_usage": 0
  }
}
```

---

##### `continue_session`

**Purpose:** Append a message/thought to a session, update context token count, and optionally force auto‑save.

**Parameters:**
```json
{
  "session_id": { "type": "string", "required": true },
  "session_token": { "type": "string", "required": true },
  "message": { "type": "string", "required": true },
  "role": { "type": "string", "enum": ["user", "assistant"], "default": "user" }
}
```

**Return:** updated session state (token usage, auto‑saved flag).

---

##### `get_session`

**Purpose:** Retrieve session details and message history (limited).

**Parameters:** `session_id`, `session_token`.

**Return:** full session object (messages up to last 100, plus metadata).

---

##### `list_sessions`

**Purpose:** List all sessions for a workspace or globally.

**Parameters:** `workspace_key` (optional), `limit`.

**Return:** array of session summaries.

---

#### 3.4 Task Management Tools

A task is a unit of work associated with a session (e.g., “implement JWT refresh”). Tasks can be created, updated, and closed.

##### `create_task`

**Parameters:**
```json
{
  "session_id": { "type": "string", "optional": true },
  "title": { "type": "string", "required": true },
  "description": { "type": "string" },
  "due_date": { "type": "string", "format": "date-time", "optional": true },
  "priority": { "type": "string", "enum": ["low","medium","high"], "default": "medium" }
}
```

**Return:** task object with `task_id`.

---

##### `list_tasks`

**Parameters:** `session_id` (optional), `status` (`pending|in_progress|completed`).

**Return:** list of tasks.

---

##### `update_task`

**Parameters:** `task_id`, `status`, `notes` (optional).

**Return:** updated task.

---

##### `get_task`

**Parameters:** `task_id`.

**Return:** full task details.

---

#### 3.5 Operational Tools

##### `health`

**Purpose:** Lightweight liveness probe.

**Return:**
```json
{ "status": "ok", "timestamp": "...", "version": "0.2.0" }
```

---

##### `diagnose`

**Purpose:** Run self‑diagnostics: check disk space, file permissions, ingestion output integrity, MCP runtime file validity.

**Return:** detailed report with warnings/errors.

---

##### `get_storage_info`

**Purpose:** Show disk usage, file sizes, and rotation status for `outputs/` and `data/`.

**Return:** structured metrics.

---

### 4. Tool Summary & Migration

| New Tool | Replaces / Combines | Status |
|----------|---------------------|--------|
| `search_conversations` | `search_memories` (enhanced) | Keep alias |
| `list_workspaces` | `list_projects` (enhanced) | Keep alias |
| `get_conversation` | `get_interaction_detail` | Keep alias |
| `trigger_ingestion` | unchanged | Keep |
| `get_ingestion_status` | new | Add |
| `rotate_storage` | new | Add |
| `create_session` | new (trae-memory) | Add |
| `continue_session` | new | Add |
| `get_session` | new | Add |
| `list_sessions` | new | Add |
| `create_task` | new | Add |
| `list_tasks` | new | Add |
| `update_task` | new | Add |
| `get_task` | new | Add |
| `health` | new | Add |
| `diagnose` | new | Add |
| `get_storage_info` | new | Add |

**Total new tools:** 12 (plus 4 enhanced, 3 kept).  
Existing 4 tools remain but get structured outputs and optional aliases.

---

### 5. Implementation Notes (Phase 0)

- **Storage layout:**  
  - `outputs/` – ingestion JSONL exports (unchanged).  
  - `data/` – MCP runtime state: `sessions.json`, `tasks.json`, `context_usage.json`, `ingestion_status.json`.  
  - Environment overrides: `SIDECORTEX_DATA_DIR`, `SIDECORTEX_SESSIONS_FILE`, etc.

- **Session token:** generated via `secrets.token_urlsafe(32)`. Required for any mutation tool (continue_session, update_task, etc.).

- **Logging:** All tools must emit structured JSON logs with `request_id` (generated per call) and respect no‑secrets rule.

- **Error handling:** Return `{"status":"error","error_code":"...","message":"..."}` and log sanitized details.

---

### 6. Next Steps

1. **Approve this toolset concept** – confirm naming, scope, and prioritisation.
2. **Implement Phase 0** – structured outputs for existing 4 tools + add `health`, `diagnose`, `rotate_storage`.
3. **Add session/task domain** (`src/mcp_runtime/`) with in‑memory + file persistence.
4. **Add the remaining tools** (`create_session`, `continue_session`, tasks, etc.).
5. **Write integration tests** for each tool using an MCP client.

This concept ensures SideCortex becomes a **production‑ready MCP server** while preserving its core strength: unified multi‑IDE conversation memory.

---

**End of SideCortex MCP Tools Concept v2**