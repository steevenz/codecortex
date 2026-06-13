---
description: Analysis Orchestra Hub — entry point for all AI-driven code analysis workflows — CODDY Codification Edition
title: Workflow Analysis Orchestra (Hub)
version: 2.0.0
author: Steeven Andrian
standard: CODDY-Workflow-v2.0
codification: WFK_ANA_001, WFK_BUG_001, WFK_PRD_001, WFK_TST_001, WFK_SEC_001, WFK_ARC_001, WFK_RFC_001
---

# Workflow: Analysis Orchestra (Hub)

> **Purpose**: Entry point and decision router for all AI-driven analysis workflows. Each workflow is now documented in its own detailed file.
> **Audience**: AI coding agents using CodeCortex MCP Server.
> **Codification Standard**: CODDY-Architecture-v1.0 §5 — `WFK_{CATEGORY}_{NNN}`
> **How to Use**: Match user intent to a WFK_* codification below, then open the linked file and follow its pipeline exactly.

---

## 1. Philosophy

The LLM does **not** guess. It follows a **decision tree** that maps user intent → workflow file → tool sequence → verification. Every workflow is:

1. **Idempotent** — safe to re-run.
2. **Incremental** — starts cheap (`inspect`), escalates only when needed (`analyze` → `graph` → `audit`).
3. **Validated** — cross-checks findings with multiple tools before reporting.
4. **Reversible** — destructive actions default to `dry_run=True`.

---

## 2. Master Decision Tree

```
User Request
    │
    ├───► "Analyze / Understand / Explain / Document"
    │       └──► WFK_ANA_001: Deep Code Analysis
    │
    ├───► "Find bugs / Fix errors / Debug / Investigate"
    │       └──► WFK_BUG_001: Bug Hunting & Diagnosis
    │
    ├───► "Is this production ready? / Review / Quality gate"
    │       └──► WFK_PRD_001: Production Readiness Checklist
    │
    ├───► "Test / Coverage / Write tests / Diagnose failures"
    │       └──► WFK_TST_001: Testing & QA Automation
    │
    ├───► "Security audit / Find secrets / Vulnerabilities"
    │       └──► WFK_SEC_001: Security & Compliance Audit
    │
    ├───► "Architecture review / Coupling / Dead code / God classes"
    │       └──► WFK_ARC_001: Architecture Audit
    │
    └───► "Refactor / Rename / Move / Modernize"
            └──► WFK_RFC_001: Safe Refactoring Pipeline
```

---

## 3. Workflow Registry

### WFK_ANA_001 — Deep Code Analysis
📄 **[deep-analysis-workflow.md](deep-analysis-workflow.md)**
- **Legacy ID**: A1
- **Goal**: Understand what a codebase does, its architecture, entry points, key symbols.
- **Trigger**: *"Analyze this codebase"*, *"Explain the architecture"*, *"Document the code"*
- **Pipeline**: `repo:inspect` → `repo:init+analyze` → `cb:status` → `cb:analyze` → `cb:graph:build+query` → `CLI:kg:extract`
- **Time**: 30s (cached) to 5min (full index)

### WFK_BUG_001 — Bug Hunting & Diagnosis
📄 **[bug-hunting-workflow.md](bug-hunting-workflow.md)**
- **Legacy ID**: A2
- **Goal**: Find root cause of bugs, trace execution paths, assess test coverage near the bug.
- **Trigger**: *"Find bugs"*, *"Debug this error"*, *"Why is this failing?"*
- **Pipeline**: `cb:search` → `cb:graph:query(callers)` → `cb:audit` → `cb:test:diagnose` → `cb:graph:query(trace_flow)`
- **Time**: 1-5 minutes

