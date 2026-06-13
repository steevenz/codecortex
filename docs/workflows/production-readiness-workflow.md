---
description: Production Readiness Checklist — 14-gate quality assessment covering security, code hygiene, dead code, placeholders, stubs, junk files, and best-practice compliance before shipping
title: WFK_PRD_001 — Production Readiness Checklist
workflow_id: WFK_PRD_001
version: 2.0.0
author: Steeven Andrian
standard: CODDY-Workflow-v2.0
---

# WFK_PRD_001: Production Readiness Checklist

> **Goal**: Determine if a codebase is safe to ship to production via 14 gated checks covering repository health, security, architecture, tests, code hygiene, dead/unwired code, placeholders, stubs, junk artifacts, and bug patterns.
> **Trigger**: User asks if code is production-ready, requests a review, or before a release.
> **Time**: 3-8 minutes (14 gates, parallelizable).
> **Cost**: Medium-to-high (audit + search + test run + graph analysis).
> **Output**: PASS/FAIL per gate with blocking issues, warnings, and recommendations.
> **Codification**: CODDY-Architecture-v1.0 §5

---

## 1. Trigger Phrases

- *"Is this production ready?"*
- *"Production readiness review"*
- *"Can we ship this?"*
- *"Quality gate"*
- *"Release check"*
- *"Pre-deployment audit"*
- *"Should we merge this?"*
- *"Code review — is it safe?"*
- *"Ship or fix?"*
- *"Any TODOs or placeholders left?"*
- *"Clean up before release"*
- *"Junk code scan"*
- *"Dead code check"*
- *"Placeholder audit"*

---

## 2. Pipeline Overview

```
Gate 1:  Repository Health      (repo:inspect)        ───┐
Gate 2:  Codebase Metrics       (cb:status)           ───┤
Gate 3:  Security Audit         (cb:audit)            ───┤
Gate 4:  Architecture Audit     (cb:graph:audit)      ───┤
Gate 5:  Test Coverage           (cb:test:run)         ───┤───► PASS/FAIL
Gate 6:  File Security Audit     (fs:audit)            ───┤      per gate
Gate 7:  Staleness Check         (repo:staleness)      ───┤
Gate 8:  Code Hygiene            (cb:search regex)     ───┤
Gate 9:  Empty / Incomplete Code (cb:search + analyze) ───┤
Gate 10: Unwired & Dead Code    (cb:graph:query)     ───┤
Gate 11: Junk Code & Artifacts   (fs:search + audit)  ───┤
Gate 12: Bug Pattern Detection   (cb:audit + search)  ───┘
Gate 13: Error Handling Audit    (cb:audit + analyze)  ───┘
Gate 14: Dependency Health       (repo:inspect deps)   ───┘
```

---

## 3. Gate 1 — Repository Health

**Purpose**: Fast health check — VCS status, index state, contributor risk.

