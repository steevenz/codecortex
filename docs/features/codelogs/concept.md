# Codelogs: Log Management & Visualization

> **Domain:** Codelogs
> **Package:** `src/modules/codelogs/`
> **Version:** 2.0.0
> **AI Coder Impact:** 9/10 ⭐
> **Production Readiness:** 90% 🎯

## Business Context

Codelogs is the **log management and visualization layer** for CodeCortex — provides systematic log path discovery, comprehensive search, file operations (cleanup, rotate, validate), and rich graph visualization with anomaly detection, health assessment, and file-level metrics. It integrates as the 10th provider in the unified search system (`codecortex-codelogs`).

## Why This Exists

- **Multi-Source Discovery:** Discovers log files across 22 languages, 3 OS platforms, 5 web servers, 5 databases, and 8 local dev tools (Laragon, WAMP, XAMPP, MAMP, Valet, Sail, Docker)
- **Systematic Collection:** 9-phase algorithm ensures no log source is overlooked
- **Rich Visualization:** Error frequency, time trends, weekday distributions, growth rates, file size distributions, error-file correlation, and z-score anomaly spike detection
- **Health Assessment:** Computes a 0–100 health score based on error rate, recent errors, and anomaly spikes
- **Auto-Indexing:** Automatically discovers log files when no standard log roots are found — zero configuration required
- **Cross-Platform:** Full support for Linux, macOS (Darwin), and Windows with platform-specific paths
- **Local Dev Tool Detection:** Automatically finds Laragon, WAMP, XAMPP, MAMP logs on Windows; Laravel Valet/Sail logs on macOS/Linux; Docker logs across platforms
- **Standard Compliance:** Follows `logging-standard.md` (structured JSON) and `project-structure-standard.md` (`outputs/logs/`)

## Theoretical Foundation

- **Systematic Path Collection:** 9-phase algorithm increments paths from custom → standard → common → language → OS → server → database → dev tool → process with deduplication
- **Regex Parsing:** Multi-pattern regex for log levels (TRACE/DEBUG/INFO/WARN/ERROR/CRITICAL/FATAL) and timestamps (ISO-8601, syslog, IIS)
- **Z-Score Anomaly Detection:** Statistical outlier detection on hourly log volume using mean/standard deviation
- **Growth Rate Analysis:** Lines/errors/warnings per hour computed from timespan
- **File-Level Correlation:** Maps error counts to individual files for targeted debugging
- **Error Peak Detection:** Days where error percentage exceeds 50% of total log volume
- **CODDY Standard Paths:** `outputs/logs/{env}/[YYYY-MM-DD]/{type}.log`
- **GZip Support:** Transparent reading of `.gz` compressed logs
- **Rotated File Detection:** Recognizes `.0`–`.9` rotated log extensions
- **Health Scoring:** Weighted formula: 30% error rate + 30% recent errors + 40% anomaly spikes
- **Auto-Indexing Cache:** Single-attempt caching to avoid repeated discovery scans

## Architecture

```
src/modules/codelogs/
├── api/              → cli.py: 9 CLI commands (scan/search/graph/discover/cleanup/rotate/validate/info)
├── services/
│   ├── log_service.py     → LogService (scan, search, cleanup, rotate, validate)
│   │                       LogPathCollector (systematic path discovery, 9-phase algorithm)
│   └── loggraph_service.py → LogGraphService (generate, error_frequency, time_trend,
│                              summary, anomalies, files, health, discover)
└── __init__.py          → Package initialization with CODDY-Codelogs-v2.0 standard
```

Integration points:
- `src/api/tools.py` → MCP tool `codecortex:loggraph` (enhanced with discover, anomalies, files, health)
- `scripts/server/codelogs_api.py` → HTTP REST router `/v1/codelogs/*` (7 endpoints)
- `scripts/server/http.py` → registers codelogs_router
- `src/services/unified_search.py` → provider `codecortex-codelogs` (10th provider)

## Domain Boundary

