# code_tester: diagnose

> **Action:** `diagnose`
> **Tool:** `code_tester`

## Purpose

Analyze test failures with root cause analysis, source code context, and actionable fix suggestions. Enables AI coders to understand and resolve test failures automatically.

## Why It Exists

When tests fail, AI coders need comprehensive failure context to fix issues efficiently. Diagnosis provides failure details, traceback analysis, source context, and fix suggestions.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | string | Yes | "diagnose" | Must be "diagnose" |
| `target_path` | string | Yes | - | Path to project or test directory |
| `test_framework` | string | No | "auto" | Framework name or "auto" |

## Output Format

```json
{
  "action": "diagnose",
  "target_path": "/project",
  "failure": {
    "name": "test_auth_login_failure",
    "file": "tests/test_auth.py",
    "line": 52,
    "message": "assert user.is_authenticated == False",
    "traceback": "File \"src/auth/service.py\", line 89, in login\n    user.is_authenticated == True"
  },
  "root_cause": {
    "type": "assertion_failure",
    "test_file": "tests/test_auth.py",
    "test_line": 52,
    "expected": "False",
    "actual": "True"
  },
  "suggestions": [
    "Check the assertion on line 52",
    "Verify test inputs produce expected outputs"
  ],
  "related_source": {
    "file": "src/auth/service.py",
    "line": 89,
    "code": "return user.is_authenticated == True",
    "context": "    def login(self, user):\n        return user.is_authenticated == True\n"
  }
}
```

## Use Cases

- **Failure Analysis:** Understand why a specific test failed
- **Source Context:** See the code causing the failure
- **Fix Suggestions:** Get actionable recommendations for resolving failures
- **Automated Debugging:** Use diagnosis output for automatic fix generation

## Examples

### Diagnose test failures
```json
{
  "action": "diagnose",
  "target_path": "tests/"
}
```

## Error Cases

| Error Code | Description |
|------------|-------------|
| CT_001 | target_path is required |
| CT_404 | Target path not found |
| CT_500 | Diagnosis failed |