### MCP Call
```
MCP: codecortex:repository
  action: "inspect"
  repo_path: "<path>"
  args: {
    include_git_diagnostics: true,
    include_index_metadata: true,
    include_file_stats: true,
    include_dependency_summary: true
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| `ai_readiness_score` | `>= 70` | **BLOCKER** if `< 50` |
| `vcs.uncommitted_changes` | `< 5` | **WARNING** if `>= 5` |
| `vcs.untracked_files` | `< 10` | **WARNING** if `>= 10` |
| `bus_factor_risk` | `!= "high"` | **WARNING** if `high` |
| `index_metadata.indexed` | `true` | **BLOCKER** if `false` |
| `crisis_frequency.crisis_risk` | `!= "high"` | **WARNING** if `high` |

### CLI
```bash
codecortex repo inspect /path/to/project --include-git-diagnostics
```

---

## 4. Gate 2 — Codebase Metrics

**Purpose**: Quantitative quality gate — LOC, comment ratio, graph density, file distribution.

### MCP Call
```
MCP: codecortex:codebase
  action: "status"
  repo_id: "<repo_id>"
  args: {
    include_metrics: true,
    include_vcs: true,
    include_symbols: true
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| `comment_ratio` | `0.1` to `0.3` | **WARNING** if `< 0.05` or `> 0.4` |
| `graph_stats.density` | `< 0.01` | **WARNING** if `> 0.05` |
| `graph_stats.components` | `< 20` (for repos < 500 files) | **WARNING** if excessive fragmentation |
| `symbols.functions_per_class` (avg) | `< 15` | **WARNING** if `> 20` |
| `summary.languages` | No anomalies | **WARNING** if `.exe` or binary in source |
| `summary.total_lines` / `summary.files` | `< 500` avg LOC/file | **WARNING** if monolithic files detected |

### CLI
```bash
codecortex cb status /path/to/project --include-metrics
```

---

## 5. Gate 3 — Security Audit

**Purpose**: Find secrets, PII, misconfigurations, vulnerabilities, and unsafe patterns.

### MCP Call
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: ".",
    scan_categories: ["secrets", "pii", "misconfig", "vulns", "naming", "di_compliance", "unsafe_patterns"],
    severity_threshold: "low",
    entropy_threshold: 4.5,
    max_file_size_kb: 1024,
    use_ast: true,
    use_aiignore: true
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| `compliance_score` | `>= 85` | **BLOCKER** if `< 60` |
| `findings` with `severity=critical` | `0` | **BLOCKER** if `> 0` |
| `findings` with `severity=high` | `< 3` | **BLOCKER** if `>= 5` |
| `findings` with `category=secrets` | `0` | **BLOCKER** if `> 0` |
| `findings` with `category=pii` | `0` | **BLOCKER** if `> 0` |
| `findings` with `category=unsafe_patterns` | `0` | **BLOCKER** if `> 0` |
| Hardcoded credentials (API keys, tokens) | `0` | **BLOCKER** if any found |
| SQL injection patterns | `0` | **BLOCKER** if any found |
| XSS vulnerabilities | `0` | **BLOCKER** if any found |

### CLI
```bash
codecortex cb audit /path/to/project --severity-threshold low
```

---

## 6. Gate 4 — Architecture Audit

**Purpose**: Detect god nodes, circular dependencies, tight coupling, dead code, complexity hotspots.

### MCP Call
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "audit",
    audit_types: ["god_nodes", "circular_deps", "coupling", "dead_code", "complexity"],
    degree_threshold: 10,
    include_summary: true,
    limit: 50
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| `god_nodes` with `in_degree > 30` | `0` | **WARNING** if any found |
| `circular_deps.count` | `0` | **BLOCKER** if `> 0` |
| `coupling` with `score > 0.7` | `0` | **WARNING** if any found |
| `dead_code` count | `< 10` | **WARNING** if `> 20` |
| `complexity` with `complexity > 25` | `< 3` | **WARNING** if `> 5` |
| `modularity_score` | `>= 0.6` | **WARNING** if `< 0.4` |

### CLI
```bash
codecortex cg audit <repo_id> --types god_nodes,circular_deps,coupling,dead_code,complexity
```

---

## 7. Gate 5 — Test Coverage

**Purpose**: Verify tests exist, pass, and coverage is acceptable. No tests = cannot ship.

### MCP Call
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: ".",
    test_framework: "auto",
    coverage_format: "summary",
    max_duration: 300
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| `summary.total` | `> 0` | **BLOCKER** if `0` |
| `summary.failed` | `0` | **BLOCKER** if `> 0` |
| `coverage_percent` | `>= 75` | **WARNING** if `< 60` |
| `coverage_percent` for critical paths | `>= 90` | **BLOCKER** if `< 80` |
| `summary.skipped` | `< 10%` of total | **WARNING** if excessive skipping |
| `flaky_tests` | `0` | **WARNING** if any found |
| Mocked tests vs real tests ratio | `> 30%` real | **WARNING** if mostly mocked |

### CLI
```bash
codecortex qa run --target . --framework auto
codecortex qa coverage --target .
```

---

## 8. Gate 6 — File Security Audit

**Purpose**: Check for sensitive files, incorrect permissions, hidden VCS data, and exposed config.

### MCP Call
```
MCP: codecortex:filesystem
  action: "audit"
  path: "<repo_path>"
  args: {
    recursive: true,
    severity: "medium",
    check_permissions: true,
    check_hidden: true,
    max_file_size_mb: 100,
    limit: 200
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| `findings` with `category=sensitive_file` | `0` | **BLOCKER** if any found |
| `findings` with `severity=critical` | `0` | **BLOCKER** if any found |
| Files with `permission=777` | `0` | **WARNING** if any found |
| Hidden VCS files exposed | `0` | **WARNING** if any found |
| `.env` files in repo | `0` | **BLOCKER** if any found |
| Backup files (`.bak`, `.tmp`, `.old`) | `0` | **WARNING** if any found |

### CLI
```bash
codecortex fs audit /path/to/project --recursive --severity medium
```

---

## 9. Gate 7 — Staleness Check

**Purpose**: Ensure the CodeCortex index matches the actual code. Stale index → misleading analysis.

### MCP Call
```
MCP: codecortex:repository
  action: "staleness"
  repo_id: "<repo_id>"
  args: {
    compare_remote: true,
    fetch_remote: false,
    include_local_changes: true,
    timeout: 30
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| `stale_files` | `0` | **WARNING** if `> 0` |
| `commits_behind` | `< 5` | **WARNING** if `>= 5` |
| `local_changes_not_indexed` | `0` | **BLOCKER** if `> 0` |

### CLI
```bash
codecortex repo staleness /path/to/project --compare-remote
```

---

## 10. Gate 8 — Code Hygiene & Completeness

**Purpose**: Detect TODOs, FIXMEs, placeholder implementations, stubs, hacking comments, and incomplete code markers that should never reach production.

### 10.1 Placeholder & TODO Detection
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "TODO|FIXME|HACK|XXX|TEMP|TEMPORARY|PLACEHOLDER|STUB|DUMMY|FAKE|MOCK_ME|IMPLEMENT_ME|NOT_IMPLEMENTED",
    search_type: "regex",
    file_pattern: "*",
    case_sensitive: false,
    include_content: true,
    limit: 100
  }
```

### 10.2 Hacking / Temporary Comments
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "quick fix|quickfix|workaround|work-around|temporary fix|temp fix|band-aid|bandaid|dirty hack|dirty fix|emergency fix|will fix later|needs cleanup|needs refactoring",
    search_type: "regex",
    file_pattern: "*",
    case_sensitive: false,
    include_content: true,
    limit: 100
  }
```

### 10.3 Fake / Placeholder Data Detection
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "lorem ipsum|example.com|test@example|1234567890|password123|admin123|0000000000|fill_in|fillme|your_name_here|sample_data|dummy_data|fake_data",
    search_type: "regex",
    file_pattern: "*",
    case_sensitive: false,
    include_content: true,
    limit: 100
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| `TODO` comments | `0` | **BLOCKER** if `> 0` |
| `FIXME` comments | `0` | **BLOCKER** if `> 0` |
| `HACK` / `XXX` / `TEMP` markers | `0` | **BLOCKER** if `> 0` |
| Placeholder implementations (pass/raise NotImplemented) | `0` | **BLOCKER** if `> 0` |
| Stub / dummy / fake data in source | `0` | **BLOCKER** if `> 0` |
| Hacking / temporary workaround comments | `0` | **WARNING** if `> 0` |

### Best Practice Rule
> **Production code must contain zero TODO, FIXME, HACK, or placeholder markers.** All unfinished work must be completed or moved to the issue tracker before release.

---

## 11. Gate 9 — Empty & Incomplete Code

**Purpose**: Find empty functions, empty classes, no-op methods, and skeletal implementations that do nothing.

### 11.1 Empty Functions / Methods
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "def\\s+\\w+\\s*\\(\\s*\\)\\s*:\\s*\\n\\s*pass|function\\s+\\w+\\s*\\(\\s*\\)\\s*\\{\\s*\\}|\\{\\s*\\}\\s*$|\\{\\s*return\\s*;?\\s*\\}",
    search_type: "regex",
    file_pattern: "*",
    include_content: true,
    limit: 100
  }
