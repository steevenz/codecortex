# Auto-Update System

> **Concept**: Background version checking against GitHub Releases, AI-detectable update signals, and self-update via `git pull`.

---

## 1. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Auto-Updater Service                         │
│                                                               │
│  CodeCortexUpdater (threading.Thread, daemon)                  │
│  ┌─────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │ Version Checker  │  │ Update Signal  │  │ Updater (pull) │ │
│  │ - GitHub API     │→│ - signal.json  │→│ - git fetch     │ │
│  │ - .version file  │  │ - update.json  │  │ - git merge    │ │
│  │ - semver compare │  │ - notify AI    │  │ - uv sync      │ │
│  └─────────────────┘  └────────────────┘  └────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
   ~/.coddy/codecortex/       github.com/steevenz/mcp-codecortex
   update_signal.json         /releases/latest
   update.json
```

### Layers

| Layer | File | Peran |
|-------|------|-------|
| **Background thread** | `src/core/update/updater.py` | Daemon thread, periodic check (default 1h), connectivity validation, exponential backoff |
| **Signal file** | `~/.coddy/codecortex/update_signal.json` | AI-readable signal — update_available, local_version, latest_version, release_url |
| **Metadata** | `~/.coddy/codecortex/update.json` | Last check timestamp, consecutive failures, versions comparison |
| **Version file** | `.version` (project root) | Single source of truth for current installed version |
| **MCP Tool** | `codecortex` → action: `update` | AI-triggered: check, status, signal, download, apply, dismiss |

---

## 2. Files & Locations

### `.version` (project root)
```
2.1.0
```

### `~/.coddy/codecortex/update_signal.json`
```json
{
  "update_available": true,
  "local_version": "2.1.0",
  "latest_version": "2.2.0",
  "release_url": "https://github.com/steevenz/mcp-codecortex/releases/tag/v2.2.0",
  "release_title": "v2.2.0 - Graph Performance Improvements",
  "release_notes": "## What's Changed\n- Optimized KuzuDB queries\n- Fixed cascade loop\n- ...",
  "signal_at": "2026-06-13T15:30:00.000Z",
  "dismissed": false
}
```

### `~/.coddy/codecortex/update.json`
```json
{
  "last_check_at": "2026-06-13T15:30:00.000Z",
  "local_version": "2.1.0",
  "latest_version": "2.2.0",
  "update_available": true,
  "error": null,
  "consecutive_failures": 0
}
```

---

## 3. Version Checking

### Connectivity Validation
Before any GitHub API call, the updater performs a lightweight `HEAD` request to `https://github.com`:

```python
def _internet_reachable(self) -> bool:
    req = urllib.request.Request("https://github.com", method="HEAD")
    with urllib.request.urlopen(req, timeout=8) as resp:
        return 200 <= resp.status < 500
```

Timeout: 8 seconds. Returns `False` without blocking the main thread.

### GitHub API Call
```
GET https://api.github.com/repos/steevenz/mcp-codecortex/releases/latest
```

Headers:
- `Accept: application/vnd.github+json`
- `User-Agent: CodeCortex-Updater/2.0`

Timeout: 15 seconds. Parses `tag_name`, `html_url`, `body` from response.

### Semver Comparison
```python
_parse_semver("2.1.0")  → (2, 1, 0)
_parse_semver("v2.2.0") → (2, 2, 0)
```

Tuple comparison: `(2, 2, 0) > (2, 1, 0)` → `update_available=True`

---

## 4. Retry & Backoff

| Failure Count | Wait Before Next Check |
|---------------|----------------------|
| 0 | 1 hour (default interval) |
| 1 | 30 seconds |
| 2 | 60 seconds |
| 3 | 120 seconds |
| 4+ | 3600 seconds (capped) |

Backoff formula: `min(BACKOFF_BASE * 2^failures, MAX_BACKOFF)`
- `BACKOFF_BASE` = 30s
- `MAX_BACKOFF` = 3600s

Consecutive failures reset to 0 on successful check.

---

## 5. AI Integration

### Auto-Detection via Signal File

AI agents can check `~/.coddy/codecortex/update_signal.json` at any time:

```
signal exists AND update_available=True AND not dismissed
    → AI: "There's a CodeCortex update available (v{latest}).
           Run `check` to see details."
```

### MCP Tool: `update`

| Action | Description | Destructive |
|--------|-------------|-------------|
| `check` | One-shot version check. Writes signal file. | No |
| `status` | Show last check result + current state | No |
| `signal` | Read the current signal file content | No |
| `dismiss` | Mark signal as read | Yes (state change) |
| `download` | `git fetch` from remote | Yes (network) |
| `apply` | `git merge --ff-only` + `uv sync` | Yes (files) |

