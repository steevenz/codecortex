# Entry Point Scoring

> **Source:** Integrated into `CodeGraphService`

## Concept

Entry point scoring assigns a 0-100 score to each function indicating how likely it is to be a system entry point — an HTTP handler, CLI command, event listener, or public API surface. This helps LLMs identify the "front doors" of a codebase.

## Scoring Criteria

| Factor | Weight | Description |
|--------|--------|-------------|
| **Call Ratio** | 40% | Ratio of incoming to outgoing calls. Entry points have many callers (or none if dead). |
| **Naming** | 25% | Names matching patterns: `handle_*`, `*_handler`, `*_action`, `*_command`, `main`, `run` |
| **Framework Signals** | 20% | Decorated with route decorators, CLI commands, event listeners |
| **File Location** | 10% | Located in `api/`, `handlers/`, `commands/`, `controllers/` directories |
| **Module Visibility** | 5% | Exported/public vs private |

## Score Interpretation

| Score Range | Classification | Description |
|-------------|---------------|-------------|
| 80-100 | **Entry Point** | HTTP route, CLI command, event handler |
| 50-79 | **Public API** | Exported service function, repository method |
| 20-49 | **Internal Logic** | Helper function, private method |
| 0-19 | **Dead Code** | No callers, no exports |

## Output

```json
{
  "top_entry_points": [
    {"name": "app.main", "score": 95, "file": "src/main.py:1", "type": "function"},
    {"name": "create_user_handler", "score": 88, "file": "src/api/users.py:25", "type": "function"},
    {"name": "main", "score": 92, "file": "src/cli.py:10", "type": "function"}
  ]
}
```
