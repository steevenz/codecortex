# Codelogs — Log Management & Visualization

**Version**: 2.0.0
**Last Updated**: 2026-06-17

---

## Overview

The Codelogs module provides systematic log file discovery, search, visualization, and maintenance with support for:

- Log file scanning and discovery across 22 languages + OS + servers + databases + local dev tools
- Full-text search with level, date range, and file pattern filters
- Graph visualization: error frequency, time trends, anomaly spikes, health assessment
- File operations: cleanup (with dry-run), rotation, format validation
- Auto-indexing when no standard log directories are found
- Local dev tool detection: Laragon, WAMP, XAMPP, MAMP, Laravel Valet, Sail, Docker

---

## Directory Structure

```
project-root/
├── outputs/
│   └── logs/                       # Standard log directory (per project-structure-standard)
│       ├── development/
│       ├── sandbox/
│       └── production/
├── logs/                           # Common log directory
├── storage/logs/                   # Framework log directory
├── var/log/                        # System log directory
├── src/modules/codelogs/
│   ├── __init__.py
│   ├── module.json                 # Module manifest v2.0.0
│   ├── api/
│   │   └── cli.py                  # 9 CLI commands
│   └── services/
│       ├── log_service.py          # LogService + LogPathCollector
│       └── loggraph_service.py     # LogGraphService
└── docs/features/codelogs/
    ├── concept.md                  # Full documentation (this feature)
    └── README.md                   # This file
```

---

## Configuration

### Module Manifest (`module.json`)

| Field | Value |
|-------|-------|
| name | `codelogs` |
| version | `2.0.0` |
| allowed_log_roots | `logs`, `outputs/logs`, `storage/logs`, `log`, `outputs/debugs` |
| max_file_size_mb | `10` |
| blocked_paths | `/etc`, `/proc`, `/sys`, `/dev`, `C:\Windows`, `C:\System32` |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGS_MAX_FILES` | `50` | Max files to scan in graph |
| `LOGS_MAX_RESULTS` | `200` | Max results for discover/search |
| `LOGS_CLEANUP_DAYS` | `30` | Default cleanup age |
| `LOGS_ROTATE_MAX_SIZE` | `50` | Max size in MB before rotation |
| `LOGS_ROTATE_KEEP` | `5` | Rotated backups to keep |

---

## Available Actions

### codecortex:loggraph (MCP Tool)

```python
# Summary
result = await loggraph(action="summary", days=7, path="/project")

# Discover logs across all sources
result = await loggraph(action="discover", path="/project",
                        detect_dev_tools=True, detect_language=True)

# Health assessment
result = await loggraph(action="health", days=30, path="/project")

# Anomaly detection
result = await loggraph(action="anomalies", days=7, path="/project")

# File-level metrics
result = await loggraph(action="files", path="/project")
```

### CLI

```bash
# Discover logs
codecortex log discover --path /project --no-db-detect

# Search for errors
codecortex log search "RuntimeError" --level ERROR --path /project --search-paths "/custom/logs"

# Graph visualization
codecortex log graph --days 30 --path /project

# Health check
codecortex log health --path /project

# Cleanup old logs (dry-run by default)
codecortex log cleanup --days 60 --apply
```

---

## Log Path Discovery

Codelogs uses a 9-phase systematic algorithm:

| Phase | Source | Example Paths |
|-------|--------|---------------|
| 1 | Custom paths | User-specified comma-separated paths |
| 2 | CODDY standard | `outputs/logs/development/`, `outputs/debugs/` |
| 3 | Common | `logs/`, `log/`, `storage/logs/`, `var/log/` |
| 4 | Language | `runtime/logs/` (PHP), `.next/logs/` (JS) |
| 5 | OS | `/var/log` (Linux), `C:\Windows\Logs` |
| 6 | Servers | `/var/log/nginx/`, `/var/log/apache2/` |
| 7 | Databases | `/var/log/mysql/`, `/var/log/postgresql/` |
| 8 | Dev tools | `C:\laragon\logs\`, `C:\xampp\apache\logs\` |
| 9 | Process | Dedup, glob, grep, regex filtering |

---

## Graph Metrics

| Metric | Description |
|--------|-------------|
| Summary | Counts, rates, timespan |
| Level Distribution | Log level counts |
| Error Frequency | Aggregated error totals |
| Time Trend | Hourly/daily buckets |
| Weekday Distribution | Volume by day of week |
| Growth Rate | Lines/errors per hour |
| File Size Dist | 5 size categories |
| File-Error Corr | Top error files |
| Top Error Messages | Frequency-ranked |
| Anomaly Spikes | Z-score > 2.0 |
| Error Peaks | Days >50% errors |
| Health Score | 0–100 weighted score |

---

## Error Codes

| Code | Description |
|------|-------------|
| CODELOGS_001 | Project root not set |
| CODELOGS_002 | Invalid search parameters |
| CODELOGS_003 | Cleanup failed |
| CODELOGS_004 | Invalid log file format |
| CODELOGS_500 | Internal error |

---

## Performance Standards

| Operation | Max Latency | Target |
|-----------|-------------|--------|
| scan | 500ms | < 200ms |
| search | 1000ms | < 500ms |
| graph | 3000ms | < 1000ms |
| discover | 2000ms | < 1000ms |
| health | 2000ms | < 500ms |
| cleanup | 1000ms | < 500ms |

---

## Maintenance Procedures

### Daily
- Run health check via `codecortex log health`

### Weekly
- Scan for new log directories via `codecortex log discover`
- Review anomaly spikes via `codecortex log anomalies`

### Monthly
- Cleanup old logs via `codecortex log cleanup --days 90 --apply`
- Rotate oversized logs via `codecortex log rotate --max-size 100 --apply`

---

## Support

For issues, check the module log at `CodeCortex.Codelogs.*` logger namespace or contact the CodeCortex development team.
