# CodeTester: Quality Assurance

> **Domain:** CodeTester
> **Package:** `src/domain/codetester/`

## Concept

CodeTester provides a unified QA automation layer. It runs test suites and linters across the codebase, tracks task execution, and supports webhook notifications for async completion.

## MCP Tools

| Tool | Function |
|------|----------|
| `qa_run` | Run a QA task (test runner or linter) |
| `qa_status` | Poll the status and results of a background QA task |

## Supported Tools

| Tool | Type | Example |
|------|------|---------|
| `pytest` | Test runner | Python unit/integration tests |
| `flake8` | Linter | Python style/lint checks |
| `unittest` | Test runner | Python standard library tests |
| `jest` | Test runner | JavaScript/TypeScript tests |
| `vitest` | Test runner | Vite-based JS/TS tests |
| `phpunit` | Test runner | PHP tests |
| `go_test` | Test runner | Go tests |
| `cargo_test` | Test runner | Rust tests |
| `npm` | Package runner | NPM scripts (test, lint) |
| `stylelint` | Linter | CSS/SCSS style linting |
| And more | | 22+ tools supported |

## Flow

```
qa_run(repo_id, tool="pytest", target_path="tests/unit", background=True)
    │
    ▼
  Task created (status: pending) ──> Task ID returned
    │
    ▼
  qa_status(task_id) ──> Poll until "completed" or "failed"
    │
    ▼
  Full results: stdout, stderr, exit code, duration
```
