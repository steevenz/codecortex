---
description: Testing & QA Automation — discover, run, diagnose, and generate tests using CodeCortex
title: WFK_TST_001 — Testing & QA Automation
workflow_id: WFK_TST_001
version: 2.0.0
author: Steeven Andrian
standard: CODDY-Workflow-v2.0
codification: CODDY-Architecture-v1.0 §5
---

# WFK_TST_001: Testing & QA Automation

> **Goal**: Automate test discovery, execution, coverage analysis, failure diagnosis, and missing test generation.
> **Trigger**: User asks about tests, coverage, failures, or wants to write new tests.
> **Time**: 1-10 minutes (depends on test suite size).
> **Cost**: Low-to-medium (test execution is the most expensive step).
> **Supported Frameworks**: pytest, unittest, jest, vitest, phpunit, go_test, cargo_test, flutter_test, and 15+ more (see support-matrix.md).

---

## 1. Trigger Phrases

- *"Run tests"*
- *"What's the coverage?"*
- *"Generate tests"*
- *"Find flaky tests"*
- *"Why did this test fail?"*
- *"Write unit tests for X"*
- *"Test this function"*
- *"Diagnose test failures"*
- *"Coverage report"*
- *"Are there tests for Y?"*

---

## 2. Pipeline Overview

```
Step 1: Discover  (cb:test:discover) ──────┐
Step 2: Run       (cb:test:run) ──────────┤
Step 3: Coverage  (cb:test:run+coverage) ──┤───► Deliverable
Step 4: Diagnose  (cb:test:diagnose) ─────┤
Step 5: Generate  (cb:test:generate) ─────┘
```

All steps are **optional** based on user intent. The AI must route intelligently:
- *"Run tests"* → Steps 1-2
- *"Coverage"* → Steps 1-3
- *"Why is this failing?"* → Steps 2, 4
- *"Write tests"* → Steps 1, 5

---

## 3. Step 1 — Discover Tests

**Purpose**: Auto-detect test framework, test files, and count total tests.

### MCP Call
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "discover",
    target_path: ".",
    test_framework: "auto",
    verbose: false
  }
```

### Response Fields
```json
{
  "frameworks": ["pytest", "jest"],
  "test_files": ["tests/test_a.py", "tests/test_b.py"],
  "total": 42,
  "framework_details": {
    "pytest": { "version": "7.4", "config": "pytest.ini" },
    "jest": { "version": "29.5", "config": "jest.config.js" }
  }
}
```

### AI Must Read
| Field | Decision |
|-------|----------|
| `frameworks[]` | Which frameworks are available. |
| `test_files[]` | Where tests live — directory structure. |
| `total` | `0` → No tests found; skip to Step 5 (Generate). |
| `framework_details` | Version info — flag if outdated. |

### CLI
```bash
codecortex qa discover --target .
```

---

## 4. Step 2 — Run Tests

**Purpose**: Execute the test suite and report results.

### 4.1 Full Suite
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: ".",
    test_framework: "auto",
    test_filter: null,
    test_names: null,
    categories: null,
    coverage_format: "summary",
    max_duration: 300,
    async_mode: true,
    verbose: false
  }
```

### 4.2 Filtered Run (Specific Module)
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: "tests/unit/auth/",
    test_framework: "pytest",
    test_filter: "test_login*",
    max_duration: 120
  }
```

### 4.3 Specific Tests by Name
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: ".",
    test_names: ["test_user_login", "test_order_processing", "test_payment_flow"],
    test_framework: "auto",
    max_duration: 300
  }
```

### Response Fields
```json
{
  "summary": {
    "passed": 38,
    "failed": 2,
    "skipped": 2,
    "duration_seconds": 5.3
  },
  "results": [
    {
      "file": "tests/test_a.py",
      "name": "test_login",
      "status": "passed",
      "duration_ms": 100,
      "message": null
    },
    {
      "file": "tests/test_a.py",
      "name": "test_checkout",
      "status": "failed",
      "duration_ms": 250,
      "message": "AssertionError: expected 200, got 401"
    }
  ],
  "framework": "pytest"
}
```

### AI Must Read
| Field | Action |
|-------|--------|
| `summary.passed` / `failed` / `skipped` | Overall health. |
| `summary.duration_seconds` | `> 60` → slow suite, flag for optimization. |
| `results[].status` | `failed` → collect for Step 4 (Diagnose). |
| `results[].message` | Error message for user report. |
| `results[].duration_ms` | `> 5000` → slow test, flag for optimization. |

### CLI
```bash
codecortex qa run --target . --framework pytest --max-duration 300
codecortex qa run --target tests/unit --filter "test_auth*"
```

---

## 5. Step 3 — Coverage Analysis

**Purpose**: Measure code coverage and identify untested areas.

### MCP Call
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: ".",
    categories: ["coverage"],
    coverage_format: "summary",
    max_duration: 300
  }
```

### Response Fields
```json
{
  "lines_total": 1000,
  "lines_covered": 750,
  "coverage_percent": 75.0,
  "files": [
    { "file": "src/a.py", "coverage": 80 },
    { "file": "src/b.py", "coverage": 45 }
  ],
  "uncovered_lines": [
    { "file": "src/b.py", "lines": [42, 43, 44, 55] }
  ]
}
```

### Coverage Thresholds
| Percentage | Rating | Action |
|------------|--------|--------|
| `>= 90%` | Excellent | Maintain |
| `75-89%` | Good | Address low-coverage files |
| `60-74%` | Fair | Priority: add tests for uncovered areas |
| `< 60%` | Poor | **BLOCKER** for production — must improve |

### CLI
```bash
codecortex qa coverage --target .
```

---

## 6. Step 4 — Diagnose Failures

**Purpose**: Analyze why tests fail — flaky detection, slow test identification, root cause analysis.

### MCP Call
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "diagnose",
    target_path: ".",
    test_names: ["failed_test_1", "failed_test_2"],
    test_framework: "auto",
    max_duration: 300,
    categories: ["flaky", "slow", "assertion"]
  }
```