### WFK_PRD_001 — Production Readiness Checklist
📄 **[production-readiness-workflow.md](production-readiness-workflow.md)**
- **Legacy ID**: A3
- **Goal**: 7-gate quality assessment before shipping — PASS/FAIL per gate.
- **Trigger**: *"Is this production ready?"*, *"Can we ship this?"*, *"Quality gate"*
- **Pipeline**: 7 gates: `repo:inspect` → `cb:status` → `cb:audit` → `cb:graph:audit` → `cb:test:run` → `fs:audit` → `repo:staleness`
- **Output**: Overall score 0-100, blocking issues, warnings, ship recommendation

### WFK_TST_001 — Testing & QA Automation
📄 **[testing-qa-workflow.md](testing-qa-workflow.md)**
- **Legacy ID**: A4
- **Goal**: Discover, run, diagnose, and generate tests.
- **Trigger**: *"Run tests"*, *"Coverage"*, *"Generate tests"*, *"Find flaky tests"*
- **Pipeline**: `cb:test:discover` → `cb:test:run` → `cb:test:run+coverage` → `cb:test:diagnose` → `cb:test:generate`
- **Frameworks**: pytest, jest, vitest, phpunit, go_test, cargo_test, and 15+ more

### WFK_SEC_001 — Security & Compliance Audit
📄 **[security-audit-workflow.md](security-audit-workflow.md)**
- **Legacy ID**: A5
- **Goal**: Multi-layer security — code secrets, Git history leaks, file permissions, architecture security.
- **Trigger**: *"Security audit"*, *"Find secrets"*, *"OWASP scan"*, *"Compliance check"*
- **Pipeline**: `cb:audit` → `repo:audit` → `fs:audit` → `cb:graph:audit`
- **Standards**: CODDY-Security-v1.0

### WFK_ARC_001 — Architecture Audit
📄 **[architecture-audit-workflow.md](architecture-audit-workflow.md)**
- **Legacy ID**: A6
- **Goal**: Detect god nodes, circular deps, coupling, dead code, community clusters.
- **Trigger**: *"Architecture review"*, *"Find god classes"*, *"Check coupling"*, *"Dead code"*
- **Pipeline**: `cb:graph:build` → `cb:graph:audit` → `cb:graph:relationships` → `CLI:cg:viz`
- **Output**: Mermaid diagram, coupling matrix, dead code list, complexity hotspots

### WFK_RFC_001 — Safe Refactoring Pipeline
📄 **[safe-refactoring-workflow.md](safe-refactoring-workflow.md)**
- **Legacy ID**: A7
- **Goal**: Refactor safely with mandatory impact → preview → apply gates.
- **Trigger**: *"Refactor this"*, *"Rename"*, *"Move"*, *"Extract"*, *"Inline"*
- **Pipeline**: `cb:refactor:impact` → `cb:refactor:*` (dry_run=true) → `cb:refactor:*` (dry_run=false, user confirms)
- **Safety Rule**: NEVER apply without impact + preview + user confirmation

---

## 4. When to Use CLI vs MCP Tools

| Scenario | Preferred | Reason |
|----------|-----------|--------|
| AI agent inside Claude/Cursor/Windsurf | **MCP** | Native integration, structured JSON, insight injection |
| CI/CD pipeline, GitHub Actions | **CLI** | Shell-friendly, exit codes, no MCP server overhead |
| One-off manual command by human | **CLI** | Faster typing, tab completion |
| Remote server execution | **CLI with `--remote`** | Proxies to remote CodeCortex instance |
| Multi-step workflow chaining | **MCP** | Consistent response format, easy to parse |
| Bulk filesystem operations | **CLI** | `fs search` with regex + replace_text |
| Scaffolding / project generation | **Either** | `scaffolder` MCP or `codecortex sc create` CLI |
| CCT (Cognitive Critical Thinking) | **CLI `cct` subcommand** | Proxies to CCT server for deep reasoning |

### Rule of Thumb
- **MCP** when the consumer is another AI agent (structured I/O, programmatic chaining).
- **CLI** when the consumer is a human or a shell script (ergonomics, piping, CI/CD).
- Both dispatch to the **same underlying 38 domain tools** — there is no capability gap.