```

### 11.2 Empty Classes / Interfaces
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "class\\s+\\w+\\s*\\(\\s*\\)\\s*:\\s*\\n\\s*pass|class\\s+\\w+\\s*\\{\\s*\\}|interface\\s+\\w+\\s*\\{\\s*\\}",
    search_type: "regex",
    file_pattern: "*",
    include_content: true,
    limit: 100
  }
```

### 11.3 NotImplemented / Raise Patterns
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "raise NotImplementedError|raise NotImplemented|throw new NotImplemented|\\.unimplemented|todo!\\(\\)|FIXME|not implemented yet|coming soon",
    search_type: "regex",
    file_pattern: "*",
    case_sensitive: false,
    include_content: true,
    limit: 100
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| Empty functions / methods | `0` | **BLOCKER** if `> 0` in production paths |
| Empty classes / interfaces | `0` | **WARNING** if `> 0` |
| `NotImplementedError` / `todo!()` | `0` | **BLOCKER** if `> 0` |
| Skeleton / scaffold code left in production | `0` | **BLOCKER** if `> 0` |

---

## 12. Gate 10 — Unwired & Dead Code

**Purpose**: Find unused exports, orphaned modules, unreachable imports, and code that exists but is never called.

### 12.1 Dead Code Discovery
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "*",
    query_type: "dead_code",
    limit: 100
  }