- **Owns:** `codecortex:loggraph` (MCP tool), log CLI commands, log HTTP API
- **Does NOT own:** Filesystem operations (handled by Filesystem domain), code analysis (CodeAnalysis)
- **Depends on:** None (standalone module with config, errors, logging from core)
- **Consumed by:** MCP layer via `api/tools.py`, HTTP layer via `scripts/server/http.py`

## CLI Architecture Note

The CLI domain is named `log` (not `codelogs`) as an intentional UX decision. Users access all log operations via `codecortex log <command>`.

## ~/.aicoders/ Compliance

- **API Standard:** `api_response()` for all tool responses
- **DDD:** `api/` + `services/` separation
- **DI:** Constructor injection for LogService and LogGraphService
- **Boundary:** Data crosses layers only via DTOs (LogEntry, LogSearchFilter, LogGraphData)
- **Error Handling:** Guard clauses, structured errors
- **Logging:** `CodeCortex.Codelogs.*` logger namespace
- **Documentation:** All docs in `docs/features/codelogs/`
- **Standard:** CODDY-Codelogs-v2.0

## Log Path Discovery Algorithm (9 Phases)

```
Phase 1: Custom paths from user request (search_paths comma-separated)
Phase 2: CODDY CodeWorks standard project paths (outputs/logs/, outputs/debugs/)
Phase 3: Common log paths (logs/, log/, storage/logs/, var/log/, runtime/logs/, tmp/logs/)
Phase 4: Language-specific paths (22 languages detected)
Phase 5: OS-specific paths (Linux: /var/log, Windows: C:\Windows\Logs, Darwin: ~/Library/Logs)
Phase 6: Web server paths (nginx, apache, iis, tomcat, caddy)
Phase 7: Database paths (mysql, postgresql, mongodb, redis, elasticsearch, mssql)
Phase 8: Local dev tool paths (laragon, wamp, xampp, mamp, laravel_valet, laravel_sail, docker)
Phase 9: Process & deduplicate — grep, glob, regex filtering with dedup
```

Each phase uses file-existence signals for detection (e.g., `laragon.exe` for Laragon, `wampmanager.exe` for WAMP, `xampp-control.exe` for XAMPP, `MAMP.exe` for MAMP).

## Supported Languages (22)

php, python, javascript, typescript, java, kotlin, go, rust, ruby, csharp, dart, swift, c, cpp, scala, groovy, lua, perl, haskell, elixir, clojure, erlang

## Supported OS (3)

- **Linux:** /var/log + 14 system log paths
- **Windows:** C:\Windows\Logs, C:\Windows\System32\LogFiles, C:\Windows\System32\winevt\Logs, ProgramData, inetpub, TEMP, LOCALAPPDATA, APPDATA
- **Darwin (macOS):** /var/log, ~/Library/Logs, /Library/Logs, ~/Library/Application Support/logs

## Supported Servers (5)

nginx, apache, iis, tomcat, caddy

## Supported Databases (6)

mysql (incl. mariadb), postgresql, mongodb, redis, elasticsearch, mssql

## Supported Local Dev Tools (8)

laragon, wamp, xampp, mamp, laravel_valet, laravel_sail, docker

## Graph Visualization Metrics

| Metric | Description |
|--------|-------------|
| **Summary** | total_files, total_lines, time_window, errors_24h/1h, unique_errors, error_rate |
| **Level Distribution** | TRACE/DEBUG/INFO/WARN/ERROR/CRITICAL/FATAL counts |
| **Error Frequency** | Aggregate error, warning, info, debug, trace, critical, fatal totals |
| **Time Trend** | Hourly and daily bucket counts with ISO timestamps |
| **Weekday Distribution** | Log volume by day of week (Monday–Sunday) |
| **Growth Rate** | Lines/errors/warnings per hour over the timespan |
| **File Size Distribution** | 5 categories: tiny (<1KB), small (1–10KB), medium (10–100KB), large (100KB–1MB), huge (>1MB) |
| **File-Error Correlation** | Top 15 files ranked by error count |
| **Top Error Messages** | Top 20 most frequent error messages |
| **Anomaly Spikes** | Z-score >2.0 hourly spikes with severity (high >3.0, medium >2.0) |
| **Error Peaks** | Days where error percentage exceeds 50% |
| **Health Score** | 0–100 score with status: healthy (>=80), degraded (>=50), critical (<50) |

