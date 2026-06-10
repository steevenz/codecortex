---
description: Bug Hunting & Diagnosis — trace, isolate, and understand bugs using CodeCortex
title: WFK_BUG_001 — Bug Hunting & Diagnosis
workflow_id: WFK_BUG_001
version: 2.0.0
author: Steeven Andrian
standard: Aegis-Workflow-v2.0
codification: Aegis-Architecture-v1.0 §5
---

# WFK_BUG_001: Bug Hunting & Diagnosis

> **Goal**: Find the root cause of bugs, trace execution paths, identify security issues near the bug, and assess test coverage.
> **Trigger**: User reports a bug, error message, failing behavior, or asks to debug.
> **Time**: 1-5 minutes.
> **Cost**: Medium (semantic search + graph queries + audit).

---

## 1. Trigger Phrases

- *"Find bugs"*
- *"Why is this failing?"*
- *"Debug this error"*
- *"Trace this issue"*
- *"What calls this function?"*
- *"Fix this crash"*
- *"Investigate the error"*
- *"This test is failing — why?"*
- *"NullPointerException in X"*
- *"Stack trace shows Y"*

---

## 2. Pipeline Overview

```
Phase 1: Symptom Search (cb:search) ─────────┐
Phase 2: Blast Radius (cb:graph:query) ──────┤
Phase 3: Code Audit (cb:audit) ─────────────┤───► Deliverable
Phase 4: Test Diagnosis (cb:test:diagnose) ───┤
Phase 5: Execution Trace (cb:graph:query(trace_flow)) ──┘
```

---

## 3. Phase 1 — Symptom Search

**Purpose**: Find the exact code location matching the error message, stack trace, or symptom.

### 3.1 Text Search (Exact Match)
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "<error-message-or-stack-trace-keyword>",
    search_type: "text",
    file_pattern: "*",
    include_content: true,
    limit: 20
  }
```

### 3.2 Semantic Search (Fuzzy / Conceptual Match)
Use when the error message doesn't match source code literally.
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "authentication token expired handling",
    search_type: "text",
    semantic: true,
    limit: 20
  }
```

### 3.3 Graph-Enriched Search (Find Related Symbols)
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "<error-keyword>",
    search_type: "text",
    semantic: true,
    graph_enrichment: true,
    graph_relations: ["CALLS", "INHERITS"],
    limit: 20
  }
```

### AI Insight
- `matches[].score` (FTS5 relevance, 0-1): Higher = more relevant text match.
- `semantic_hits[].similarity` (cosine similarity): Higher = conceptually related.
- `relationships[]` (from graph_enrichment): Shows how the matched symbol connects to others.

### Common Error Patterns to Search
| Symptom | Search Query |
|---------|-------------|
| NullPointerException / null ref | `"null"` + file where crash occurs |
| TypeError / AttributeError | `"type"` + `"error"` + suspect module |
| Memory leak | `"memory"` + `"leak"` + `"cache"` |
| Race condition | `"async"` + `"race"` + `"lock"` |
| Auth failure | `"auth"` + `"token"` + `"401"` |
| DB connection lost | `"connection"` + `"pool"` + `"timeout"` |

---

## 4. Phase 2 — Blast Radius Analysis

**Purpose**: Understand who calls the buggy function and what it calls — the full dependency web.

### 4.1 Find Callers (Upstream)
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<suspect_symbol>",
    query_type: "callers",
    max_depth: 3,
    direction: "upstream",
    limit: 50
  }
```

### 4.2 Find Callees (Downstream)
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<suspect_symbol>",
    query_type: "callees",
    max_depth: 3,
    direction: "downstream",
    limit: 50
  }
```

### 4.3 Full Call Graph (Both Directions)
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<suspect_symbol>",
    query_type: "all_callers",
    max_depth: 3,
    direction: "both"
  }
```

### AI Must Read
| Field | Interpretation |
|-------|---------------|
| `nodes[]` | All symbols in the blast radius. |
| `edges[]` | `CALLS`, `INHERITS`, `IMPORTS` relationships. |
| `total` | Number of affected symbols. `> 20` → high blast radius. |
| `path[]` (trace_path) | Direct path from entry to bug. |

---

## 5. Phase 3 — Code Audit (Security + Quality Near Bug)

**Purpose**: Check if the buggy area also has security issues, missing type hints, or DI violations.

### MCP Call
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: "<suspect_file_or_dir>",
    scan_categories: ["vulns", "secrets", "misconfig", "type_hints", "naming", "di_compliance"],
    severity_threshold: "medium",
    entropy_threshold: 4.5,
    max_file_size_kb: 1024,
    use_ast: true,
    use_aiignore: true
  }
```

### AI Must Read
| Field | Action |
|-------|--------|
| `findings[].severity` | Prioritize `critical` and `high`. |
| `findings[].confidence` | `> 0.9` → high confidence, definitely a problem. |
| `findings[].remediation` | Suggest to user as fix. |
| `findings[].standard_ref` | Reference to Aegis standard violated. |
| `compliance_score` | `< 70` → area needs broader cleanup. |

---

## 6. Phase 4 — Test Diagnosis

**Purpose**: Check if tests exist, if they cover the buggy path, and diagnose why they fail.

### 6.1 Discover Tests
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "discover",
    target_path: ".",
    test_framework: "auto"
  }
```

