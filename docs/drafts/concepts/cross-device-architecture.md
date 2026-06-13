# CodeCortex Architecture: Cross-Device, Remote Server & Cloud Sync

> **Status:** Draft / Concept
> **Version:** 0.1.0
> **Last Updated:** 2026-05-27
> **Author:** Steeven Andrian

---

## 1. The Problem

CodeCortex runs as a local MCP server (stdio) on each developer's machine. When the same project exists on multiple devices:

| Problem | Impact |
|---------|--------|
| Same repo, different paths (`C:\Users\A\project` vs `/home/b/project`) | Duplicate database entries, fragmented analysis |
| IDE conversations on Device A invisible on Device B | Lost cross-device memory |
| Knowledge extracted on Device A not available on Device B | Duplicate work |
| No central coordination for multi-agent setups | Each agent works in isolation |

---

## 2. Architecture Overview

```
┌─ Device A ──────────────────────────────────────┐
│ codecortex MCP (stdio — zero latency)            │
│ database/codecortex.db                           │
│   ├── CODE INDEX (files, symbols, edges, FTS)    │ ← LOCAL only (GB-scale)
│   ├── GRAPH (relationships, communities)         │ ← LOCAL only (rebuildable)
│   ├── EMBEDDINGS (vector search)                 │ ← LOCAL only (GB-scale)
│   ├── IDE CONVERSATIONS (cross-IDE memories)     │ ← SYNCED (KB-scale)
│   ├── KNOWLEDGE (engineering knowledge)          │ ← SYNCED (KB-scale)
│   ├── DEVICES + PATH MAPPINGS                    │ ← SYNCED
│   └── REPO METADATA (by remote_url)              │ ← SYNCED
│                                                    │
│   ~/.coddy/codecortex/                                   │
│   ├── device.json (device_id)                      │
│   ├── cloud.json (sync config)                     │
│   └── keys/ (E2E encryption keypair)               │
└─────────────────┬─────────────────────────────────┘
                  │
                  │ codecortex cloud push/pull
                  │ HTTPS / JSON
                  ▼
┌─ Relay / Sync Server ────────────────────────────┐
│ (PAID — api.codecortex.ai)                        │
│                                                    │
│  ● Data transit only — NOT stored on disk          │
│  ● TTL 24h — auto-delete after delivery            │
│  ● E2E encrypted — server cannot read plaintext    │
│  ● Coordinates push/pull between devices           │
│                                                    │
│  ● Web UI (dashboard) via WebSocket tunnel         │
│    → proxy ke device user → baca /api/v1/*         │
│    → NO data stored di server                      │
└──────────────────────┬────────────────────────────┘
                       │
┌─ Device B ───────────┘──────────────────────────┐
│ Same structure as Device A                        │
│ codecortex cloud pull → merge conversations       │
└──────────────────────────────────────────────────┘
```

### Key Principle: Data Locality

| Data Category | Size | Location | Sync? | Rationale |
|--------------|------|----------|-------|-----------|
| File index | MB–GB | LOCAL only | ❌ | Rebuildable via `repo sync` |
| Graph edges | MB | LOCAL only | ❌ | Rebuildable via `cb graph build` |
| Embeddings | MB | LOCAL only | ❌ | Rebuildable, model-specific |
| IDE conversations | KB | LOCAL + CLOUD | ✅ | Cross-device value |
| Knowledge chunks | KB | LOCAL + CLOUD | ✅ | Shared engineering knowledge |
| Device registry | KB | LOCAL + CLOUD | ✅ | Know which devices exist |
| Path mappings | KB | LOCAL + CLOUD | ✅ | Cross-device path resolution |

---

## 3. Cross-Device Identity (Phase 1)

### Problem

Before this feature, repository identity was **100% path-based**:

```sql
SELECT id FROM repositories WHERE root_path = '/path/to/project'  -- ONLY match
```

Same project on different paths = different `repo_id` = fragmented data.

### Solution: Git Remote as Canonical Identity

```sql
ALTER TABLE repositories ADD COLUMN vcs_url TEXT;
CREATE UNIQUE INDEX idx_repositories_vcs_url ON repositories(vcs_url)
    WHERE vcs_url IS NOT NULL AND vcs_url != '';
```

**Resolution order** (`upsert_repository`):

```
1. Match by root_path (exact)       → return existing repo_id     (O(1))
2. Match by vcs_url (remote origin) → return existing repo_id     (O(1))
3. Neither found                    → create new repository
```

**On `repo init`**, auto-capture git remote URL:

```python
result = subprocess.run(["git", "-C", path, "config", "--get", "remote.origin.url"])
if result.returncode == 0:
    remote_url = result.stdout.strip()  # "git@github.com:user/project.git"
```

### Case-Insensitive Path Normalization

Windows paths `C:\Users\...` vs `c:\Users\...` are now handled:

- `COLLATE NOCASE` in SQLite queries
- `Path().resolve()` normalization before storage
- `get_by_path_ci()` fallback in ORM store

### CLI: `repo link`

```bash
codecortex repo link /path/to/project git@github.com:user/project.git
```

