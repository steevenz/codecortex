# MCP Node ↔ Python Server Architecture

> **Concept**: How Node.js wrappers (`index.cjs`, `run_server.js`) connect to a Python MCP backend with multi-IDE safety, PID handshake, and lifecycle management.
>
> **Applies to**: `scripts/server/js/index.cjs`, `scripts/server/run_server.js`, `src/main.py`

---

## 1. Architectural Overview

CodeCortex supports two deployment modes, each with a distinct Node ↔ Python relationship:

```
┌─────────────────────────────────────────────────────────┐
│                    MODE: SHARED (HTTP/SSE)                │
│                                                         │
│  IDE-A (Trae)           IDE-B (Cursor)                  │
│   ┌──────────┐          ┌──────────┐                    │
│   │index.cjs │          │index.cjs │                    │
│   │stdio←→RPC│          │stdio←→RPC│                    │
│   └────┬─────┘          └────┬─────┘                    │
│        │ HTTP/SSE            │ HTTP/SSE                 │
│        └──────────┬──────────┘                          │
│                   ▼                                      │
│        ┌──────────────────────┐                          │
│        │  Python MCP Server   │ ◄── Satu instance        │
│        │  (src/main.py)       │     untuk semua IDE      │
│        └──────────────────────┘                          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                   MODE: STDIO (Standalone)                │
│                                                         │
│  IDE                                                        │
│   ┌──────────┐                                            │
│   │run_serv- │── spawn ──► Python (src/main.py)           │
│   │er.js     │         stdio tunnel                       │
│   └──────────┘                                            │
└─────────────────────────────────────────────────────────┘
```

| Aspek | Shared Mode | Stdio Mode |
|-------|-------------|------------|
| Transport | HTTP/SSE (`CODECORTEX_TRANSPORT=sse`) | stdio (default) |
| Node wrapper | `index.cjs` | `run_server.js` |
| Python instances | 1 untuk semua IDE | 1 per IDE |
| Lifecycle manager | `index.cjs` (file lock + refCount) | IDE langsung |
| PID kill-loop | **Skip** — biar Node manage | Full safeguard |

---

## 2. Instance Identity & PID Handshake

### 2.1 Lockfile Format (JSON v2)

Kunci komunikasi 2 arah: `~/.codecortex/codecortex.pid`

Python dan Node sama-sama nulis lockfile dengan format yang sama. Siapa pun yang start duluan bisa baca status instance lain.

```json
{
  "pid": 35712,
  "signature": "codecortex-src.main-C:\\Users\\...\\mcp-codecortex",
  "source": "python",
  "instance_id": "e6a6b7365ded",
  "ide": "vscode",
  "pid_timestamp": 1718000000.123,
  "version": 2,
  "shared_mode": true,
  "node_parent_pid": 12345
}
```

| Field | Type | Description |
|-------|------|-------------|
| `pid` | int | Process ID of the instance |
| `signature` | str | Identifies the code location (file path hash) |
| `source` | str | `"python"` or `"node"` |
| `instance_id` | str | SHA-256 hash (12 chars) — unique per process, stable for lifetime |
| `ide` | str | Detected IDE: `trae`, `cursor`, `vscode`, `unknown` |
| `pid_timestamp` | float | Epoch time when this identity was created |
| `version` | int | Lockfile format version (currently 2) |
| `shared_mode` | bool | True jika ini shared HTTP/SSE server |
| `node_parent_pid` | int\|null | PID of the Node.js parent (Python only) |

### 2.2 Python → Node Handshake

**Python writes lockfile at startup** via `_build_instance_identity()` + `_safeguard_instance()`:

```python
# src/main.py — Lockfile written with full identity
pid_file.write_text(json.dumps(identity, indent=2))
# → ~/.codecortex/codecortex.pid
```

### 2.3 Node → Python Handshake

**Node writes lockfile after spawning Python** via `writeNodeLockfile()`:

