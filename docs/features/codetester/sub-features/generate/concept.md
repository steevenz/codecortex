# code_tester: generate

> **Action:** `generate`
> **Tool:** `code_tester`

## Purpose

Generate test code for a specific function or symbol using AST-based analysis. Extracts parameters, return types, and edge cases to create test scaffolding.

## Why It Exists

Writing tests is time-consuming. AI coders can automatically generate test scaffolding for new functions, accelerating test coverage and ensuring consistent test structure.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | string | Yes | "generate" | Must be "generate" |
| `target_path` | string | Yes | - | Path to source file |
| `target_symbol` | string | No | null | Function/symbol name (defaults to file stem) |

## Output Format

```json
{
  "action": "generate",
  "target_file": "src/math_utils.py",
  "target_symbol": "add",
  "test_file": "tests/test_math_utils.py",
  "test_line_start": 124,
  "test_code": "def test_add_success():\n    a = None\n    b = None\n    result = add(a, b)\n    assert result is not None\n\ndef test_add_edge_case():\n    a = None\n    b = None\n    result = add(a, b)\n    assert result is not None",
  "recommendations": [
    "Verify test file at tests/test_math_utils.py",
    "Run: pytest tests/test_math_utils.py -k add"
  ]
}
```

## Use Cases

- **New Function Tests:** Generate tests for newly created functions
- **Coverage Gaps:** Create tests for functions lacking coverage
- **Test Scaffolds:** Generate base tests for manual completion
- **Batch Generation:** Create tests for multiple functions at once

## Examples

### Generate test for a function
```json
{
  "action": "generate",
  "target_path": "src/math_utils.py",
  "target_symbol": "add"
}
```

### Generate test without specifying symbol
```json
{
  "action": "generate",
  "target_path": "src/math_utils.py"
}
```

## Error Cases

| Error Code | Description |
|------------|-------------|
| CT_001 | target_path is required |
| CT_404 | Source file not found |
| CT_500 | Test generation failed |