Manually associate a local path with a remote URL (for repos without git).

---

## 4. Path Mapping (Phase 2)

### Problem

Remote server has paths like `/data/repos/project` but agent has `D:\Work\project`. The server needs to translate.

### Solution: Device + Path Mapping Tables

```sql
CREATE TABLE devices (
    id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    os TEXT DEFAULT '',
    user_home TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL
);

CREATE TABLE device_path_mappings (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES devices(id),
    device_path TEXT NOT NULL,
    server_path TEXT NOT NULL,
    repo_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(device_id, device_path)
);
```

### Resolution Flow

```
Agent sends: codecortex --remote http://server:8001 repo init D:\Work\project
                                                            ↑ device path
Server receives:
  Headers: X-Device-ID: abc-123
  Params:  action="init", repo_path="D:\Work\project"

Server interceptor (_resolve_device_and_paths):
  1. Lookup path mapping: device_id=abc-123, device_path="D:\Work\project"
  2. Found → translate to server_path="/data/repos/project"
  3. Execute tool with translated path
```

### Auto-Registration

On `repo init`, if the server detects an unmapped path, it stores an explicit mapping via CLI:

```bash
codecortex remote path-map D:\Work\project /data/repos/project --remote http://server:8001
```

### Device Identity

Auto-generated on first use, stored in `~/.coddy/codecortex/device.json`:

```json
{
  "device_id": "e7c126b1-be77-4a3e-8444-6a57a7c72ecb",
  "hostname": "MY-LAPTOP",
  "os": "Windows 11",
  "user_home": "C:\\Users\\user"
}
```

---

## 5. Monorepo Detection

### Problem

A monorepo at `/monorepo` has subdirectories `/packages/a`, `/packages/b`. Without detection, each subdirectory init creates a duplicate entry.

### Solution

On `upsert_repository`, before creating a new entry:

```python
for existing_repo in all_repos:
    if new_path is inside existing_repo.path:
        has_own_vcs = (
            (new_path / ".git").is_dir()
            or (new_path / ".svn").is_dir()
        )
        if not has_own_vcs:
            return existing_repo.id  # merge into parent
```

| Scenario | `.git`? | Result |
|----------|---------|--------|
| `/monorepo/packages/pkg-a` | ❌ | Merge into `/monorepo` |
| `/monorepo/vendor/lib-sdk` | ✅ | Create new repo (submodule) |
| `/standalone-project` (not in any repo) | — | Create new repo |

---

## 6. Remote Execution Proxy

### CLI `--remote` Flag

All CLI commands can be sent to a remote server instead of executing locally:

```bash
codecortex --remote http://server:8001 repo list
codecortex --remote http://server:8001 fs read /path/to/file.py
codecortex --remote http://server:8001 cb search "find_users"
```

### How It Works

```python
def main():
    # ...
    if remote_url and domain not in ("server", "remote", "cloud", "version"):
        result = _send_remote(remote_url, domain, args_ns)
        output(result)
        return
    # ... local dispatch
```

### Domain-to-Method Mapping

| CLI Domain | MCP Method | Example Params |
|-----------|-----------|----------------|
| `repo` | `repository` | `{"action": "list"}` |
| `fs` | `filesystem` | `{"action": "read", "path": "/file.py"}` |
| `cb` | `codebase` | `{"action": "search", "repo_path": "...", "args": {...}}` |
| `sc` | `scaffolder` | `{"action": "list_stacks"}` |
| `kg` | `knowledge_graph` | `{"action": "extract", "repo_path": "..."}` |
| `ig` | `idegraph` | `{"action": "search", "query": "payment"}` |

---

## 7. Server Expose (Tunnel)

### Architecture

```
codecortex server start --expose https://api.codecortex.ai

┌─ Local HTTP Server ──────┐     ┌─ Relay Server ───────────────┐
│ localhost:8001             │     │ api.codecortex.ai            │
│  ├── /api/v1/status       │◀───▶│  ├── /tunnel/register       │
│  ├── /api/v1/repositories │     │  ├── /tunnel/{id}/poll      │
│  ├── /api/v1/conversations│     │  ├── /tunnel/{id}/respond   │
│  ├── /api/v1/knowledge    │     │  └── WebSocket to Web UI    │
│  └── /api/v1/devices      │     └─────────────────────────────┘
└────────────────────────────┘
```

### Tunnel Protocol

```
1. Client POSTs to /tunnel/register → gets tunnel_id
2. Client polls GET /tunnel/{id}/poll (SSE/long-poll)
3. Relay sends proxy_request: {id, method, path, headers, body}
4. Client executes locally via httpx
5. Client POSTs response to /tunnel/{id}/respond: {id, status, body}
```

### Read-Only API Endpoints

| Endpoint | Returns | For Web UI |
|----------|---------|------------|
| `GET /api/v1/status` | `{repositories, conversations, messages, knowledge_chunks}` | Dashboard stats |
| `GET /api/v1/repositories` | All repos with metadata | Repo list |
| `GET /api/v1/conversations` | Latest 50 with message count | Conversation list |
| `GET /api/v1/conversations/{id}` | Full conversation + all messages | Detail view |
| `GET /api/v1/knowledge` | Knowledge chunks by importance | Knowledge explorer |
| `GET /api/v1/devices` | Registered devices | Device management |