---

## 5. Response Interpretation Guide for AI

Every CodeCortex tool returns:
```json
{
  "success": true|false,
  "status_code": 200|400|404|500,
  "message": "human readable",
  "data": { /* tool-specific */ },
  "meta": { "timestamp", "request_id", "duration_ms" },
  "insight": { "summary", "recommendations", "risks" }  // if --ai flag or CCT enabled
}
```

### AI Must Handle:
1. **`success: false`** → Stop pipeline, report error to user, do not proceed to next phase.
2. **`status_code: 409`** (repo exists) → Reuse `existing_repo_id`, do not re-init.
3. **`data.cached: true`** → Data is from cache; note staleness in report.
4. **`insight.recommendations`** → Surface to user as actionable next steps.
5. **`meta.duration_ms > 30000`** → Note slow operation, suggest optimization.

---

*End of Workflow: Analysis Orchestra (Hub)*

#### Phase 1 — Health Check (Cheap)
```
MCP: codecortex:repository
  action: "inspect"
  repo_path: "<user-provided-path>"
  args: {
    include_git_diagnostics: true,
    include_index_metadata: true,
    include_file_stats: true,
    include_dependency_summary: true
  }
```
**Why MCP?** Fast, zero-parsing, gives `ai_readiness_score`. If `< 50`, proceed to Phase 2. If already indexed, skip to Phase 3.

#### Phase 2 — Index & Sync (One-time cost)
```
MCP: codecortex:repository
  action: "init"
  repo_path: "<path>"
  args: { run_audit: true, parallel: true, max_workers: 4 }

MCP: codecortex:repository
  action: "analyze"
  repo_path: "<path>"
  args: {
    incremental: true,
    build_graph: true,
    extract_symbols: true,
    parallel: true,
    timeout: 300
  }
```
**Why MCP?** `init` creates repo_id; `analyze` builds the full AST index + graph. CLI equivalent: `codecortex repo init <path>` then `codecortex repo analyze <path>`.

#### Phase 3 — Codebase Status Snapshot
```
MCP: codecortex:codebase
  action: "status"
  repo_path: "<path>"
  args: { include_metrics: true, include_vcs: true, include_symbols: true }
```
**Key fields to read**: `summary.files`, `summary.languages`, `symbols.classes`, `symbols.functions`, `graph_stats.nodes`, `graph_stats.edges`, `vcs.branch`, `cached`.

#### Phase 4 — Symbol-Level Analysis
```
MCP: codecortex:codebase
  action: "analyze"
  repo_id: "<repo_id>"
  args: {
    target: "src/",
    mode: "auto",
    max_depth: 3,
    include_docstring: true,
    page_size: 100
  }
```
**AI Insight**: Use `symbols[].calls` to build call graph. Use `edges[].relation` for coupling detection. Use `tree` for folder navigation.

#### Phase 5 — Graph Relationship Discovery
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "build",
    detect_modular: true,
    build_dependency_graph: true,
    scan_hmvc_p: true,
    max_depth: 5
  }
```
Then query:
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "main_entry_point",
    query_type: "trace_flow",
    max_depth: 3
  }
```

#### Phase 6 — Knowledge Extraction (Documentation)
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "README architecture overview",
    search_type: "text",
    limit: 20
  }
```

Or CLI (if running locally in shell):
```bash
# Extract engineering knowledge from docs
codecortex kg extract <path> --types architecture,api,decision,adr
```

### Deliverable
A structured report with:
- **Overview**: What the codebase does (language breakdown, framework detection)
- **Architecture**: Modular structure, entry points, call flows (Mermaid from `cg viz`)
- **Key Symbols**: Classes, services, controllers (from `code_analyze`)
- **VCS Health**: Branch, commit velocity, churn hotspots (from `repo_inspect`)
- **Knowledge Graph**: Engineering docs extracted (from `kg extract`)

---

## 4. WORKFLOW-A2: Bug Hunting & Diagnosis

### Trigger Phrases
- *"Find bugs"*, *"Why is this failing?"*, *"Debug this error"*, *"Trace this issue"*, *"What calls this function?"*

### Pipeline (5 phases)

#### Phase 1 — Symptom Search
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "<error-message-or-stack-trace-keyword>",
    search_type: "text",
    semantic: true,
    limit: 50
  }
```
**Why semantic?** Error messages in logs may not match source code exactly. Semantic search finds related code.

