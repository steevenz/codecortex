# CodeAnalysis Domain - Test Cases

**Date:** 2026-05-28  
**Domain:** CodeAnalysis  
**Scope:** 4 MCP tools + 8 CLI commands  
**Test Strategy:** Multi-scenario coverage for happy paths, error cases, and integration

---

## Test Case Matrix

### MCP Tool: code_analyze

| Scenario ID | Description | Parameters | Expected Status | Expected Output |
|-------------|-------------|------------|----------------|----------------|
| CA-001 | Basic file analysis | target="test.py", mode="auto" | 200 | Symbols list with signatures |
| CA-002 | Directory overview | target="src/", mode="overview", max_depth=2 | 200 | Directory tree structure |
| CA-003 | Symbol focus mode | target="test.py", mode="symbol_focus", focus="MyClass" | 200 | Single symbol with call graph |
| CA-004 | Missing target | target="" | 400 | Error: target is required |
| CA-005 | Non-existent path | target="/nonexistent.py" | 404 | Error: path does not exist |
| CA-006 | Pagination | target="src/", page_size=50, cursor="token" | 200 | Paginated results with next_cursor |
| CA-007 | Max depth limit | target="src/", max_depth=15 | 200 | Depth capped at 10 |
| CA-008 | Include docstrings | target="test.py", include_docstring=true | 200 | Symbols with docstring field populated |
| CA-009 | Include comments | target="test.py", include_comments=true | 200 | Symbols with comment data |
| CA-010 | Repo ID resolution | target="test.py", repo_id="uuid" | 200 | Symbols from specific repository |

---

### MCP Tool: code_search

| Scenario ID | Description | Parameters | Expected Status | Expected Output |
|-------------|-------------|------------|----------------|----------------|
| CS-001 | Basic symbol search | query="payment" | 200 | Matching symbols list |
| CS-002 | Search with limit | query="user", limit=10 | 200 | Max 10 results |
| CS-003 | File pattern filter | query="auth", file_pattern="*.py" | 200 | Only Python file matches |
| CS-004 | Semantic search | query="authentication", semantic=true | 200 | Results with semantic scores |
| CS-005 | Graph enrichment | query="process", graph=true | 200 | Results with relationship data |
| CS-006 | Empty query | query="" | 400 | Error: query is required |
| CS-007 | Repo-scoped search | query="test", repo_id="uuid" | 200 | Results from specific repo |
| CS-008 | Include content | query="config", include_content=true | 200 | Results with code snippets |
| CS-009 | Cache hit | query="cached_term" (second call) | 200 | Results with from_cache=true |
| CS-010 | Combined search | query="api", semantic=true, graph=true | 200 | Multi-layer enriched results |

---

### MCP Tool: code_audit

| Scenario ID | Description | Parameters | Expected Status | Expected Output |
|-------------|-------------|------------|----------------|----------------|
| CAU-001 | Full directory audit | target="src/" | 200 | Findings + compliance_score |
| CAU-002 | Single file audit | target="test.py" | 200 | File-specific findings |
| CAU-003 | Category filter | target="src/", scan_categories=["secrets", "pii"] | 200 | Only security findings |
| CAU-004 | Severity filter | target="src/", severity_threshold="high" | 200 | Only high/critical findings |
| CAU-005 | Specific files | target="src/", files=["test.py", "main.py"] | 200 | Audit only specified files |
| CAU-006 | Missing target | target="" | 400 | Error: target is required |
| CAU-007 | Non-existent path | target="/nonexistent" | 404 | Error: path does not exist |
| CAU-008 | Use AST cache | target="src/", use_ast=true | 200 | Faster scan with cached AST |
| CAU-009 | Custom entropy | target="src/", entropy_threshold=5.0 | 200 | Adjusted secrets detection |
| CAU-010 | Output format CSV | target="src/", output_format="csv" | 200 | CSV-formatted findings |

---

### MCP Tool: code_status

