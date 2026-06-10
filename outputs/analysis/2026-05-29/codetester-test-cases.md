# CodeTester Domain - Test Case Design

**Date:** 2026-05-29
**Domain:** CodeTester
**Tool:** `code_tester` (MCP tool)
**Actions:** run, coverage, discover, generate, diagnose

---

## Test Case Matrix

### Action: run

#### Happy Path Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| R1 | Basic test run with auto-detection | action="run", target_path="tests/" | Success with summary |
| R2 | Run with specific framework | action="run", target_path="tests/", test_framework="pytest" | Success with framework=pytest |
| R3 | Run with test filter | action="run", target_path="tests/", test_filter="marker=unit" | Success with filtered results |
| R4 | Run specific test names | action="run", target_path="tests/", test_names=["test_foo", "test_bar"] | Success with specific tests |
| R5 | Run with category filter | action="run", target_path="tests/", categories=["unit"] | Success with unit tests only |
| R6 | Run with max_duration | action="run", target_path="tests/", max_duration=60 | Success or timeout error |
| R7 | Async mode without follow | action="run", target_path="tests/", async_mode=True | Returns task_id immediately |
| R8 | Async mode with follow | action="run", target_path="tests/", async_mode=True, follow=True | Waits and returns full results |
| R9 | Run on single test file | action="run", target_path="tests/test_foo.py" | Success with file-specific results |
| R10 | Run with all parameters | action="run", target_path="tests/", test_framework="pytest", test_filter="unit", test_names=["test_x"], categories=["unit"], max_duration=120, async_mode=False | Success with all filters applied |

#### Error Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| R11 | Missing target_path | action="run", target_path="" | Error CT_001 (400) |
| R12 | Invalid action | action="invalid", target_path="tests/" | Error CT_002 (400) |
| R13 | Non-existent path | action="run", target_path="/nonexistent/" | Error CT_404 (404) |
| R14 | Invalid framework | action="run", target_path="tests/", test_framework="invalid" | Fallback to auto-detection |
| R15 | Max duration too low | action="run", target_path="tests/", max_duration=5 | Clamped to minimum 10s |
| R16 | Max duration too high | action="run", target_path="tests/", max_duration=1000 | Clamped to maximum 600s |

#### Integration Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| R17 | Run on git repository | action="run", target_path="repo_with_tests/" | Success with test results |
| R18 | Run with pytest markers | action="run", target_path="tests/", test_filter="slow" | Success with slow tests |
| R19 | Run with unittest discovery | action="run", target_path="tests/", test_framework="unittest" | Success with unittest results |
| R20 | Run on JavaScript project | action="run", target_path="js_tests/", test_framework="jest" | Success with jest results |

---

### Action: coverage

#### Happy Path Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| C1 | Basic coverage analysis | action="coverage", target_path="src/" | Success with overall_coverage |
| C2 | Coverage with detailed format | action="coverage", target_path="src/", coverage_format="detailed" | Success with per-file coverage |
| C3 | Coverage with JSON format | action="coverage", target_path="src/", coverage_format="json" | Success with JSON output |
| C4 | Coverage with specific framework | action="coverage", target_path="src/", test_framework="pytest" | Success with pytest coverage |
| C5 | Coverage on test directory | action="coverage", target_path="tests/" | Success with test coverage |
| C6 | Coverage with recommendations | action="coverage", target_path="src/" | Success with coverage recommendations |

#### Error Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| C7 | Missing target_path | action="coverage", target_path="" | Error CT_001 (400) |
| C8 | Non-existent path | action="coverage", target_path="/nonexistent/" | Error CT_404 (404) |
| C9 | Invalid coverage format | action="coverage", target_path="src/", coverage_format="invalid" | Fallback to summary |

#### Integration Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| C10 | Coverage on Python project | action="coverage", target_path="src/" | Success with Python coverage |
| C11 | Coverage with pytest-cov | action="coverage", target_path="src/", test_framework="pytest" | Success with pytest-cov data |

---

### Action: discover

#### Happy Path Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| D1 | Basic test discovery | action="discover", target_path="tests/" | Success with test list |
| D2 | Discover with auto-detection | action="discover", target_path="tests/", test_framework="auto" | Success with detected framework |
| D3 | Discover with specific framework | action="discover", target_path="tests/", test_framework="pytest" | Success with pytest tests |
| D4 | Discover test files | action="discover", target_path="tests/" | Success with test_files list |
| D5 | Discover markers | action="discover", target_path="tests/" | Success with markers list |
| D6 | Discover categories | action="discover", target_path="tests/" | Success with categories dict |

#### Error Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| D7 | Missing target_path | action="discover", target_path="" | Error CT_001 (400) |
| D8 | Non-existent path | action="discover", target_path="/nonexistent/" | Error CT_404 (404) |
| D9 | No tests found | action="discover", target_path="empty_dir/" | Success with empty test list |