#### Phase 2 — Blast Radius Analysis
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<suspect_symbol>",
    query_type: "callers",
    max_depth: 3,
    direction: "both"
  }
```
**AI reads**: `nodes[]`, `edges[]` to understand who calls the buggy function and what it calls.

#### Phase 3 — Code Audit (Security + Quality)
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: "<suspect_file_or_dir>",
    scan_categories: ["vulns", "secrets", "misconfig", "type_hints", "naming", "di_compliance"],
    severity_threshold: "medium",
    use_ast: true
  }
```

#### Phase 4 — Test Diagnosis
If tests exist:
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "diagnose",
    target_path: "<test_dir>",
    test_framework: "auto",
    max_duration: 300
  }
```

#### Phase 5 — Execution Flow Trace
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<entry_point>",
    query_type: "trace_flow",
    max_depth: 5,
    end_node: "<buggy_symbol>"
  }
```
**AI Insight**: This traces the exact path from user request → bug location.

### Deliverable
- **Root Cause**: Symbol-level location with file:line
- **Call Chain**: Full caller/callee path (from `trace_flow`)
- **Audit Findings**: Security/quality issues near the bug (from `code_audit`)
- **Test Status**: Whether tests cover this path (from `code_tester`)
- **Recommended Fix**: With confidence score

---

## 5. WORKFLOW-A3: Production Readiness Checklist

### Trigger Phrases
- *"Is this production ready?"*, *"Production readiness review"*, *"Can we ship this?"*, *"Quality gate"*

### Pipeline (7 gates)

#### Gate 1 — Repository Health
```
MCP: codecortex:repository
  action: "inspect"
  repo_path: "<path>"
  args: { include_git_diagnostics: true, include_index_metadata: true }
```
**Checks**: `ai_readiness_score >= 70`, `vcs.uncommitted_changes < 5`, no `bus_factor_risk=high`.

#### Gate 2 — Codebase Metrics
```
MCP: codecortex:codebase
  action: "status"
  repo_id: "<repo_id>"
  args: { include_metrics: true, include_symbols: true }
```
**Checks**: `comment_ratio` between 0.1-0.3, `graph_stats.density < 0.01` (modular), no language anomalies.

#### Gate 3 — Security Audit
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: ".",
    scan_categories: ["secrets", "pii", "misconfig", "vulns"],
    severity_threshold: "low",
    entropy_threshold: 4.5
  }
```
**Checks**: `compliance_score >= 85`, zero `critical` findings, `high` findings < 3.

#### Gate 4 — Architecture Audit
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "audit",
    audit_types: ["god_nodes", "circular_deps", "coupling", "dead_code", "complexity"],
    degree_threshold: 10,
    include_summary: true
  }
```
**Checks**: No `god_nodes` with `in_degree > 30`, `circular_deps.count == 0`, `coupling.score < 0.7`.

#### Gate 5 — Test Coverage
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
**Checks**: All tests pass, coverage > 75% (configurable per org).

#### Gate 6 — File Security Audit
```
MCP: codecortex:filesystem
  action: "audit"
  path: "<repo_path>"
  args: { recursive: true, severity: "medium", check_permissions: true }
```
**Checks**: No sensitive files in repo, correct permissions.

#### Gate 7 — Staleness Check
```
MCP: codecortex:repository
  action: "staleness"
  repo_id: "<repo_id>"
  args: { compare_remote: true, include_local_changes: true }
```
**Checks**: Index is not stale vs remote.