| Scenario ID | Description | Parameters | Expected Status | Expected Output |
|-------------|-------------|------------|----------------|----------------|
| CST-001 | Full status | path="src/", include_metrics=true, include_vcs=true, include_symbols=true | 200 | Complete status with all sections |
| CST-002 | Metrics only | path="src/", include_metrics=true, include_vcs=false, include_symbols=false | 200 | Only metrics data |
| CST-003 | VCS only | path="src/", include_metrics=false, include_vcs=true, include_symbols=false | 200 | Only git status |
| CST-004 | Symbols only | path="src/", include_metrics=false, include_vcs=false, include_symbols=true | 200 | Only symbol counts |
| CST-005 | Language filter | path="src/", language="python" | 200 | Python-specific metrics |
| CST-006 | Missing path | path="" | 400 | Error: path is required |
| CST-007 | Non-existent path | path="/nonexistent" | 404 | Error: path does not exist |
| CST-008 | Cached status | path="src/", repo_id="uuid" | 200 | Results from cache with cached=true |
| CST-009 | No git repo | path="/tmp/nogit" | 200 | Status with vcs.type="none" |
| CST-010 | Repo ID resolution | path="src/", repo_id="uuid" | 200 | Status with repo metadata |

---

### CLI Command: codebase analyze

| Scenario ID | Description | Command | Expected Status | Expected Output |
|-------------|-------------|---------|----------------|----------------|
| CLI-CA-001 | Basic analyze | python -m src.cli codebase analyze test.py | 200 | JSON with analysis results |
| CLI-CA-002 | Directory analyze | python -m src.cli codebase analyze src/ --mode overview | 200 | Directory tree JSON |
| CLI-CA-003 | Max depth | python -m src.cli codebase analyze src/ --max-depth 5 | 200 | Analysis with depth limit |
| CLI-CA-004 | Missing target | python -m src.cli codebase analyze | 400 | Error: required argument |
| CLI-CA-005 | Invalid mode | python -m src.cli codebase analyze test.py --mode invalid | 400 | Error: invalid choice |

---

### CLI Command: codebase search

| Scenario ID | Description | Command | Expected Status | Expected Output |
|-------------|-------------|---------|----------------|----------------|
| CLI-CS-001 | Basic search | python -m src.cli codebase search "payment" | 200 | JSON with search results |
| CLI-CS-002 | With target | python -m src.cli codebase search "user" --target src/ | 200 | Scoped search results |
| CLI-CS-003 | Missing query | python -m src.cli codebase search | 400 | Error: required argument |

---

### CLI Command: codebase audit

| Scenario ID | Description | Command | Expected Status | Expected Output |
|-------------|-------------|---------|----------------|----------------|
| CLI-CAU-001 | Basic audit | python -m src.cli codebase audit src/ | 200 | JSON with audit findings |
| CLI-CAU-002 | With severity | python -m src.cli codebase audit src/ --severity high | 200 | High+ severity findings |
| CLI-CAU-003 | With mode | python -m src.cli codebase audit src/ --mode security | 200 | Security-focused audit |
| CLI-CAU-004 | Missing target | python -m src.cli codebase audit | 400 | Error: required argument |

---

### CLI Command: codebase status

| Scenario ID | Description | Command | Expected Status | Expected Output |
|-------------|-------------|---------|----------------|----------------|
| CLI-CST-001 | Get status | python -m src.cli codebase status repo_uuid | 200 | JSON with repo status |
| CLI-CST-002 | Missing repo_id | python -m src.cli codebase status | 400 | Error: required argument |
| CLI-CST-003 | Invalid repo_id | python -m src.cli codebase status invalid_uuid | 404 | Error: repo not found |

---

### CLI Command: codebase graph

| Scenario ID | Description | Command | Expected Status | Expected Output |
|-------------|-------------|---------|----------------|----------------|
| CLI-CG-001 | Build graph | python -m src.cli codebase graph src/ build | 200 | JSON with graph build result |
| CLI-CG-002 | Query graph | python -m src.cli codebase graph src/ query --query-node MyClass | 200 | JSON with graph query result |
| CLI-CG-003 | Get relationships | python -m src.cli codebase graph src/ relationships --target-node node_id | 200 | JSON with relationships |
| CLI-CG-004 | Audit graph | python -m src.cli codebase graph src/ audit | 200 | JSON with graph audit result |
| CLI-CG-005 | Missing target | python -m src.cli codebase graph | 400 | Error: required argument |

