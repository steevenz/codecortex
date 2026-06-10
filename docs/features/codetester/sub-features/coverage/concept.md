# code_tester: coverage

> **Action:** `coverage`
> **Tool:** `code_tester`

## Purpose

Generate test coverage analysis with overall percentage, per-file coverage details, and actionable recommendations for improving coverage.

## Why It Exists

AI coders need to identify untested code to prioritize test additions. Coverage analysis provides a data-driven approach to improving code quality.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | string | Yes | "coverage" | Must be "coverage" |
| `target_path` | string | Yes | - | Path to project directory |
| `test_framework` | string | No | "auto" | Framework name or "auto" |
| `coverage_format` | string | No | "summary" | "summary" | "detailed" | "json" |

## Output Format

```json
{
  "action": "coverage",
  "target_path": "/project",
  "overall_coverage": 74.5,
  "files": [
    {
      "file": "src/auth/handler.py",
      "coverage": 92.3,
      "total_lines": 156,
      "covered_lines": 144,
      "uncovered_lines": [12, 45, 67],
      "uncovered_functions": ["validate_token_expiry"]
    }
  ],
  "recommendations": [
    {
      "severity": "high",
      "message": "Low coverage",
      "file": "src/payment/processor.py",
      "suggested_tests": ["test_process_refund"]
    }
  ]
}
```

## Use Cases

- **Coverage Assessment:** Quick check of overall coverage percentage
- **Gap Identification:** Find files with low coverage needing tests
- **Targeted Improvements:** Get specific recommendations for coverage gaps
- **Quality Gates:** Verify coverage meets project thresholds

## Examples

### Basic coverage analysis
```json
{
  "action": "coverage",
  "target_path": "src/"
}
```

### Detailed coverage report
```json
{
  "action": "coverage",
  "target_path": "src/",
  "coverage_format": "detailed"
}
```

## Error Cases

| Error Code | Description |
|------------|-------------|
| CT_001 | target_path is required |
| CT_404 | Target path not found |
| CT_500 | Coverage analysis failed |