### Deliverable
A **PASS/FAIL** checklist per gate with:
- Score per gate (0-100)
- Blocking issues (must-fix before ship)
- Warnings (should-fix)
- Recommendations

---

## 6. WORKFLOW-A4: Testing & QA Automation

### Trigger Phrases
- *"Run tests"*, *"What's the coverage?"*, *"Generate tests"*, *"Find flaky tests"*, *"Why did this test fail?"*

### Pipeline

#### Step 1 — Discover Tests
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: { sub_action: "discover", target_path: ".", test_framework: "auto" }
```

#### Step 2 — Run Tests
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: ".",
    test_framework: "auto",
    max_duration: 300,
    async_mode: true
  }
```

#### Step 3 — Coverage Analysis
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: ".",
    categories: ["coverage"],
    coverage_format: "summary"
  }
```

#### Step 4 — Diagnose Failures (if any failed)
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "diagnose",
    target_path: ".",
    test_names: ["failed_test_1", "failed_test_2"]
  }
```

#### Step 5 — Generate Missing Tests
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "generate",
    target_symbol: "<function_or_class_without_tests>",
    test_framework: "auto",
    max_duration: 300
  }
```

### CLI Alternative (for CI/CD pipelines)
```bash
# Discover + run + coverage in one shot
codecortex qa discover --target .
codecortex qa run --target . --framework pytest --max-duration 300
codecortex qa coverage --target .
```

---

## 7. WORKFLOW-A5: Security & Compliance Audit

### Trigger Phrases
- *"Security audit"*, *"Find secrets"*, *"Check for vulnerabilities"*, *"Compliance check"*, *"OWASP scan"*

### Pipeline

#### Step 1 — Code-Level Security Audit
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: ".",
    scan_categories: ["secrets", "pii", "misconfig", "vulns", "naming", "di_compliance"],
    severity_threshold: "low",
    entropy_threshold: 4.5,
    max_file_size_kb: 1024,
    use_ast: true,
    use_aiignore: true
  }
```

#### Step 2 — Git History Audit
```
MCP: codecortex:repository
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    secrets: true,
    include_git_history: true,
    scope: { exclude: ["vendor/", "node_modules/"] }
  }
```

#### Step 3 — File Security Audit
```
MCP: codecortex:filesystem
  action: "audit"
  path: "<repo_path>"
  args: { recursive: true, severity: "low", check_permissions: true, max_file_size_mb: 100 }
```

#### Step 4 — Architecture Security Patterns
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "audit",
    audit_types: ["security", "coupling", "complexity"],
    include_summary: true
  }
```

### Deliverable
- **Compliance Score**: 0-100
- **Findings by Severity**: Critical / High / Medium / Low
- **Category Breakdown**: Secrets, PII, Misconfig, Vulns, DI violations
- **Remediation Plan**: Per finding with `standard_ref`

---

## 8. WORKFLOW-A6: Architecture Audit

### Trigger Phrases
- *"Architecture review"*, *"Find god classes"*, *"Check coupling"*, *"Dead code detection"*, *"Circular dependencies"*

### Pipeline

#### Step 1 — Build Graph (if not exists)
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "build",
    detect_modular: true,
    build_dependency_graph: true,
    scan_hmvc_p: true,
    max_depth: 5
  }
```

#### Step 2 — Run Graph Audit
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "audit",
    audit_types: ["god_nodes", "dead_code", "circular_deps", "coupling", "complexity", "communities"],
    degree_threshold: 10,
    include_summary: true,
    limit: 50
  }
```

#### Step 3 — Relationship Exploration (for suspected耦合)
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "relationships",
    target_node: "<suspected_god_node>",
    relation_type: "CALLS",
    direction: "both",
    depth: 2,
    include_community: true,
    min_confidence: "INFERRED"
  }
```