### Response Fields
```json
{
  "flaky_tests": [
    {
      "name": "test_async_login",
      "failure_rate": 0.25,
      "suggestion": "Add explicit wait or mock the async dependency"
    }
  ],
  "slow_tests": [
    {
      "name": "test_database_migration",
      "duration_ms": 15000,
      "suggestion": "Use in-memory DB or mock migration"
    }
  ],
  "assertion_failures": [
    {
      "name": "test_checkout",
      "expected": "200",
      "actual": "401",
      "file": "tests/test_checkout.py",
      "line": 42,
      "suggestion": "Auth token may be expired; check setup fixture"
    }
  ],
  "suggestions": [
    "Add retry logic to flaky test",
    "Mock external API in slow test",
    "Check test isolation — state leak detected"
  ]
}
```

### AI Must Read
| Field | Action |
|-------|--------|
| `flaky_tests[]` | `failure_rate > 0.1` → serious, needs fix. |
| `slow_tests[]` | `duration_ms > 5000` → optimize or mock. |
| `assertion_failures[]` | Exact expected vs actual → pinpoint bug. |
| `suggestions[]` | Surface directly to user as next steps. |

### CLI
```bash
codecortex qa diagnose --target . --names "test_checkout,test_login"
```

---

## 7. Step 5 — Generate Missing Tests

**Purpose**: Auto-generate test boilerplate for functions/classes without coverage.

### 7.1 Generate for Specific Symbol
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "generate",
    target_symbol: "src/services/order.py::OrderService.process_order",
    test_framework: "auto",
    max_duration: 300,
    categories: ["unit", "edge_cases"]
  }
```

### 7.2 Generate for Uncovered Files
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "generate",
    target_path: "src/",
    test_framework: "auto",
    max_duration: 300,
    categories: ["unit"]
  }
```

### Response Fields
```json
{
  "files_created": [
    "tests/test_order_service.py"
  ],
  "template": "pytest",
  "tests_generated": 5,
  "coverage_estimate": "Will cover 45% of OrderService",
  "warnings": [
    "External API calls detected — mock required",
    "Database dependency — use test fixture"
  ]
}
```

### CLI
```bash
codecortex qa generate --target src/services/order.py --symbol OrderService.process_order
codecortex qa generate --target src/ --framework pytest
```

---

## 8. Deliverable Format

```markdown
# Testing & QA Report

## 1. Test Discovery
- **Frameworks**: <list>
- **Test Files**: <N> files
- **Total Tests**: <N>

## 2. Test Run Results
- **Passed**: <N> | **Failed**: <N> | **Skipped**: <N>
- **Duration**: <N>s
- **Status**: <PASS / PARTIAL / FAIL>

## 3. Coverage
- **Overall**: <N>% (<covered>/<total> lines)
- **Low-Coverage Files**:
  | File | Coverage | Action |
  |------|----------|--------|
  | ... | ... | ... |

## 4. Failure Diagnosis
- **Flaky Tests**: <N> — <suggestions>
- **Slow Tests**: <N> — <suggestions>
- **Assertion Failures**: <N> — <expected vs actual>

## 5. Generated Tests
- **Files Created**: <list>
- **Tests Generated**: <N>
- **Warnings**: <list>

## 6. Recommendations
- <actionable next steps>
```

---

## 9. CI/CD Integration

### GitHub Actions — Full QA Pipeline
```yaml
jobs:
  qa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Discover Tests
        run: codecortex qa discover --target .
      - name: Run Tests
        run: codecortex qa run --target . --max-duration 300
      - name: Coverage Check
        run: codecortex qa coverage --target .
      - name: Diagnose (on failure)
        if: failure()
        run: codecortex qa diagnose --target .
```

---

## 10. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| `test_filter` instead of full suite | ~60% | Run only affected tests |
| `coverage_format: "summary"` vs "detailed" | ~40% | Skip per-line coverage data |
| Skip `discover` if test files already known | ~15% | Use user-provided test paths |
| `max_duration: 120` vs 300 | ~50% | Cap execution time |

### Parallel Execution
- Step 1 (`discover`) + Step 2 (`run`) are sequential
- But Step 3 (`coverage`) can run in parallel with Step 4 (`diagnose`) after run completes
- Step 5 (`generate`) for multiple symbols can be batched

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| User says "just run tests" | Skip Steps 1, 3, 4, 5. Run Step 2 only. |
| `summary.total == 0` after discover | Skip run, go straight to Step 5 (generate) |
| All tests pass, no failures | Skip Step 4 (diagnose), deliver coverage only |
| User asks "coverage only" | Skip Steps 1, 2, 4, 5. Run `cb:status --include-metrics` |

### Cache Reuse
- Reuse `repo_id` across test sessions
- If `discover` ran in last 10 minutes → reuse test file list
- If coverage report exists → only re-run changed test files

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [analysis-orchestra-workflow.md](analysis-orchestra-workflow.md)*