## Error Codes

| Prefix | Tool | Description |
|--------|------|-------------|
| CODELOGS_0xx | loggraph | General errors |
| CODELOGS_001 | discover | Project root not set |
| CODELOGS_002 | search | Invalid search parameters |
| CODELOGS_003 | cleanup | Cleanup failed |
| CODELOGS_004 | validate | Invalid log file format |
| CODELOGS_5xx | general | Internal error |

## 9/10 AI Coder Impact Features

1. **Systematic Log Discovery** — 9-phase algorithm finds logs across 22 languages + OS + servers + databases + dev tools
2. **Auto-Indexing** — Zero-config discovery when no standard log roots exist
3. **Rich Graph Visualization** — 11 metric categories including anomaly detection and health scoring
4. **Comprehensive Search** — Filter by log level, date range, query string, file pattern
5. **File Operations** — Safe cleanup (dry-run by default) and rotation
6. **Local Dev Tool Detection** — Laragon, WAMP, XAMPP, MAMP, Valet, Sail, Docker logs automatically found
7. **Unified Search Integration** — 10th provider in `codecortex:search` with log-specific params
8. **Cross-Platform** — Linux, macOS, Windows with platform-specific paths
9. **GZip + Rotated Files** — Transparent reading of `.gz` compressed and `.0`–`.9` rotated logs

## Token Economy

All responses pass through `api_response()` which auto-truncates data exceeding token budget when `summary_mode=True`. The `discover` action limits results to 200 (configurable via `max_results`). The `generate` method caps file scanning at `max_files` (default 50).

---

## Related Sub-Features

- [Scan](sub-features/scan/concept.md) — List and discover log files
- [Search](sub-features/search/concept.md) — Filter logs by level, date, query
- [Graph](sub-features/graph/concept.md) — Error frequency, time trends, health, anomalies
- [Discover](sub-features/discover/concept.md) — Systematic log file discovery across sources
- [Health](sub-features/health/concept.md) — Health score and status assessment
- [Cleanup](sub-features/cleanup/concept.md) — Remove old log files
- [Rotate](sub-features/rotate/concept.md) — Rotate oversized log files
- [Validate](sub-features/validate/concept.md) — Validate log file format
- [Info](sub-features/info/concept.md) — Configured directories and detection diagnostics

## Tool Reference

### codecortex:loggraph (Unified MCP Tool)

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | `summary` | See actions below |
| `days` | int | ❌ | `7` | Time window in days |
| `path` | string | ❌ | — | Project root path to scan |
| `file_pattern` | string | ❌ | `*.log` | Log file glob pattern |
| `granularity` | string | ❌ | `hourly` | `hourly` or `daily` |
| `max_files` | int | ❌ | `50` | Max files to scan |
| `search_paths` | string | ❌ | — | Comma-separated additional paths |
| `detect_language` | bool | ❌ | `true` | Enable language detection |
| `detect_os` | bool | ❌ | `true` | Enable OS detection |
| `detect_servers` | bool | ❌ | `true` | Enable server detection |
| `detect_databases` | bool | ❌ | `true` | Enable database detection |
| `detect_dev_tools` | bool | ❌ | `true` | Enable local dev tool detection |
| `max_results` | int | ❌ | `200` | Max results for discover |