---

## 8. Cloud Sync (git-style)

### Philosophy

```
Manual, explicit — like git. Not auto-sync.

User decides when to push/pull.
Zero overhead when not syncing.
No surprise conflicts.
```

### Commands

```bash
codecortex cloud init https://api.codecortex.ai    # Register device + generate keys
codecortex cloud push                                # Upload local changes
codecortex cloud pull                                # Download remote changes
codecortex cloud sync                                # Push + Pull (bi-directional)
codecortex cloud status                              # Show sync state
```

### What Gets Synced

Only **portable data** (KB-scale) is synced:

| Table | Size Estimate | Why Portable |
|-------|--------------|--------------|
| `conversations` | KB | Cross-IDE memories |
| `messages` | KB | Conversation content |
| `contexts` | KB | AI context snapshots |
| `knowledge_chunks` | KB | Engineering knowledge |
| `knowledge_relationships` | KB | Knowledge graph edges |
| `golden_knowledge` | KB | AI context injection |
| `workspaces`, `projects` | KB | IDE workspace metadata |
| `ides`, `configurations` | KB | IDE detection |
| `devices` | KB | Device registry |
| `device_path_mappings` | KB | Cross-device path mapping |

### Encryption (E2E)

Data is encrypted client-side before leaving the device:

```
cloud init → generate X25519 keypair → ~/.coddy/codecortex/keys/
cloud push → encrypt(AES-256-GCM) → send ciphertext to relay
cloud pull → receive ciphertext → decrypt locally → merge into DB
```

The relay server never sees plaintext data.

### Change Tracking

`~/.coddy/codecortex/cloud.json`:

```json
{
  "server_url": "https://api.codecortex.ai",
  "device_id": "e7c126b1-...",
  "last_push_at": "2026-05-27T10:30:00+00:00",
  "last_pull_at": "2026-05-27T10:30:00+00:00"
}
```

Push reads records where `updated_at > last_push_at`. Pull reads from other devices where `updated_at > last_pull_at`.

---

## 9. Database Cleanup: Deduplicate

### Problem

Before case normalization and monorepo detection, the database accumulated duplicate entries:

```
C:\Users\A\project   (repo_id: abc)
c:\Users\A\project   (repo_id: xyz)  ← same path, different case
/monorepo/pkg-a      (repo_id: def)  ← subdirectory without .git
```

### CLI Command

```bash
codecortex repo deduplicate           # Dry-run — preview duplicates
codecortex repo deduplicate --apply   # Merge duplicates
```

### Detection Logic (3 types)

1. **Case-insensitive path**: `GROUP BY LOWER(root_path)`
2. **Subdirectory monorepo**: Path A inside Path B, no `.git`/`.svn`
3. **Remote URL**: Same `vcs_url`

### Merge Logic

```python
for canonical, duplicate in pairs:
    # Transfer FK records (20 tables): files, symbols, edges, etc.
    for table in FK_TABLES:
        UPDATE table SET repository_id = canonical_id
        WHERE repository_id = duplicate_id
    # Delete duplicate
    DELETE FROM repositories WHERE id = duplicate_id
```

---

## 10. Implementation Status

| Feature | Files Changed | Status |
|---------|--------------|--------|
| Remote URL identity | `main.py`, ORM model, both stores, CLI | ✅ |
| Case normalization | Both stores (`COLLATE NOCASE`) | ✅ |
| Monorepo detection | `sqlite_store.py` | ✅ |
| Path mapping | `path_mapping.py`, `http.py`, `cli.py` | ✅ |
| Remote execution proxy | `cli.py` (`--remote` + `_REMOTE_ROUTES`) | ✅ |
| Server expose (tunnel) | `tunnel.py`, `http.py`, `cli.py` | ✅ |
| Read-only API | `http.py` (6 endpoints) | ✅ |
| Cloud sync (git-style) | `cloud_sync.py`, `cli.py` | ✅ |
| E2E encryption | `encryption.py` | ✅ |
| Deduplicate CLI | `cli.py` (`repo deduplicate`) | ✅ |
| Deduplicate merge | `cli.py` (20 FK tables) | ✅ |

### Total: ~15 files, ~2000 lines of new/changed code

---

## 11. Future Work (Paid Server)

The following components are NOT open source — they run on the paid server:

| Component | Description |
|-----------|-------------|
| **Relay API** | `POST /tunnel/register`, `GET /tunnel/{id}/poll`, `POST /tunnel/{id}/respond` |
| **Cloud push/pull** | `POST /cloud/push` (receive ciphertext), `POST /cloud/pull` (return ciphertext) |
| **Web UI** | Dashboard consuming `/api/v1/*` via WebSocket tunnel |
| **Auth** | Subscription management, device registration |
| **TTL cleanup** | Auto-delete relayed data after 24h |
