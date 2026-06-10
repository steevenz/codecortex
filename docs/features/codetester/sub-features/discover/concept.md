# code_tester: discover

> **Action:** `discover`
> **Tool:** `code_tester`

## Purpose

Discover all tests in a project with markers, categories, and test file locations. Enables selective test execution based on project structure.

## Why It Exists

Before running tests, AI coders need to understand the test landscape. Discovery reveals available tests, their organization, and markers for targeted execution.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | string | Yes | "discover" | Must be "discover" |
| `target_path` | string | Yes | - | Path to project directory |
| `test_framework` | string | No | "auto" | Framework name or "auto" |

## Output Format

```json
{
  "action": "discover",
  "target_path": "/project",
  "framework": "pytest",
  "test_files": ["tests/test_auth.py", "tests/test_payment.py"],
  "tests": [
    {
      "name": "test_login",
      "file": "tests/test_auth.py",
      "line": 10,
      "markers": ["unit"],
      "category": "unit"
    }
  ],
  "markers": ["unit", "integration", "slow"],
  "categories": {
    "unit": ["test_login"],
    "integration": ["test_payment"]
  }
}
```

## Use Cases

- **Test Inventory:** Discover all available tests before execution
- **Marker Discovery:** Find available test markers for filtering
- **Category Analysis:** Understand test organization by type
- **Selective Planning:** Plan targeted test runs based on discovery

## Examples

### Discover all tests
```json
{
  "action": "discover",
  "target_path": "tests/"
}
```

## Error Cases

| Error Code | Description |
|------------|-------------|
| CT_001 | target_path is required |
| CT_404 | Target path not found |
| CT_500 | Discovery failed |