```

### 12.2 Unused Exports
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "export\\s+(const|let|var|function|class|interface|type)\\s+\\w+|module\\.exports|export default",
    search_type: "regex",
    file_pattern: "*",
    include_content: false,
    limit: 200
  }
```
Then cross-reference with `cb:graph:query` to find which exports have zero callers.

### 12.3 Orphaned / Unreachable Imports
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "import\\s+.*\\s+from\\s+['\"]\\.\\./|require\\s*\\(\\s*['\"]\\.\\./|from\\s+['\"]\\.\\.",
    search_type: "regex",
    file_pattern: "*",
    include_content: false,
    limit: 200
  }
```

### 12.4 Commented-Out Code
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "^\\s*//\\s*(def|function|class|import|const|let|var|#include|import)\\s+|^\\s*/\\*\\s*(def|function|class)\\s+|^\\s*#\\s*(def|class|import)",
    search_type: "regex",
    file_pattern: "*",
    include_content: true,
    limit: 100
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| Dead functions / classes | `0` | **WARNING** if `> 10` |
| Unused exports | `< 5` | **WARNING** if `> 10` |
| Orphaned modules (zero imports) | `< 3` | **WARNING** if `> 5` |
| Commented-out code blocks | `0` | **WARNING** if `> 0` |
| Unreachable imports (imported but never used) | `< 5` | **WARNING** if `> 10` |

### Best Practice Rule
> **Dead code is a liability.** It misleads new developers, increases compilation/parsing time, and creates false confidence in coverage metrics. Remove it before shipping.

---

## 13. Gate 11 — Junk Code & Artifacts

**Purpose**: Find debug statements, console logs, temporary files, backup files, source maps, and development artifacts that must never reach production.

### 13.1 Debug Statements
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "console\\.log\\s*\\(|console\\.debug\\s*\\(|console\\.warn\\s*\\(|console\\.error\\s*\\(|print\\s*\\(|printf\\s*\\(|debugger;|binding\\.pry|byebug|ipdb\\.set_trace|pdb\\.set_trace|debugger\\s*:|binding\\.irb",
    search_type: "regex",
    file_pattern: "*",
    exclude_pattern: "test*|spec*|*.test.*|*.spec.*",
    include_content: true,
    limit: 100
  }
```

