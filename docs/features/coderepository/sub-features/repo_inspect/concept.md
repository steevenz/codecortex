# repo_inspect: Fast Health Check

> **Tool:** repo_inspect
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Fast health check for repositories — metadata, VCS diagnostics (churn, bus factor, velocity), file stats, dependency summary, and AI readiness score. Zero parsing — no AST, no file content reading.

## Why This Exists

- **Instant Assessment:** Provides repository health in < 2s without heavy parsing
- **VCS Diagnostics:** Churn, bus factor, velocity metrics for team insights
- **AI Readiness:** Scores repository readiness for AI-assisted development
- **Dependency Summary:** Quick overview of external dependencies
- **Zero Overhead:** No AST parsing or file content reading

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to repository |
| `include_git_diagnostics` | bool | ❌ | `true` | Include VCS metrics (churn, bus factor, velocity) |
| `include_file_stats` | bool | ❌ | `true` | Include file statistics (counts, languages) |
| `diagnostic_period` | string | ❌ | `30d` | Time period for VCS diagnostics (e.g., "30d", "90d") |
| `output_format` | string | ❌ | `json` | "json" or "markdown" |

## Output

```json
{
  "repo_id": "uuid-v7",
  "repo_path": "/absolute/path",
  "metadata": {
    "name": "myproject",
    "created_at": "2026-01-01T00:00:00Z",
    "sync_at": "2026-05-29T10:00:00Z"
  },
  "file_stats": {
    "total_files": 150,
    "source_files": 120,
    "languages": {"python": 80, "javascript": 40}
  },
  "git_diagnostics": {
    "churn_rate": 0.25,
    "bus_factor": 3,
    "velocity": 15.5,
    "period": "30d"
  },
  "ai_readiness_score": 85,
  "ai_actions": [
    {
      "priority": "info",
      "action": "Repository health score: 85/100. Good for AI-assisted development."
    }
  ]
}
```

## AI Actions

1. **Health Score** — AI readiness assessment with recommendations
2. **VCS Insights** — Churn, bus factor, velocity metrics interpretation
3. **Dependency Summary** — External dependency overview
4. **Next Steps** — Suggests repo_analyze for deeper analysis

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_404 | 404 | Repository not indexed |
| REP_500 | 500 | Internal error during inspection |

## Integration

- **repo_analyze** — For full semantic analysis
- **repo_staleness** — For VCS sync status
- **repo_audit** — For security assessment