```javascript
// scripts/server/run_server.js
// Node records the Python child PID + its own identity
writeNodeLockfile(child.pid);
// → ~/.codecortex/codecortex.pid (overwrites with Node's view)
```

### 2.4 Mutual Recognition

Both sides use `instance_id` untuk saling kenal:
- Python: skip killing jika lockfile PID adalah dirinya sendiri (`data.get("pid") == os.getpid()`)
- Node: skip killing jika lockfile instance_id miliknya sendiri (`lock.instance_id === _NODE_INSTANCE_ID`)

---

## 3. Lifecycle Management

### 3.1 Shared Mode (Multi-IDE)

`index.cjs` manages lifecycle dengan **file lock + reference counting**:

```
1. index.cjs start
2. tryAcquireLock()  ← atomic file lock (SERVER_LOCK_PATH)
3. readServerState() ← read existing server state (refCount, baseUrl)
4. IF server alive AND auth OK:
     → refCount++ , connect via HTTP/SSE
   ELSE:
     → spawn Python(fork) on candidate port
     → write state: {pid, baseUrl, refCount: 1}
5. releaseLock()
```

**Shutdown (terminateWrapper)**:
```
1. tryAcquireLock()
2. readServerState() → refCount--
3. IF refCount > 0:
     → write state, exit
   ELSE:
     → kill Python child (SIGTERM)
     → delete server state file
     → exit
```

### 3.2 Stdio Mode (Single IDE)

`run_server.js` manages simpler lifecycle:

```
1. handleStaleInstance() ← check lockfile, kill orphan Python
2. spawn Python (stdio tunnel)
3. writeNodeLockfile(child.pid) ← record identity
4. on child exit: clearLockfile(), exit
```

### 3.3 Reference Counting

File: `database/config/codecortex_shared_server.json`

```json
{
  "prd_id": "mcp-codecortex-20251024",
  "pid": 81345,
  "baseUrl": "http://127.0.0.1:8001",
  "startedAt": "2026-06-13T15:00:00.000Z",
  "refCount": 2
}
```

- **Increment**: setiap `index.cjs` baru connect ke server existing
- **Decrement**: setiap `index.cjs` disconnect (IDE tab closed)
- **Zero → shutdown**: last client disconnect triggers Python process kill

---

## 4. Cascade Prevention

### 4.1 Three Guards in `_safeguard_instance()`

#### Guard 0: Killed-PID Cache
File: `~/.codecortex/codecortex.killed`

```json
{"12345": 1718000000.0, "67890": 1718000001.5}
```

- Cache file persist di disk — survives process restart
- PID yang udah dibunuh <30 detik lalu **tidak dibunuh lagi**
- Mencegah cascade loop: `spawn → kill → crash → spawn → kill again`

```python
if pid in killed_cache:
    continue  # skip, already killed recently
```

#### Guard 1: Process Age
- Skip killing process yang umurnya <3 detik
- Mencegah shared server candidate pool saling bunuh

```python
if _is_process_younger_than(pid, seconds=3.0):
    continue  # too young, probably another candidate
```

#### Guard 2: Node.exe Parent Check
- Skip killing process yang parent-nya `node.exe`
- Mencegah `run_server.js` atau `index.cjs` spawn dibunuh oleh Python

```python
if _is_spawned_by_node(pid):
    continue  # legitimate IDE-spawned process
```

### 4.2 Shared Mode Bypass

Saat `CODECORTEX_TRANSPORT=sse` atau `http`, **seluruh kill-loop dilewati**:

```python
if shared_mode:
    # Only write lockfile, do NOT kill other Python PIDs
    # Lifecycle is managed by index.cjs file lock + refCount
    pid_file.write_text(json.dumps(identity))
    return
```

---

## 5. IDE Detection

Python dan Node sama-sama detect IDE dari environment variables:

| Priority | Variable | IDE |
|----------|----------|-----|
| 1 | `TRAE_ID` | trae |
| 2 | `VSCODE_NLS_CONFIG` | vscode |
| 3 | `TERM_PROGRAM=cursor` | cursor |
| 4 | `TERM_PROGRAM=trae` | trae |
| 5 | Fallback | `unknown` |

---

## 6. Process Tree Traversal

Python uses PowerShell `Get-CimInstance` to traverse process trees:

```python
# Trace parent chain (max 3 levels)
PID=35712 (python)
  ├── parent: PID=34120 (node.exe)    ← index.cjs / run_server.js
  │     ├── grandparent: PID=33010 (node.exe)  ← IDE process
  │     │       └── great-grandparent: PID=1 (System)
```

Jika parent `node.exe` sudah mati (orphan) → process dianggap stale dan siap dibunuh.

---

## 7. Sequence Diagram

### Multi-IDE Handshake (Shared Mode)

```
IDE-A (Trae)              IDE-B (Cursor)            Python (Shared)
    │                         │                         │
    │ spawn index.cjs         │                         │
    ├──── file lock ──────────┤                         │
    ├──── port 8001? ─────────┤                         │
    ├──── spawn ──────────────┼──── sse ───────────────►│
    │                         │                         │
    │                         │ spawn index.cjs         │
    │                         ├──── file lock ──────────┤
    │                         ├──── read state ─────────┤
    │                         ├──── connect ────────────┤
    │                         │       HTTP/SSE          │
    │                         │                         │
    │ [close tab]             │                         │
    ├──── file lock ──────────┤                         │
    ├──── refCount-- = 1 ─────┤                         │
    ├──── exit ───────────────┤                         │
    │                         │                         │
    │                         │ [close tab]             │
    │                         ├──── file lock ──────────┤
    │                         ├──── refCount-- = 0 ─────┤
    │                         ├──── kill Python ────────►│
    │                         │       SIGTERM            │
    │                         │                         │
```

### Stdio Mode (Single IDE)

```
IDE                          run_server.js              Python
 │                                │                        │
 │── spawn ──────────────────────►│                        │
 │                                ├── handleStaleInstance()│
 │                                ├── spawn ──────────────►│
 │                                │                        ├── _safeguard_instance()
 │                                │                        ├── PID cache check
 │                                │                        ├── kill stale PIDs
 │                                │                        ├── write lockfile
 │                                │                        ├── FastMCP ready
 │                                ├── writeNodeLockfile() │
 │                                │                        │
 │── JSON-RPC over stdio ────────►│── HTTP ───────────────►│
 │◄───────────────────────────────│◄───────────────────────│
```

---

## 8. File Reference

| File | Peran |
|------|-------|
| `src/main.py` | Python MCP server entry. `_safeguard_instance()` untuk single-instance enforcement |
| `scripts/server/js/index.cjs` | Multi-IDE HTTP/SSE proxy. File lock + refCount + candidate spawning |
| `scripts/server/run_server.js` | Single-IDE stdio wrapper. PID handshake + lockfile cleanup |
| `~/.codecortex/codecortex.pid` | JSON lockfile (instance identity, shared by Node & Python) |
| `~/.codecortex/codecortex.killed` | JSON killed-PID cache (cascade prevention) |
| `database/config/codecortex_shared_server.json` | Shared server state (refCount, baseUrl, pid) |
| `database/config/codecortex_shared_server.lock` | Atomic file lock for concurrency |

---

## 9. Key Design Decisions

1. **JSON lockfile, not plain text** — memungkinkan rich identity (instance_id, ide, source, shared_mode) untuk mutual recognition
2. **Killed-PID cache di disk, not memory** — survives cascade crash-restart cycle
3. **Node writes lockfile too** — Python bisa tahu siapa parent Node-nya
4. **`instance_id` sebagai trust anchor** — bukan PID yang bisa reuse
5. **Shared mode bypass** — Python ga perlu ikut campur lifecycle kalo index.cjs yang manage