### Suggested AI Workflow

```
AI detects signal → "Update v2.2.0 available. Apply now?"
User: "yes"
AI → update check
AI → update download
AI → update apply
AI → "Update applied. Restart recommended."
```

---

## 6. Background Daemon

- **Thread type**: `threading.Thread(daemon=True)`
- **Start**: `CortexOrchestrator.__init__()` → `CodeCortexUpdater(auto_start=True)`
- **Initial check**: 10 seconds after server start
- **Interval**: 3600 seconds (1 hour), configurable via `check_interval` param
- **Stop**: Thread auto-exits when Python process terminates (daemon=True)

### Resource Usage
- **CPU**: Near zero between checks. `time.sleep()` in 5-second increments.
- **Network**: One `HEAD` + one `GET` per check (only when interval elapses).
- **Memory**: ~500KB for `CodeCortexUpdater` instance + daemon thread stack.

---

## 7. Update Lifecycle

```
IDLE
 │
 │ [interval elapsed or check() called]
 ▼
CHECKING ──► internet? ──NO──► ERROR
 │                │
 │               YES
 │                │
 ▼                ▼
GitHub API    VersionCheckResult
 │            (cached in memory)
 │                │
 │         ┌──────┴──────┐
 │         ▼              ▼
 │    update? YES    NO (up-to-date)
 │         │              │
 │   ┌─────┘              │
 │   ▼                    │
 │ UPDATE_AVAILABLE       │
 │ write signal.json ─────┘
 │
 │ [AI calls download()]
 ▼
DOWNLOADING ──► git fetch
 │                  │
 │             ┌────┴────┐
 │             ▼         ▼
 │          OK?       FAIL
 │             │         │
 │        UPDATE_     ERROR
 │        AVAILABLE
 │
 │ [AI calls apply()]
 ▼
APPLYING ──► git merge --ff-only
 │               │
 │          ┌────┴────┐
 │          ▼         ▼
 │        OK?       FAIL
 │           │         │
 │      uv sync →  ERROR
 │           │
 │      .version
 │      dismiss signal
 │           │
 │      UP_TO_DATE
 │      (restart recommended)
```

---

## 8. Error Handling

| Scenario | Behavior |
|----------|----------|
| No internet | `_internet_reachable()` returns `False` → error result, no crash |
| GitHub API timeout | `urllib.error.URLError` → caught, error in `VersionCheckResult` |
| GitHub rate limit | `429` → retry eligible via `RETRY_CODES` |
| Git not available | `subprocess.CalledProcessError` → `download()` returns `False` |
| Merge conflict | `git merge --ff-only` fails (no conflict possible with FF-only) → error |
| `uv sync` failure | `CalledProcessError` → `apply()` returns `False` |
| Thread crash | Daemon thread dies silently, main process unaffected |

---

## 9. Testing

### Unit Test
```bash
# Test version parse
python -c "
from src.core.update.updater import CodeCortexUpdater
u = CodeCortexUpdater()
assert u._parse_semver('2.1.0') == (2, 1, 0)
assert u._parse_semver('v2.2.0') == (2, 2, 0)
assert u._compare_versions('2.1.0', '2.2.0') == True
assert u._compare_versions('2.2.0', '2.1.0') == False
print('Version compare OK')
"
```

### Signal File Test
```bash
python -c "
from src.core.update.updater import CodeCortexUpdater
u = CodeCortexUpdater(auto_start=False)
signal = u.get_signal()
print(f'Signal: {signal.to_dict() if signal else \"None\"}')
"
```

### Full Check (needs internet)
```bash
python -c "
from src.core.update.updater import CodeCortexUpdater
u = CodeCortexUpdater(auto_start=False)
result = u.check()
print(f'Local: {result.local_version}, Latest: {result.latest_version}')
print(f'Update available: {result.update_available}')
print(f'Error: {result.error}')
"
```

### MCP Tool Test (via server)
```
codecortex update action=check
codecortex update action=status
codecortex update action=signal
```

---

## 10. Python Dependencies

The auto-updater uses **only standard library modules**:

| Module | Usage |
|--------|-------|
| `threading` | Background daemon thread |
| `urllib.request` | GitHub API + connectivity checks |
| `urllib.error` | Error handling |
| `subprocess` | `git fetch`, `git merge`, `uv sync` |
| `json` | Signal file + metadata |
| `time` | Interval sleep, timestamps |
| `dataclasses` | `VersionCheckResult`, `UpdateSignal` |
| `pathlib` | File paths |
| `logging` | Structured logging |
| `enum` | `UpdateStatus` |

**No third-party dependencies required.**