### 13.2 Junk Files Search
```
MCP: codecortex:filesystem
  action: "search"
  path: "<repo_path>"
  args: {
    pattern: "\\.(bak|tmp|old|orig|swp|swo|~|rej)$|debug\\.log|npm-debug\\.log|yarn-error\\.log|\\.DS_Store|Thumbs\\.db",
    recursive: true,
    limit: 100
  }
```

### 13.3 Source Maps & Dev Artifacts
```
MCP: codecortex:filesystem
  action: "search"
  path: "<repo_path>"
  args: {
    pattern: "\\.map$|\\.sourcemap$|webpack\\.config\\.|vite\\.config\\.|rollup\\.config\\.|babel\\.config\\.",
    recursive: true,
    limit: 50
  }
```

### 13.4 Build / Dist Artifacts in Source
```
MCP: codecortex:filesystem
  action: "search"
  path: "<repo_path>"
  args: {
    pattern: "dist/|build/|out/|\\.next/|target/",
    recursive: false,
    limit: 50
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| `console.log` / `print` / `debugger` in production code | `0` | **BLOCKER** if `> 0` |
| Backup / temp / swap files | `0` | **WARNING** if `> 0` |
| Source maps in production build | `0` | **WARNING** if `> 0` |
| Build artifacts committed to source | `0` | **WARNING** if `> 0` |
| Debug log files | `0` | **WARNING** if `> 0` |
| `.DS_Store`, `Thumbs.db` | `0` | **WARNING** if `> 0` |

---

## 14. Gate 12 — Bug Pattern Detection

**Purpose**: Detect common bug patterns, anti-patterns, and error-handling gaps that cause production issues.

### 14.1 Empty Catch / Except Blocks
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "except\\s*.*:\\s*\\n\\s*pass|catch\\s*\\(\\s*.*\\s*\\)\\s*\\{\\s*\\}|catch\\s*\\{\\s*\\}",
    search_type: "regex",
    file_pattern: "*",
    include_content: true,
    limit: 100
  }
```

### 14.2 Mutable Default Arguments (Python)
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "def\\s+\\w+\\s*\\([^)]*=[][^)]*\\):",
    search_type: "regex",
    file_pattern: "*.py",
    include_content: true,
    limit: 100
  }
```

### 14.3 Race Conditions / Unsafe Patterns
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "time\\.sleep\\s*\\(|setTimeout\\s*\\(|setInterval\\s*\\(|sleep\\s*\\(|busy\\s*wait|race\\s*condition|TODO\\s*thread|FIXME\\s*sync",
    search_type: "regex",
    file_pattern: "*",
    include_content: true,
    limit: 100
  }
```

### 14.4 Memory Leak Patterns
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "setInterval\\s*\\(|while\\s*\\(true\\)|while\\s*\\(1\\)|recursive\\s+call\\s+without\\s+base|eventEmitter\\.on\\s*\\(|addEventListener\\s*\\(",
    search_type: "regex",
    file_pattern: "*",
    include_content: true,
    limit: 100
  }