**Actions:**
- `summary` — Full summary with level distribution, error frequency, top messages
- `error-frequency` — Error frequency by level
- `time-trend` — Trend over time (hourly or daily)
- `scan` — List all log files in configured directories
- `discover` — Discover log files via systematic path collection
- `anomalies` — Spike detection and anomaly analysis (z-score)
- `files` — File-level metrics (size distribution, error correlation, growth)
- `health` — Log health assessment with health score (0–100)
- `info` — Show configured log directories and detection diagnostics

**Output (summary):**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Full summary for last 7 days",
  "data": {
    "summary": {
      "total_files": 15,
      "total_lines": 1250,
      "time_window_days": 7,
      "errors_last_24h": 3,
      "errors_last_1h": 0,
      "unique_error_messages": 12,
      "error_rate_percent": 4.2,
      "warning_rate_percent": 8.1,
      "files_with_errors": 5,
      "timespan": {
        "first_log": "2026-06-10T08:00:00+00:00",
        "last_log": "2026-06-17T14:30:00+00:00"
      }
    },
    "error_frequency": { "total_errors": 53, "total_warnings": 101, ... },
    "level_distribution": { "INFO": 800, "DEBUG": 296, ... },
    "top_error_messages": [ ... ],
    "anomaly_spikes": [ ... ],
    "growth_rate": { "lines_per_hour": 7.4, ... }
  },
  "meta": { "request_id": "req_abc", "timestamp": "..." }
}
```

---

## CLI Commands

### codecortex log

**Commands:**
- `scan [--path] [--search-paths]` — List all log files
- `search <query> [--level] [--date-from] [--date-to] [--path] [--search-paths]` — Search logs with filters
- `graph [--days] [--path] [--search-paths]` — Generate graph visualization
- `discover [--path] [--search-paths] [--no-lang-detect] [--no-os-detect] [--no-server-detect] [--no-db-detect] [--no-dev-tool-detect]` — Discover log files across all sources
- `cleanup [--days] [--apply] [--path] [--search-paths]` — Remove old logs (dry-run default)
- `rotate [--max-size] [--keep] [--apply] [--path]` — Rotate oversized logs (dry-run default)
- `validate <file> [--path]` — Validate log file format
- `info [--path]` — Show configured directories and detection info

**Example:**
```bash
codecortex log discover --no-db-detect --no-server-detect --path /var/www/myapp
codecortex log search "RuntimeError" --level ERROR --date-from 2026-06-01 --path /var/www/myapp
codecortex log graph --days 30 --path /var/www/myapp
codecortex log health --path /var/www/myapp
```

---

## HTTP API

**Base:** `POST /v1/codelogs/{action}`

| Endpoint | Description |
|----------|-------------|
| `POST /v1/codelogs/scan` | List log files |
| `POST /v1/codelogs/search` | Search log entries |
| `POST /v1/codelogs/graph` | Generate graph visualization |
| `POST /v1/codelogs/discover` | Discover log files |
| `POST /v1/codelogs/health` | Health assessment |
| `POST /v1/codelogs/cleanup` | Cleanup old logs |
| `POST /v1/codelogs/info` | Detection diagnostics |

---

## Production Readiness Assessment

**Current Status:** 90% 🎯

**Strengths:**
- ✅ Unified MCP tool with 9 comprehensive actions
- ✅ CLI commands for all operations with api_response() compliance
- ✅ Systematic 9-phase log path discovery algorithm
- ✅ Comprehensive graph visualization (11 metric categories)
- ✅ Auto-indexing with single-attempt caching
- ✅ Constructor DI pattern
- ✅ Cross-platform support (Linux, macOS, Windows)
- ✅ Local dev tool detection (8 tools)
- ✅ GZip + rotated file support
- ✅ HTTP REST API (7 endpoints)
- ✅ Unified search integration (10th provider)
- ✅ Dry-run safety for destructive operations
- ✅ AllowedLogRoots with path traversal prevention
- ✅ 12 unit tests passing

**Gaps:**
- ⬜ Sub-feature documentation (concept.md is master document)
- ⬜ No dedicated API spec doc
- ⬜ Limited test coverage (12 tests — more needed for edge cases)