#### Integration Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| D10 | Discover pytest tests | action="discover", target_path="tests/", test_framework="pytest" | Success with pytest test structure |
| D11 | Discover jest tests | action="discover", target_path="js_tests/", test_framework="jest" | Success with jest test structure |

---

### Action: generate

#### Happy Path Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| G1 | Generate test for function | action="generate", target_path="src/foo.py", target_symbol="bar" | Success with test code |
| G2 | Generate test without symbol | action="generate", target_path="src/foo.py" | Success with test for file stem |
| G3 | Generate test for class method | action="generate", target_path="src/foo.py", target_symbol="MyClass.method" | Success with test code |
| G4 | Generate test in existing file | action="generate", target_path="src/foo.py" | Appends to existing test file |
| G5 | Generate test with recommendations | action="generate", target_path="src/foo.py" | Success with recommendations |

#### Error Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| G6 | Missing target_path | action="generate", target_path="" | Error CT_001 (400) |
| G7 | Non-existent file | action="generate", target_path="/nonexistent.py" | Error CT_404 (404) |
| G8 | Invalid Python file | action="generate", target_path="src/bad.py" | May fail or generate basic test |
| G9 | Symbol not found | action="generate", target_path="src/foo.py", target_symbol="nonexistent" | Generates test for file stem |

#### Integration Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| G10 | Generate test in tests/ directory | action="generate", target_path="src/foo.py" | Creates test in tests/ |
| G11 | Generate test in tests/ subdirectory | action="generate", target_path="src/module/foo.py" | Creates test in tests/module/ |

---

### Action: diagnose

#### Happy Path Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| Dg1 | Diagnose test failure | action="diagnose", target_path="tests/" | Success with failure analysis |
| Dg2 | Diagnose with specific framework | action="diagnose", target_path="tests/", test_framework="pytest" | Success with pytest failure |
| Dg3 | Diagnose with source context | action="diagnose", target_path="tests/" | Success with related_source |
| Dg4 | Diagnose with suggestions | action="diagnose", target_path="tests/" | Success with fix suggestions |
| Dg5 | Diagnose no failures | action="diagnose", target_path="tests/" | Success with "no failures" message |

#### Error Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| Dg6 | Missing target_path | action="diagnose", target_path="" | Error CT_001 (400) |
| Dg7 | Non-existent path | action="diagnose", target_path="/nonexistent/" | Error CT_404 (404) |

#### Integration Scenarios

| ID | Description | Parameters | Expected |
|----|-------------|------------|----------|
| Dg8 | Diagnose assertion failure | action="diagnose", target_path="tests/" | Success with assertion analysis |
| Dg9 | Diagnose import error | action="diagnose", target_path="tests/" | Success with import error context |

---

## Test Execution Plan

### Priority 1: Critical Path Tests (Must Pass)
- R1, R2, R11, R12, R13 (Basic run functionality)
- C1, C7, C8 (Basic coverage functionality)
- D1, D7, D8 (Basic discover functionality)
- G1, G6, G7 (Basic generate functionality)
- Dg1, Dg6, Dg7 (Basic diagnose functionality)

**Total:** 15 tests

### Priority 2: Feature Tests (Should Pass)
- R3, R4, R5, R6, R7, R8, R9, R10 (Advanced run features)
- C2, C3, C4, C5, C6 (Advanced coverage features)
- D2, D3, D4, D5, D6 (Advanced discover features)
- G2, G3, G4, G5 (Advanced generate features)
- Dg2, Dg3, Dg4, Dg5 (Advanced diagnose features)

**Total:** 20 tests

### Priority 3: Integration Tests (Nice to Have)
- R14, R15, R16, R17, R18, R19, R20 (Run integration)
- C9, C10, C11 (Coverage integration)
- D9, D10, D11 (Discover integration)
- G8, G9, G10, G11 (Generate integration)
- Dg8, Dg9 (Diagnose integration)

**Total:** 14 tests

**Total Test Cases:** 49

---

## Test Execution Strategy

### MCP Tool Testing
1. Start MCP server in HTTP mode
2. Use curl or HTTP client to call `code_tester` tool
3. Validate response structure matches DTOs
4. Check error codes match expected values

### CLI Testing
- **Status:** No CLI commands exist for codetester
- **Action:** Skip CLI testing, document as gap

### Framework-Specific Testing
- Test with pytest (Python)
- Test with jest (JavaScript/TypeScript)
- Test with go_test (Go)
- Test with cargo_test (Rust)

### Test Data Requirements
- Sample Python project with pytest tests
- Sample JavaScript project with jest tests
- Sample Go project with go tests
- Sample Rust project with cargo tests

---

## Success Criteria

- **Minimum:** 15/15 Priority 1 tests pass (100%)
- **Target:** 35/49 tests pass (71%)
- **Ideal:** 49/49 tests pass (100%)

**Current Status:** Pending execution