---

### CLI Command: codebase index

| Scenario ID | Description | Command | Expected Status | Expected Output |
|-------------|-------------|---------|----------------|----------------|
| CLI-CI-001 | Index status | python -m src.cli codebase index src/ status | 200 | JSON with index status |
| CLI-CI-002 | Build index | python -m src.cli codebase index src/ build | 200 | JSON with build result |
| CLI-CI-003 | Reindex | python -m src.cli codebase index src/ reindex | 200 | JSON with reindex result |
| CLI-CI-004 | Clear index | python -m src.cli codebase index src/ clear | 200 | JSON with clear result |
| CLI-CI-005 | Remove index | python -m src.cli codebase index src/ remove | 200 | JSON with remove result |

---

### CLI Command: codebase test

| Scenario ID | Description | Command | Expected Status | Expected Output |
|-------------|-------------|---------|----------------|----------------|
| CLI-CT-001 | Run tests | python -m src.cli codebase test tests/ | 200 | JSON with test results |
| CLI-CT-002 | With framework | python -m src.cli codebase test tests/ --framework pytest | 200 | Framework-specific results |
| CLI-CT-003 | Missing path | python -m src.cli codebase test | 400 | Error: required argument |

---

### CLI Command: codebase refactor

| Scenario ID | Description | Command | Expected Status | Expected Output |
|-------------|-------------|---------|----------------|----------------|
| CLI-CR-001 | Rename symbol | python -m src.cli codebase refactor repo_uuid target --old-name OldName --new-name NewName --symbol | 200 | JSON with refactor result |
| CLI-CR-002 | Rename file | python -m src.cli codebase refactor repo_uuid target --file path/to/file.py --old-name old --new-name new | 200 | JSON with refactor result |
| CLI-CR-003 | Missing repo_id | python -m src.cli codebase refactor | 400 | Error: required argument |

---

## Test Coverage Summary

**Total Test Scenarios:** 50  
**MCP Tool Tests:** 40 (10 per tool)  
**CLI Command Tests:** 10 (cross-domain)  
**Happy Path Scenarios:** 25  
**Error Scenarios:** 15  
**Integration Scenarios:** 10

**Coverage Goals:**
- Minimum: 10 critical scenarios per tool
- Ideal: All 50 scenarios
- Current Design: 50 scenarios (100% coverage target)

---

## Test Execution Plan

### Priority 1 - Critical Scenarios (Execute First)
1. CA-004, CS-006, CAU-006, CST-006 (missing required parameters)
2. CA-005, CS-007, CAU-007, CST-007 (non-existent paths)
3. CLI-CA-004, CLI-CS-003, CLI-CAU-004, CLI-CST-002 (missing arguments)

### Priority 2 - Happy Path Scenarios
1. CA-001, CS-001, CAU-001, CST-001 (basic operations)
2. CA-002, CS-002, CAU-002, CST-002 (with parameters)
3. CLI-CA-001, CLI-CS-001, CLI-CAU-001, CLI-CST-001 (basic CLI)

### Priority 3 - Advanced Scenarios
1. CA-003, CS-004, CAU-003, CST-005 (specialized modes)
2. CA-006, CS-009, CAU-008, CST-008 (caching/performance)
3. CLI-CG-001 through CLI-CR-003 (cross-domain operations)

---

## Test Data Requirements

### Test Files Needed
- `test.py` - Simple Python file with class/function definitions
- `src/` - Directory with multiple files for tree analysis
- `src/secrets.py` - File with hardcoded secrets for audit testing
- `src/bad_code.py` - File with violations for audit testing
- Test repository with git history for VCS testing

### Test Database State
- Repository with indexed symbols
- Repository with embeddings for semantic search
- Repository with graph edges for relationship testing
- Empty repository for error case testing

---

## Success Criteria

A test scenario is considered passing when:
1. HTTP status code matches expected value
2. Response structure matches documented format
3. Error messages are descriptive and include error codes
4. Data fields are correctly populated
5. Performance meets acceptable thresholds (< 5s for most operations)
