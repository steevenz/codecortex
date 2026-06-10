# code_tester: run

> **Action:** `run`
> **Tool:** `code_tester`

## Purpose

Execute tests using the auto-detected or specified test framework. Returns structured results with pass/fail counts, individual test details, and execution duration.

## Why It Exists

AI coders need to verify code changes don't break existing functionality. Running tests and getting structured results enables automated decision-making about code quality.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | string | Yes | "run" | Must be "run" |
| `target_path` | string | Yes | - | Path to project or test directory/file |
| `test_framework` | string | No | "auto" | Framework name or "auto" for detection |
| `test_filter` | string | No | null | Filter expression (marker, pattern, name) |
| `test_names` | list[string] | No | null | Specific test names to run |
| `categories` | list[string] | No | null | Test categories (unit, integration, e2e) |
| `max_duration` | int | No | 300 | Max execution time in seconds (10-600) |
| `async_mode` | boolean | No | false | Run in background (returns task_id) |
| `follow` | boolean | No | false | Wait for async completion |

## Output Format

```json
{
  "action": "run",
  "target_path": "/project",
  "framework": "pytest",
  "duration_seconds": 5.2,
  "summary": {
    "total": 50,
    "passed": 45,
    "failed": 2,
    "skipped": 3,
    "errors": 0
  },
  "results": [
    {
      "name": "test_auth_success",
      "file": "tests/test_auth.py",
      "line": 45,
      "status": "passed",
      "duration_ms": 12.3
    }
  ],
  "test_run_id": "tr_20260525_143022"
}
```

## Use Cases

- **Verify Changes:** Run all tests after code modifications
- **Selective Testing:** Run only tests matching specific markers or names
- **Category Filtering:** Run only unit or integration tests
- **Background Execution:** Start tests in background for long-running suites

## Examples

### Run all tests with auto-detection
```json
{
  "action": "run",
  "target_path": "tests/"
}
```

### Run with specific framework
```json
{
  "action": "run",
  "target_path": "tests/",
  "test_framework": "pytest"
}
```

### Run filtered tests
```json
{
  "action": "run",
  "target_path": "tests/",
  "test_filter": "unit",
  "categories": ["unit"]
}
```

## Error Cases

| Error Code | Description |
|------------|-------------|
| CT_001 | target_path is required |
| CT_002 | Invalid action |
| CT_404 | Target path not found |
| CT_500 | Test execution failed |