### 6.2 Run Tests (if user mentioned specific failures)
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: ".",
    test_filter: "<suspect_module>*",
    test_framework: "auto",
    verbose: true,
    max_duration: 300
  }
```

### 6.3 Diagnose Specific Failures
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "diagnose",
    target_path: ".",
    test_names: ["test_user_login", "test_order_processing"],
    test_framework: "auto",
    max_duration: 300
  }
```

### AI Must Read
| Field | Meaning |
|-------|---------|
| `flaky_tests[]` | Tests that fail intermittently → timing/race issues. |
| `slow_tests[]` | Tests > threshold → performance bottleneck. |
| `suggestions[]` | CodeCortex's recommendations for fixing. |
| `summary.passed` / `summary.failed` | Overall health. |

---

## 7. Phase 5 — Execution Flow Trace

**Purpose**: Trace the exact execution path from user request → bug location.

### 7.1 Trace from Entry Point to Bug
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<entry_point>",
    query_type: "trace_flow",
    max_depth: 5,
    end_node: "<buggy_symbol>",
    direction: "both"
  }
```

### 7.2 Find Shortest Path
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<entry_point>",
    query_type: "trace_path",
    end_node: "<buggy_symbol>",
    max_depth: 10
  }
```

### 7.3 Check for Circular Dependencies Near Bug
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<suspect_symbol>",
    query_type: "circular",
    max_depth: 5
  }
```

---

## 8. Deliverable Format

```markdown
# Bug Hunting Report

## 1. Symptom
- **Description**: <user's bug report>
- **Error Message**: <extracted from user input>
- **Suspected Area**: <file:line from search>

## 2. Root Cause
- **Symbol**: `<file>::<symbol>`
- **Location**: `file:line:column`
- **Code**: <relevant lines>
- **Explanation**: <why it fails>

## 3. Call Chain
```
Entry: <function>
  → <caller_1>
    → <caller_2>
      → <buggy_function>  <-- BUG HERE
        → <callee_1>
```

## 4. Related Findings
- **Security Issues**: <list from audit>
- **Quality Issues**: <missing types, naming violations>
- **Test Coverage**: <covered / not covered>

## 5. Recommended Fix
- **Change**: <specific code change>
- **Confidence**: <high/medium/low>
- **Blast Radius**: <N files affected>
- **Tests to Update**: <list>
```

---

## 9. Edge Cases

### 9.1 Bug in External Dependency
If `cb:search` shows the bug is in `node_modules/` or `vendor/`:
- Report to user: "Bug appears to be in `<package> v<version>`"
- Check `dependency_summary` for version
- Suggest: upgrade, patch, or workaround

### 9.2 No Tests Cover the Bug
- Run `cb:test:generate` for the buggy symbol
- Report: "No tests found for this path. Generating test boilerplate..."

### 9.3 Intermittent / Race Condition Bug
- Run `cb:test:diagnose` to find flaky tests
- Search for `async`, `await`, `lock`, `mutex`, `thread` in suspect area
- Recommend: add synchronization or redesign flow

---

## 10. Error Handling

| Error | Cause | AI Action |
|-------|-------|-----------|
| `cb:search` returns 0 matches | Keyword too specific | Try semantic search with broader concept |
| `cb:graph:query` 404 | Symbol not in graph | Run `repo:analyze` to rebuild index |
| `cb:audit` no findings | Clean code or wrong target | Expand target to parent directory |
| `cb:test:diagnose` no tests | No test framework detected | Run `cb:test:generate` |

---

## 11. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| Start with `search_type: "text"` (not semantic) | ~25% | FTS5 is faster and cheaper than embeddings |
| `limit: 10` for initial symptom search | ~40% | Narrow before broadening |
| Skip `graph_enrichment` if text search finds exact line | ~20% | Don't fetch relationships unnecessarily |
| `max_depth: 2` for callers/callees | ~30% | Most bugs are within 2 hops |

### Parallel Execution
- Phase 1 text search + Phase 3 audit can run in parallel (different targets)
- Phase 2 upstream callers + Phase 2 downstream callees can run in parallel

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| `cb:search` returns exact error string with file:line | Skip to Phase 3 audit only |
| `cb:audit` shows no security issues near bug | Skip Phase 3, go to Phase 4 |
| User provides exact stack trace with line number | Skip Phase 1, go straight to Phase 2 |
| Bug is in test file, not source | Run `cb:test:diagnose` immediately |

### Cache Reuse
- Reuse `repo_id` from user's previous analysis session
- If graph already built → skip graph rebuild, use `cb:graph:query` directly
- If audit ran in last hour → focus on changed files only

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [analysis-orchestra-workflow.md](analysis-orchestra-workflow.md)*