#### Step 4 — Visualize (Optional)
```
CLI: codecortex cg query visualize <target_module> --repo-id <repo_id> --viz-format mermaid
```

### Deliverable
- **God Nodes**: Classes/functions with excessive in-degree (>30)
- **Circular Dependencies**: Cycles with suggested break points
- **Coupling Matrix**: Module pairs with score > 0.7
- **Dead Code**: Unused functions/classes
- **Community Clusters**: Leiden/Louvain detection results
- **Mermaid Diagram**: Architecture visualization

---

## 9. WORKFLOW-A7: Safe Refactoring Pipeline

### Trigger Phrases
- *"Refactor this"*, *"Rename this function"*, *"Move this class"*, *"Extract this logic"*

### Pipeline (Mandatory 3-step)

#### Step 1 — Impact Analysis (Read-only, always first)
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "impact",
    target_symbol: "src/service.py::process_order",
    changes: { new_name: "process_order_v2" }
  }
```
**AI checks**: `blast_radius.risk`. If `high` (>10 files), warn user and request explicit approval.

#### Step 2 — Preview (Dry Run)
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "rename",
    target_symbol: "src/service.py::process_order",
    changes: { new_name: "process_order_v2" },
    dry_run: true
  }
```

#### Step 3 — Apply (Only with user confirmation)
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "rename",
    target_symbol: "src/service.py::process_order",
    changes: { new_name: "process_order_v2" },
    dry_run: false
  }
```

### CLI Equivalent
```bash
# Step 1: Impact
codecortex ref impact --repo-id <id> src/service.py::process_order

# Step 2: Preview
codecortex ref rename --repo-id <id> src/service.py::process_order --new-name process_order_v2

# Step 3: Apply
codecortex ref rename --repo-id <id> src/service.py::process_order --new-name process_order_v2 --apply
```

---

## 10. When to Use CLI vs MCP Tools

| Scenario | Preferred | Reason |
|----------|-----------|--------|
| AI agent inside Claude/Cursor/Windsurf | **MCP** | Native integration, structured JSON, insight injection |
| CI/CD pipeline, GitHub Actions | **CLI** | Shell-friendly, exit codes, no MCP server overhead |
| One-off manual command by human | **CLI** | Faster typing, tab completion |
| Remote server execution | **CLI with `--remote`** | Proxies to remote CodeCortex instance |
| Multi-step workflow chaining | **MCP** | Consistent response format, easy to parse |
| Bulk filesystem operations | **CLI** | `fs search` with regex + replace_text |
| Scaffolding / project generation | **Either** | `scaffolder` MCP or `codecortex sc create` CLI |
| CCT (Cognitive Critical Thinking) | **CLI `cct` subcommand** | Proxies to CCT server for deep reasoning |

### Rule of Thumb
- **MCP** when the consumer is another AI agent (structured I/O, programmatic chaining).
- **CLI** when the consumer is a human or a shell script (ergonomics, piping, CI/CD).
- Both dispatch to the **same underlying 38 domain tools** — there is no capability gap.

---

## 11. Response Interpretation Guide for AI

Every CodeCortex tool returns:
```json
{
  "success": true|false,
  "status_code": 200|400|404|500,
  "message": "human readable",
  "data": { /* tool-specific */ },
  "meta": { "timestamp", "request_id", "duration_ms" },
  "insight": { "summary", "recommendations", "risks" }  // if --ai flag or CCT enabled
}
```

### AI Must Handle:
1. **`success: false`** → Stop pipeline, report error to user, do not proceed to next phase.
2. **`status_code: 409`** (repo exists) → Reuse `existing_repo_id`, do not re-init.
3. **`data.cached: true`** → Data is from cache; note staleness in report.
4. **`insight.recommendations`** → Surface to user as actionable next steps.
5. **`meta.duration_ms > 30000`** → Note slow operation, suggest optimization.

---

*End of Workflow: Analysis Orchestra*