```

### 14.5 Unsafe Type Assertions / Casts
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "as\\s+any|as\\s+unknown|!\\s*non-null|unsafe|force unwrap|forceUnwrap|\\.cast\\s*\\(|reinterpret_cast|static_cast",
    search_type: "regex",
    file_pattern: "*",
    include_content: true,
    limit: 100
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| Empty catch / except blocks | `0` | **BLOCKER** if `> 0` |
| Mutable default arguments | `0` | **BLOCKER** if `> 0` |
| Race condition patterns | `0` | **WARNING** if `> 0` |
| Memory leak patterns (unclosed listeners) | `< 3` | **WARNING** if `> 5` |
| Unsafe type assertions | `< 3` | **WARNING** if `> 5` |
| Null pointer risk patterns | `< 5` | **WARNING** if `> 10` |

---

## 15. Gate 13 — Error Handling & Resilience Audit

**Purpose**: Verify the codebase has robust error handling, graceful degradation, and no unhandled edge cases.

### 15.1 Unhandled Promise Rejections
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "\\.then\\s*\\(|async\\s+function|Promise|await\\s+|catch\\s*\\(",
    search_type: "regex",
    file_pattern: "*.js,*.ts,*.jsx,*.tsx",
    include_content: true,
    limit: 200
  }
```

### 15.2 Panic / Fatal Patterns
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "panic\\s*\\(|os\\.Exit\\s*\\(|process\\.exit\\s*\\(|sys\\.exit\\s*\\(|fatal|abort\\s*\\(|kill\\s*-9",
    search_type: "regex",
    file_pattern: "*",
    include_content: true,
    limit: 100
  }
```

### 15.3 Input Validation Gaps
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: "src/",
    scan_categories: ["input_validation", "unsafe_patterns"],
    severity_threshold: "medium"
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| Async functions without catch/finally | `0` | **BLOCKER** if `> 0` |
| Panic / fatal exits in non-init code | `0` | **BLOCKER** if `> 0` |
| Missing input validation on API endpoints | `0` | **BLOCKER** if `> 0` |
| Unhandled edge cases (no default case) | `< 3` | **WARNING** if `> 5` |
| Missing timeout on network calls | `< 3` | **WARNING** if `> 5` |

---

## 16. Gate 14 — Dependency Health

**Purpose**: Verify dependencies are up-to-date, have no known vulnerabilities, and no dev dependencies leaked to production.

### MCP Call
```
MCP: codecortex:repository
  action: "inspect"
  repo_path: "<path>"
  args: {
    include_dependency_summary: true,
    include_vulnerability_scan: true
  }
```

### Pass Criteria
| Check | Threshold | Severity |
|-------|-----------|----------|
| Known vulnerabilities in dependencies | `0` | **BLOCKER** if `> 0` critical/high |
| Outdated major dependencies | `< 3` | **WARNING** if `> 5` |
| Dev dependencies in production build | `0` | **BLOCKER** if `> 0` |
| Unpinned critical dependencies | `< 3` | **WARNING** if `> 5` |
| Unused dependencies | `< 3` | **WARNING** if `> 5` |
| License compliance issues | `0` | **WARNING** if any found |

---

## 17. Deliverable Format

```markdown
# Production Readiness Report

## Overall Score: <N>/100

| Gate | Status | Score | Blockers | Warnings |
|------|--------|-------|----------|----------|
| 1. Repository Health | PASS/FAIL | <N> | <N> | <N> |
| 2. Codebase Metrics | PASS/FAIL | <N> | <N> | <N> |
| 3. Security Audit | PASS/FAIL | <N> | <N> | <N> |
| 4. Architecture Audit | PASS/FAIL | <N> | <N> | <N> |
| 5. Test Coverage | PASS/FAIL | <N> | <N> | <N> |
| 6. File Security | PASS/FAIL | <N> | <N> | <N> |
| 7. Staleness | PASS/FAIL | <N> | <N> | <N> |
| 8. Code Hygiene | PASS/FAIL | <N> | <N> | <N> |
| 9. Empty / Incomplete Code | PASS/FAIL | <N> | <N> | <N> |
| 10. Unwired & Dead Code | PASS/FAIL | <N> | <N> | <N> |
| 11. Junk Code & Artifacts | PASS/FAIL | <N> | <N> | <N> |
| 12. Bug Pattern Detection | PASS/FAIL | <N> | <N> | <N> |
| 13. Error Handling | PASS/FAIL | <N> | <N> | <N> |
| 14. Dependency Health | PASS/FAIL | <N> | <N> | <N> |

