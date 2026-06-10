# repo_analyze: Full Semantic Analysis

> **Tool:** repo_analyze
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Full semantic analysis — AST parsing, graph building (calls/imports/inherits), VCS integration (churn, bug magnets), complexity metrics, and entry point detection. Heavyweight operation that enables search & refactor.

## Why This Exists

- **Deep Understanding:** Extracts symbols, call graphs, and dependency graphs
- **Bug Magnet Detection:** Identifies frequently modified files (when integrated with repo_history)
- **Complexity Metrics:** Cyclomatic complexity, coupling, inheritance depth
- **Entry Point Detection:** Identifies main entry points (main(), CLI, web routes)
- **Search Enablement:** Builds embeddings for semantic search
- **Refactor Support:** Provides data for code refactoring operations

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to repository |
| `build_graph` | bool | ❌ | `true` | Build call/dependency graphs |
| `store_embeddings` | bool | ❌ | `false` | Store semantic embeddings for search |
| `force` | bool | ❌ | `false` | Force re-analysis even if cached |
| `incremental` | bool | ❌ | `true` | Only analyze changed files (mtime-based) |

## Output

```json
{
  "repo_id": "uuid-v7",
  "repo_path": "/absolute/path",
  "analysis_summary": {
    "symbols_extracted": 450,
    "classes": 25,
    "functions": 200,
    "edges": 300
  },
  "complexity_metrics": {
    "avg_cyclomatic": 3.5,
    "max_cyclomatic": 15,
    "coupling_score": 0.4
  },
  "entry_points": [
    {"file": "src/main.py", "function": "main", "type": "cli"}
  ],
  "ai_actions": [
    {
      "priority": "info",
      "action": "Analysis complete: 450 symbols extracted, 300 edges built.",
      "status": "completed"
    },
    {
      "priority": "medium",
      "action": "High complexity detected in 3 files. Consider refactoring.",
      "files": ["src/payment.py", "src/auth.py"]
    }
  ]
}
```

## AI Actions

1. **Analysis Summary** — Symbol and edge counts
2. **Complexity Alerts** — High complexity file warnings
3. **Entry Points** — Main entry points identification
4. **Next Steps** — Suggests code_search, code_refactor

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_404 | 404 | Repository not indexed |
| REP_500 | 500 | Analysis failed |

## Integration

- **repo_inspect** — For quick health check before analysis
- **repo_history** — For bug magnet detection (commits linked to bugs)
- **code_search** — For semantic search using embeddings
- **code_refactor** — For refactoring operations
