# CodeTester Domain - Gap Analysis Report

**Date:** 2026-05-29
**Domain:** CodeTester
**Scope:** MCP Tools + CLI Commands
**Source of Truth:** Source Code Implementation

---

## Executive Summary

**Overall Documentation Accuracy:** 30%

**Critical Finding:** The documentation describes a completely different tool architecture than what is implemented in the source code. This is a **P0 (Critical)** gap that must be resolved.

---

## Gap Analysis Matrix

### 1. Tool Naming Architecture Mismatch (CRITICAL - P0)

| Aspect | Documentation Claims | Source Code Reality | Severity |
|--------|---------------------|-------------------|----------|
| Tool Name | `qa_run`, `qa_status` | `code_tester` (single tool) | Critical |
| Tool Count | 2 separate tools | 1 consolidated tool with 5 actions | Critical |
| Module Config | `qa_test`, `qa_lint`, `qa_format`, `qa_coverage`, `qa_security` | `code_tester` with actions: run, coverage, discover, generate, diagnose | Critical |

**Impact:** Documentation is completely misleading. Users following docs will fail to use the correct tool.

**Root Cause:** Documentation was written for a planned architecture that was never implemented. Source code uses a consolidated action-based approach instead.

---

### 2. Tool Actions Mismatch (HIGH - P1)

| Action | Documentation | Source Code | Status |
|--------|--------------|-------------|--------|
| Run tests | `qa_run` | `code_tester` action="run" | Mismatched |
| Coverage | Not documented | `code_tester` action="coverage" | Missing in docs |
| Discover tests | Not documented | `code_tester` action="discover" | Missing in docs |
| Generate tests | Not documented | `code_tester` action="generate" | Missing in docs |
| Diagnose failures | Not documented | `code_tester` action="diagnose" | Missing in docs |
| Status polling | `qa_status` | Not implemented | Missing in source |

**Impact:** 3 of 5 implemented actions are undocumented. 1 documented feature (status polling) doesn't exist.

---

### 3. Parameter Documentation Gap (HIGH - P1)

**Documented Parameters:** None documented in concept.md

**Implemented Parameters in `code_tester`:**
- `action` (required): "run" | "coverage" | "discover" | "generate" | "diagnose"
- `target_path` (required): Path to project or test file
- `test_framework` (optional, default="auto"): Framework name or "auto"
- `test_filter` (optional): Filter expression (marker, pattern, name)
- `test_names` (optional): List of specific test names
- `categories` (optional): Test categories (unit, integration, e2e)
- `coverage_format` (optional, default="summary"): "summary" | "detailed" | "json"
- `target_symbol` (optional): Symbol for test generation
- `max_duration` (optional, default=300): Max execution time in seconds (10-600)
- `async_mode` (optional, default=False): Run in background
- `follow` (optional, default=False): Wait for async completion

**Impact:** 100% of parameters are undocumented. Users cannot discover available options.

---

### 4. CLI Commands Gap (MEDIUM - P2)

**Expected:** CLI commands for codetester domain

**Reality:** No CLI commands found in `src/cli/`

**Impact:** No CLI interface available, only MCP tool access.

---

### 5. Documentation Structure Issues (MEDIUM - P2)

**Misplaced Documentation:**
- `src/modules/codetester/README.md` (52 lines) - Should be in `docs/features/codetester/`
- Contains module overview that duplicates concept.md content

**Missing Documentation:**
- No AI impact token efficiency analysis
- No 10/10 AI Coder Impact features section
- No error codes table
- No domain boundary section
- No business context section
- No theoretical foundation section
- No architecture diagram
- No CLI architecture note
- No ~/.aicoders/ compliance section

**Impact:** Documentation does not follow the codeanalysis standard template.

---

### 6. Sub-Feature Documentation (LOW - P3)

**Existing:**
- `docs/features/codetester/sub-features/background-tasks/concept.md` (34 lines)

**Missing Sub-Feature Docs:**
- No docs for `code_tester` tool
- No docs for each action (run, coverage, discover, generate, diagnose)
- No docs for framework detection
- No docs for test adapters

**Impact:** No detailed documentation for individual features.

---

### 7. Test Adapter Documentation Gap (LOW - P3)

**Documented:** 22+ tools mentioned in concept.md

**Implemented:** 28 test adapters in source code

**Gap:** 6 adapters not documented:
- pnpm
- yarn
- kotlin_test
- sbt_test
- maven_test
- perl_test

**Impact:** Minor - users may not know all supported frameworks.

---

## Gap Summary

| Severity | Count | Description |
|----------|-------|-------------|
| Critical (P0) | 1 | Tool naming architecture completely mismatched |
| High (P1) | 2 | Actions mismatched, parameters undocumented |
| Medium (P2) | 2 | No CLI, misplaced README |
| Low (P3) | 2 | Missing sub-feature docs, adapter gap |
| **Total** | **7** | |

**Documentation Accuracy:** 30% (only background tasks concept is accurate)

---

## Recommended Actions

### P0 (Critical - Fix Immediately)
1. **Rewrite concept.md** to reflect actual `code_tester` tool architecture
2. **Update module.json** to match implemented tool structure
3. **Remove references** to `qa_run` and `qa_status` from all documentation

### P1 (High - Fix This Sprint)
4. **Document all 11 parameters** in concept.md with types, defaults, descriptions
5. **Document all 5 actions** with examples and use cases
6. **Remove or implement** `qa_status` if status polling is needed

### P2 (Medium - Fix Next Sprint)
7. **Move README.md** from `src/modules/codetester/` to `docs/features/codetester/`
8. **Add CLI commands** if CLI interface is desired, or document that CLI is not available

### P3 (Low - Nice to Have)
9. **Create sub-feature docs** for each action
10. **Update supported tools list** to include all 28 adapters
11. **Add examples directory** with usage examples

---

## Next Steps

1. Execute Phase 4.5: JSON Output Review
2. Design comprehensive test cases
3. Execute tests to verify tool functionality
4. Implement fixes starting with P0 issues
5. Rewrite documentation following codeanalysis standard
6. Generate final QA report