## Ship Recommendation
- [ ] **READY** — All gates pass, no blockers.
- [ ] **CONDITIONAL** — Warnings present, review recommended.
- [ ] **BLOCKED** — Blockers found, must fix before ship.

## Blocking Issues (Must Fix)
1. **<Gate>**: <Issue> — <file:line>
   - Fix: <recommendation>

## Warnings (Should Fix)
1. **<Gate>**: <Issue> — <impact>
   - Fix: <recommendation>

## Quick Fixes
- <list of low-effort, high-impact fixes>

## Code Hygiene Summary
| Type | Count | Status |
|------|-------|--------|
| TODO / FIXME | <N> | <BLOCKER if > 0> |
| Placeholder / Stub | <N> | <BLOCKER if > 0> |
| Debug statements | <N> | <BLOCKER if > 0> |
| Empty functions | <N> | <BLOCKER if > 0> |
| Dead code | <N> | <WARNING if > 0> |
| Junk files | <N> | <WARNING if > 0> |
| Bug patterns | <N> | <WARNING if > 0> |
```

---

## 18. Scoring Algorithm

```
Overall Score = (
  Gate1_score  * 0.07 +   # Repository Health
  Gate2_score  * 0.07 +   # Codebase Metrics
  Gate3_score  * 0.15 +   # Security Audit
  Gate4_score  * 0.10 +   # Architecture Audit
  Gate5_score  * 0.12 +   # Test Coverage
  Gate6_score  * 0.05 +   # File Security
  Gate7_score  * 0.03 +   # Staleness
  Gate8_score  * 0.10 +   # Code Hygiene
  Gate9_score  * 0.08 +   # Empty / Incomplete Code
  Gate10_score * 0.07 +   # Unwired & Dead Code
  Gate11_score * 0.05 +   # Junk Code & Artifacts
  Gate12_score * 0.05 +   # Bug Pattern Detection
  Gate13_score * 0.03 +   # Error Handling
  Gate14_score * 0.03     # Dependency Health
)

Gate Score = 100 - (blocker_penalty * 20) - (warning_penalty * 5)
  where blocker_penalty = count of blockers
  and warning_penalty = count of warnings (capped at 10)
```

### Recommendation Thresholds
| Overall Score | Recommendation |
|---------------|----------------|
| `>= 90` | **READY** — Ship with confidence |
| `80-89` | **CONDITIONAL** — Address warnings, ship after review |
| `70-79` | **REVIEW REQUIRED** — Fix blockers before ship |
| `< 70` | **BLOCKED** — Significant issues, do not ship |

---

## 19. Production Readiness Best Practices (Industry Standard)

### Code Completeness
- [ ] **Zero TODO/FIXME** in production code
- [ ] **Zero placeholder implementations** (no `pass`, `TODO()`, `NotImplemented`)
- [ ] **Zero empty functions/classes** in production paths
- [ ] **Zero stub/dummy data** in production builds
- [ ] **Zero hacking/temporary comments** explaining workarounds

### Code Hygiene
- [ ] **Zero debug statements** (`console.log`, `print`, `debugger`) in production
- [ ] **Zero commented-out code** blocks
- [ ] **Zero backup/swap/temp files** in repo
- [ ] **Zero build artifacts** committed to source control
- [ ] **Zero source maps** in production build

### Code Quality
- [ ] **Zero dead code** (unused functions, unreachable imports)
- [ ] **Zero empty catch blocks** (swallowed exceptions)
- [ ] **Zero mutable default arguments** (Python anti-pattern)
- [ ] **Zero unsafe type assertions** (`as any`, force unwrap)
- [ ] **Zero race condition patterns** (busy waits, unsafe concurrency)

### Security
- [ ] **Zero hardcoded secrets** (API keys, tokens, passwords)
- [ ] **Zero PII** in logs or error messages
- [ ] **Zero SQL injection** patterns
- [ ] **Zero XSS vulnerabilities**
- [ ] **Input validation** on all external-facing endpoints

### Testing
- [ ] **Coverage >= 75%** overall
- [ ] **Coverage >= 90%** for critical paths
- [ ] **Zero failing tests**
- [ ] **Zero flaky tests**
- [ ] **Tests are real**, not mostly mocked

### Architecture
- [ ] **Zero circular dependencies**
- [ ] **Zero god classes** (in-degree > 30)
- [ ] **Graph density < 0.01** (modular architecture)
- [ ] **Dead code < 10** symbols

---

## 20. CI/CD Integration

### GitHub Actions Example
```yaml
- name: Production Readiness Gate
  run: |
    # Gates 1-7: Core checks
    codecortex repo inspect . --include-git-diagnostics
    codecortex cb status . --include-metrics
    codecortex cb audit . --severity-threshold low
    codecortex cg audit <repo_id> --types god_nodes,circular_deps,dead_code
    codecortex qa run --target . --max-duration 300
    codecortex fs audit . --recursive
    codecortex repo staleness . --compare-remote

    # Gates 8-11: Code hygiene & junk
    codecortex cb search . --query "TODO|FIXME|HACK|PLACEHOLDER|STUB" --regex
    codecortex cb search . --query "console\\.log|debugger;|print\\s*\\(" --regex --exclude test*
    codecortex fs search . --pattern "\\.(bak|tmp|old|swp)$" --recursive
    codecortex fs search . --pattern "dist/|build/|\\.next/" --recursive

    # Gates 12-14: Bugs & dependencies
    codecortex cb search . --query "except.*:.*pass|catch\\s*\\(\\)\\s*\\{\\s*\\}" --regex
    codecortex cb audit . --scan-categories input_validation,unsafe_patterns
    codecortex repo inspect . --include-dependency-summary
```

---

## 21. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| Run Gates 1-7 first, skip 8-14 if any gate fails | ~50% | Early exit on BLOCKER |
| `limit: 20` on all search gates (8-12) | ~40% | Cap regex search results |
| Parallel Gates 8-11 (all regex searches) | ~30% | Launch 4 searches simultaneously |
| `severity_threshold: "medium"` on Gate 3 if time-constrained | ~25% | Reduce audit noise |
| Skip Gate 14 if no `package.json` / `requirements.txt` | ~10% | No deps to audit |

### Parallel Execution
These gates are independent and can run in parallel after `repo_id` is known:
- Gates 1 (`repo:inspect`) + 2 (`cb:status`) + 7 (`repo:staleness`)
- Gates 3 (`cb:audit`) + 4 (`cb:graph:audit`) + 6 (`fs:audit`)
- Gates 8-11 (all `cb:search` regex patterns)
- Gate 5 (`cb:test:run`) should run alone (CPU intensive)

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| Any gate scores BLOCKER | Immediately flag ship as BLOCKED, but finish remaining gates for completeness |
| `compliance_score < 60` after Gate 3 | Critical security issues → ship BLOCKED regardless |
| `summary.failed > 0` after Gate 5 | Tests failing → ship BLOCKED |
| All Gates 1-7 pass with no warnings | Skip Gates 8-14 for speed, or run them for thoroughness |

### Cache Reuse
- Reuse `repo_id` from previous analysis session
- If `cb:audit` ran within 24h → use `since` parameter
- If `cb:test:run` ran within last CI run → reuse test results
- Gate 7 (`staleness`) can be skipped if `repo:sync` just ran

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [analysis-orchestra-workflow.md](analysis-orchestra-workflow.md)*
