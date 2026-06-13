---
description: Master decision matrix and tool inventory for all CodeCortex AI workflows — CODDY Codification Edition
title: Workflow Master Index
version: 2.0.0
author: Steeven Andrian
standard: CODDY-Workflow-v2.0
---

# Workflow Master Index

> **Purpose**: The single entry point for AI agents using CodeCortex. Contains the complete tool inventory, comprehensive decision trees, CODDY-compliant workflow codification, and routing logic for all workflows.
> **Audience**: AI coding agents (Claude, Cursor, Windsurf, Cline, Trae, Continue).
> **Must Read Before**: Any other workflow document.
> **Codification Standard**: CODDY-Architecture-v1.0 §5 — Human codes follow `{DOMAIN}_{CATEGORY}_{NNN}` pattern.

---

## 1. CODDY Codification Standard (Applied)

### 1.1 Pattern

Per `~/.aicoders/rules/architecture.md` §5:

> - Machine IDs: UUID (12-char truncated for display)
> - Human codes: Readable business codes (e.g., `KG_001`, `KG_EXTRACT_ERROR`)
> - Error codes MUST follow domain prefix pattern: `{DOMAIN}_{number}`

**Workflow Codification**: `WFK_{CATEGORY}_{NNN}`

| Segment | Meaning | Example |
|---------|---------|---------|
| `WFK` | **WF**orkflow domain prefix | Fixed |
| `{CATEGORY}` | 3-letter functional category | `ANA` = Analysis |
| `{NNN}` | 3-digit sequence | `001`, `002` |

### 1.2 Category Prefixes

| Prefix | Category | Workflows |
|--------|----------|-----------|
| `ANA` | **AN**alysis | Deep code analysis, overview |
| `BUG` | **BUG** hunting | Bug diagnosis, tracing |
| `PRD` | **PR**o**D**uction | Production readiness, gates |
| `TST` | **T**e**ST**ing | Test discovery, run, coverage, generate |
| `SEC` | **SEC**urity | Security audit, compliance |
| `ARC` | **ARC**hitecture | Architecture audit, coupling, communities |
| `RFC` | **R**e**F**a**C**toring | Safe refactoring, impact analysis |
| `GRN` | **GR**ee**N**field | New project scaffolding |
| `LGY` | **L**e**GY**acy | Legacy knowledge, modernization |
| `IDE` | **IDE** context | IDE memory, context ingestion |
| `SCH` | **S**ear**CH** | Advanced search & discovery |
| `MRP` | **M**ulti-**R**e**P**o | Multi-repository analysis |
| `CCT` | **C**reative **C**ritical **T**hinking | Deep reasoning, architecture decisions |
| `SYN` | **SYN**c | Incremental sync, monitoring |

### 1.3 Complete Workflow Registry

| Codification | Legacy ID | Document | Trigger |
|--------------|-----------|----------|---------|
| `WFK_ANA_001` | A1 | `deep-analysis-workflow.md` | *"Analyze this codebase"* |
| `WFK_BUG_001` | A2 | `bug-hunting-workflow.md` | *"Find bugs / Debug"* |
| `WFK_PRD_001` | A3 | `production-readiness-workflow.md` | *"Is this production ready?"* |
| `WFK_TST_001` | A4 | `testing-qa-workflow.md` | *"Run tests / Coverage"* |
| `WFK_SEC_001` | A5 | `security-audit-workflow.md` | *"Security audit"* |
| `WFK_ARC_001` | A6 | `architecture-audit-workflow.md` | *"Architecture review"* |
| `WFK_RFC_001` | A7 | `safe-refactoring-workflow.md` | *"Refactor / Rename"* |
| `WFK_GRN_001` | G1 | `greenfield-workflow.md` §3 | *"Create new project"* |
| `WFK_GRN_002` | G2 | `greenfield-workflow.md` §4 | *"Help me choose stack"* |
| `WFK_GRN_003` | G3 | `greenfield-workflow.md` §5 | *"Full DDD scaffold"* |
| `WFK_LGY_001` | L1 | `brownfield-workflow.md` §3 | *"Understand legacy code"* |
| `WFK_LGY_002` | L2 | `brownfield-workflow.md` §4 | *"Add feature to legacy"* |
| `WFK_LGY_003` | L3 | `brownfield-workflow.md` §5 | *"Modernize / Upgrade"* |
| `WFK_LGY_004` | L4 | `brownfield-workflow.md` §6 | *"Strangler fig migration"* |
| `WFK_LGY_005` | L5 | `brownfield-workflow.md` §7 | *"Extract microservice"* |
| `WFK_IDE_001` | — | `ide-context-workflow.md` | *"Ingest to memory / Search IDE"* |
| `WFK_SCH_001` | — | `search-discovery-workflow.md` | *"Find symbol / Search code"* |
| `WFK_MRP_001` | — | `multi-repo-workflow.md` | *"Compare multiple separate repos"* |
| `WFK_MNR_001` | — | `mono-repo-workflow.md` | *"Analyze mono-repo workspace / Nx / pnpm"* |
| `WFK_CCT_001` | — | `cct-reasoning-workflow.md` | *"Architecture decision / Deep reasoning"* |
| `WFK_SYN_001` | — | `brownfield-workflow.md` §5 Phase 6 | *"Sync index / Check staleness"* |

---

## 2. Comprehensive AI Decision Tree

### 2.1 Master Intent Router

```
User Intent
│
├──► CODE ANALYSIS
│   │
│   ├──► "Analyze / Understand / Explain / Document / Map"
│   │      └──► WFK_ANA_001 → Deep Code Analysis
│   │           (repo:inspect → repo:init+analyze → cb:status → cb:analyze → cb:graph:build → CLI:kg:extract)
│   │
│   ├──► "Find bugs / Debug / Trace / Why is this failing?"
│   │      └──► WFK_BUG_001 → Bug Hunting & Diagnosis
│   │           (cb:search → cb:graph:query(callers) → cb:audit → cb:test:diagnose → cb:graph:query(trace_flow))
│   │
│   ├──► "Is this production ready? / Can we ship? / Quality gate"
│   │      └──► WFK_PRD_001 → Production Readiness Checklist
│   │           (7 gates: repo:inspect → cb:status → cb:audit → cb:graph:audit → cb:test:run → fs:audit → repo:staleness)
│   │
│   └──► "Architecture review / Coupling / God classes / Dead code / Circular deps"
│          └──► WFK_ARC_001 → Architecture Audit
│               (cb:graph:build → cb:graph:audit → cb:graph:relationships → CLI:cg:viz)
│
├──► TESTING & QA
│   │
│   ├──► "Run tests / What's the coverage? / Test results"
│   │      └──► WFK_TST_001 → Testing & QA Automation
│   │           (cb:test:discover → cb:test:run → cb:test:run+coverage)
│   │
│   ├──► "Why did this test fail? / Diagnose / Flaky tests"
│   │      └──► WFK_TST_001 → Step 4: Diagnose
│   │
│   └──► "Generate tests / Write tests for X / Missing coverage"
│          └──► WFK_TST_001 → Step 5: Generate
│               (cb:test:generate + scaffolder:generate_class type=test)
│
├──► SECURITY
│   │
│   ├──► "Security audit / Find secrets / Vulnerabilities / OWASP"
│   │      └──► WFK_SEC_001 → Security & Compliance Audit
│   │           (cb:audit → repo:audit → fs:audit → cb:graph:audit)
│   │
│   └──► "Compliance check / Are we leaking credentials? / PII scan"
│          └──► WFK_SEC_001 → Security & Compliance Audit
│               (cb:audit categories=secrets,pii,misconfig,vulns)
│
├──► REFACTORING
│   │
│   ├──► "Refactor / Rename / Move / Extract / Inline / Change signature"
│   │      └──► WFK_RFC_001 → Safe Refactoring Pipeline
│   │           (cb:refactor:impact → cb:refactor:* dry_run=true → cb:refactor:* dry_run=false + user confirm)
│   │
│   └──► "Modernize / Upgrade framework / Brownfield migration"
│          └──► WFK_LGY_003 → Incremental Modernization
│               (cb:graph:audit → tooling → structural extraction → framework migration → continuous sync)
│
├──► PROJECT LIFECYCLE
│   │
│   ├──► "Create new project / Scaffold / Bootstrap / Init"
│   │      └──► WFK_GRN_001 → Stack-Known Scaffolding
│   │           (scaffolder:validate_name → scaffolder:get_stack → scaffolder:create dry_run → scaffolder:create → scaffolder:generate_class → repo:init)
│   │
│   ├──► "I don't know the stack / Help me choose"
│   │      └──► WFK_GRN_002 → Stack Discovery & Decision
│   │           (scaffolder:list_stacks → scaffolder:get_stack × N → scaffolder:list_licenses → AI recommendation)
│   │
│   ├──► "Full DDD project / Hexagonal architecture"
│   │      └──► WFK_GRN_003 → DDD-Aware Full Scaffold
│   │           (domain layer → application layer → infrastructure → interface → graph validation)
│   │
│   ├──► "Understand legacy code / Document brownfield / Map existing"
│   │      └──► WFK_LGY_001 → Knowledge Graph Construction
│   │           (repo:init+analyze → cb:graph:build → CLI:kg:extract → cb:graph:audit → cb:audit → cb:test:discover → AGENTS.md)
│   │
│   ├──► "Add feature to legacy / Safe change in old code"
│   │      └──► WFK_LGY_002 → Safe Feature Addition
│   │           (cb:search → cb:graph:query(trace_flow) → cb:refactor:impact → cb:test:generate → implement → cb:test:run → repo:sync)
│   │
│   ├──► "Migrate to new architecture / Strangler fig"
│   │      └──► WFK_LGY_004 → Strangler Fig Migration
│   │           (cb:graph:build → community detection → scaffold new service → cb:refactor:move → API facade → verify)
│   │
│   └──► "Extract microservice / Bounded context extraction"
│          └──► WFK_LGY_005 → Service Extraction
│               (cb:graph:audit communities → symbol inventory → dependency audit → cb:refactor:impact → scaffold → extract)
│
├──► SEARCH & DISCOVERY
│   │
│   ├──► "Find symbol / Search code / Where is X defined?"
│   │      └──► WFK_SCH_001 → Advanced Search & Discovery
│   │           (cb:search text → cb:search semantic → cb:search graph_enriched → cb:analyze symbol_focus)
│   │
│   ├──► "Semantic search / Conceptually related code"
│   │      └──► WFK_SCH_001 → Semantic Mode
│   │
│   ├──► "Trace call chain / Who calls this? / What does this call?"
│   │      └──► WFK_SCH_001 → Graph-Enriched Search
│   │           (cb:graph:query callers/callees → cb:graph:query trace_flow)
│   │
│   └──► "Find dead code / Unused functions"
│          └──► WFK_SCH_001 → Dead Code Discovery
│               (cb:graph:query dead_code)
│
├──► CONTEXT & MEMORY
│   │
│   ├──► "Ingest this project to memory / Remember this codebase"
│   │      └──► WFK_IDE_001 → IDE Context Ingestion
│   │           (repo:init+analyze → CLI:kg:extract → CLI:ig:ingest)
│   │
│   ├──► "Search my previous work / IDE memories"
│   │      └──► WFK_IDE_001 → IDE Graph Search
│   │           (CLI:ig:search → CLI:ig:harvest)
│   │
│   └──► "Build knowledge from docs / Extract architecture decisions"
│          └──► WFK_LGY_001 → Knowledge Graph Construction (Phase 4)
│               (CLI:kg:extract types=architecture,adr,decision)
│
├──► REASONING & DECISIONS
│   │
│   ├──► "Should I use X or Y? / Architecture decision / Trade-off analysis"
│   │      └──► WFK_CCT_001 → CCT Deep Reasoning
│   │           (CLI:cct:think-start → CLI:cct:analyze → synthesis)
│   │
│   ├──► "Evaluate this design / Review this approach"
│   │      └──► WFK_CCT_001 → CCT Analyze Mode
│   │
│   └──► "Complex multi-domain problem / Hard refactoring strategy"
│          └──► WFK_CCT_001 → CCT Think-Start
│               (CLI:cct:think-start --profile critical)
│
├──► MONO-REPO WORKSPACES
│   │
│   ├──► "Mono-repo / pnpm workspace / Yarn workspaces / Nx / Turborepo"
│   │      └──► WFK_MNR_001 → Mono-Repository Analysis
│   │           (workspace discovery → package graph → affected testing)
│   │
│   ├──► "Package dependency graph within a repo"
│   │      └──► WFK_MNR_001 → Package Dependency Analysis
│   │
│   ├──► "Affected tests / Which packages changed?"
│   │      └──► WFK_MNR_001 → Affected Detection
│   │
│   └──► "Cross-package refactoring / Workspace boundaries"
│          └──► WFK_MNR_001 → Cross-Package Impact Analysis
│
└──► OPERATIONS & MONITORING
    │
    ├──► "Sync index after changes / Re-index / Update graph"
    │      └──► WFK_SYN_001 → Incremental Sync & Monitoring
    │           (repo:sync mode=auto → cb:graph:build use_cache=true)
    │
    ├──► "Is the index stale? / Check freshness"
    │      └──► WFK_SYN_001 → Staleness Check
    │           (repo:staleness compare_remote=true → reindex if needed)
    │
    ├──► "Compare multiple repos / Cross-repo analysis"
    │      └──► WFK_MRP_001 → Multi-Repository Analysis
    │           (repo:list → repo:inspect × N → cb:status × N → compare metrics)
    │
    └──► "Visualize architecture / Generate diagram"
           └──► WFK_ARC_001 → Step 4: Visualization
                (CLI:cg:viz --format mermaid / dot)
```

### 2.2 Quick Intent Matcher

| Keywords in User Input | Likely Workflow | Confidence |
|------------------------|-----------------|------------|
| analyze, understand, explain, document, map, overview | `WFK_ANA_001` | High |
| bug, debug, trace, failing, error, crash, exception | `WFK_BUG_001` | High |
| production ready, ship, quality gate, release check | `WFK_PRD_001` | High |
| test, coverage, pytest, jest, unittest, diagnose | `WFK_TST_001` | High |
| security, secret, vulnerability, OWASP, compliance, PII | `WFK_SEC_001` | High |
| architecture, coupling, god class, dead code, circular, modular | `WFK_ARC_001` | High |
| refactor, rename, move, extract, inline, signature | `WFK_RFC_001` | High |
| create project, scaffold, bootstrap, new project, init | `WFK_GRN_001` | High |
| legacy, brownfield, old code, understand existing, upgrade | `WFK_LGY_001` | High |
| modernize, migration, framework upgrade, strangler fig | `WFK_LGY_003/004` | High |
| search, find symbol, where is, lookup, discover | `WFK_SCH_001` | High |
| memory, context, ingest, IDE graph, remember | `WFK_IDE_001` | High |
| compare repos, multi-repo, cross-repo, portfolio | `WFK_MRP_001` | High |
| mono-repo, pnpm workspace, nx, turborepo, lerna, yarn workspace | `WFK_MNR_001` | High |
| affected tests, package dependencies, workspace packages | `WFK_MNR_001` | High |
| should I, decision, trade-off, architecture choice, evaluate | `WFK_CCT_001` | High |
| sync, stale, reindex, update index, refresh | `WFK_SYN_001` | High |
| visualize, diagram, mermaid, graphviz, DOT | `WFK_ARC_001` | Medium |

---

## 3. CLI vs MCP — Comprehensive Decision Tree

### 3.1 The Binary Decision Tree

```
Is the consumer an AI agent (Claude, Cursor, Windsurf, etc.)?
├── YES
│   ├── Is the task CCT deep reasoning (complex architecture decisions)?
│   │   ├── YES → Use CLI `cct` subcommand (proxies to CCT cognitive server)
│   │   └── NO  → Use MCP tools (native IDE integration, structured JSON)
│   │
│   └── Is the task a one-off command the user explicitly wants as CLI?
│       ├── YES → Provide CLI equivalent
│       └── NO  → Use MCP tools (default for AI agents)
│
└── NO (Human or automation)
    ├── Is this a CI/CD pipeline or shell script?
    │   ├── YES → Use CLI (exit codes, piping, no MCP overhead)
    │   └── NO
    │       ├── Is this a one-off manual command by a human?
    │       │   ├── YES → Use CLI (ergonomics, tab completion, history)
    │       │   └── NO  → Use MCP tools (programmatic access, structured output)
    │       └── Is this remote server execution?
    │           ├── YES → Use CLI with `--remote` flag
    │           └── NO  → Default to CLI
```

### 3.2 When to Use MCP Tools (Definitive List)

Use **MCP tools** when ANY of the following is true:

| Condition | Reason | Example |
|-----------|--------|---------|
| Consumer is an **AI agent** inside MCP-enabled IDE | Native integration, structured JSON response, `insight` field injection | Claude Desktop, Cursor, Windsurf |
| **Multi-step workflow chaining** | Consistent `{success, data, meta}` envelope, easy programmatic parsing | WFK_ANA_001 6-phase pipeline |
| **Real-time tool calling** | Tools appear as functions LLM can invoke directly | `codecortex:codebase:search` |
| **Need CCT-enriched responses** | `insight` field with `summary`, `recommendations`, `risks` | `--ai` flag or CCT enabled |
| **Filesystem ops in AI chat** | `fs_manage` + `fs_search` with regex + replace preview | `fs:search` with graph enrichment |
| **Cross-platform safety required** | No shell escaping, Windows-safe paths, Unicode-safe output | Path with spaces or Unicode |
| **Response must be machine-parseable** | JSON envelope with guaranteed schema | Automated report generation |
| **Error handling must be programmatic** | `success`, `status_code`, `error_code` fields | Retry logic, conditional branching |
| **Inside chat-based IDE interface** | User is typing in chat, not terminal | "Analyze this codebase" in Claude |

### 3.3 When to Use CLI (Definitive List)

Use **CLI** (`codecortex <domain> <command>`) when ANY of the following is true:

| Condition | Reason | Example |
|-----------|--------|---------|
| Consumer is a **human developer** at terminal | Ergonomics, tab completion, shell history, piping | `codecortex cb search "auth"` |
| **CI/CD pipeline** (GitHub Actions, GitLab CI, etc.) | Exit codes (`0`/`1`), no MCP server startup overhead | `codecortex qa run` in `.github/workflows/ci.yml` |
| **One-off manual exploration** | Faster typing vs composing JSON payload | `codecortex repo inspect .` |
| **Remote execution** | `--remote` flag proxies to remote CodeCortex instance | `codecortex --remote http://server:8001` |
| **Batch operations** | `fs search` with `--replace-text` and `--dry-run` | Bulk find-replace across repo |
| **CCT deep reasoning** | `cct` subcommand proxies to CCT cognitive server | `codecortex cct think-start "..."` |
| **Scripting / automation** | Bash/PowerShell scripts, cron jobs, pre-commit hooks | `codecortex repo sync` in `.sh` |
| **Piping to other tools** | Output piped to `jq`, `grep`, `awk` | `codecortex cb status . \| jq '.data'` |
| **Offline / air-gapped environments** | CLI can work without MCP server running | Local execution mode |
| **Debugging tool behavior** | Human wants to see raw output | `codecortex --verbose` |

### 3.4 The Golden Rule

> **MCP and CLI dispatch to the exact same 38 domain tools.** There is zero capability difference. The choice is purely about **who is consuming the output** and **how they want to consume it**.

| Consumer | Context | Preferred | Example |
|----------|---------|-----------|---------|
| AI Agent | Claude Desktop / Cursor / Windsurf | **MCP** | `codecortex:codebase` tool call |
| AI Agent | Needs CCT reasoning | **CLI `cct`** | `codecortex cct analyze "..."` |
| Human Developer | Terminal / shell | **CLI** | `codecortex cb search "auth"` |
| CI/CD Pipeline | GitHub Actions, GitLab CI | **CLI** | `codecortex qa run --target .` |
| Shell Script | Bash, PowerShell, cron | **CLI** | `codecortex repo sync /path` |
| Remote Server | Over network | **CLI `--remote`** | `codecortex --remote http://server` |
| IDE Plugin | VS Code extension | **MCP** | Direct tool invocation |
| Notebook | Jupyter, Google Colab | **CLI** | `!codecortex cb status` |
| API Consumer | External service | **HTTP API** | `POST /codecortex-api/v1/sync` |

---

## 4. AI Agent Execution Protocol

When a user gives a command, the AI MUST follow this protocol:

```
Step 1: INTENT CLASSIFICATION
  Parse the user's natural language command.
  Match against Section 2 "Master Intent Router" or "Quick Intent Matcher".
  Resolve to a WFK_* codification.

Step 2: TOOL INTERFACE SELECTION (MCP vs CLI)
  Is the consumer an AI agent in an MCP-enabled IDE?
  ├── YES → Use MCP tools (Section 3.2)
  │   └── EXCEPTION: CCT reasoning → Use CLI cct subcommand
  └── NO → Use CLI (Section 3.3)

Step 3: REPO_ID RESOLUTION
  If repo_path is provided:
    → Call codecortex:repository:inspect to resolve repo_id
    → If not indexed, run repo:init
  If repo_id is provided:
    → Use directly
  If neither:
    → Ask user for the project path

Step 4: WORKFLOW SELECTION
  → Load the matching workflow document from docs/workflows/
  → Follow the phase-by-phase pipeline EXACTLY
  → Do NOT skip phases or reorder steps

Step 5: RESPONSE VALIDATION
  After EVERY tool call, check:
    - success === true?
    - status_code === 200?
    - If error: STOP, report to user, do not proceed
    - If insight.present: surface recommendations
    - If cached === true: note potential staleness

Step 6: DELIVERABLE GENERATION
  Synthesize findings into the deliverable format specified in the workflow.
  Include citations: which tools were used and what data they returned.
  Reference the WFK_* codification in the report header.
```

---

## 5. Tool Inventory

### 5.1 Unified MCP Tools (4 Top-Level)

| Tool | Actions | Domain |
|------|---------|--------|
| `codecortex:repository` | init, inspect, analyze, sync, audit, staleness, list, compact, cleanup, dump, restore, git, svn | CodeRepository |
| `codecortex:filesystem` | read, write, delete, copy, move, mkdir, list, search, watch, usage, audit | Filesystem |
| `codecortex:codebase` | analyze, search, audit, graph, status, index, test, refactor | CodeAnalysis, CodeGraph, CodeIndex, CodeTester, CodeRefactor |
| `codecortex:scaffolder` | list_stacks, get_stack, validate_name, list_licenses, generate_content, generate_class, create_project | Scaffolder |

**Total**: 4 tools → 39 actions → 38 domain tools.

### 5.2 Domain-Specific Tools (38 Underlying)

| Domain | Tools |
|--------|-------|
| **CodeAnalysis** | `code_analyze`, `code_search`, `code_audit`, `code_status` |
| **CodeGraph** | `graph_search`, `graph_query`, `graph_audit`, `graph_build`, `graph_relationship`, `graph_refactor` |
| **CodeIndex** | `code_index` |
| **CodeRepository** | `repo_init`, `repo_inspect`, `repo_analyze`, `repo_sync`, `repo_audit`, `repo_staleness`, `repo_list`, `repo_db_compact`, `repo_cleanup`, `repo_git`, `repo_svn` |
| **Filesystem** | `fs_manage`, `fs_search`, `fs_watch`, `fs_df`, `fs_audit` |
| **CodeRefactor** | `refactor_symbol`, `refactor_impact`, `refactor_apply` |
| **CodeTester** | `code_tester` |
| **KnowledgeGraph** | `knowledge_extract` |
| **Scaffolder** | `scaffold_list_stacks`, `scaffold_get_stack`, `scaffold_validate_name`, `scaffold_list_licenses`, `scaffold_generate`, `scaffold_make`, `scaffold_create` |

### 5.3 CLI Domains (15+ Domains, 50+ Commands)

| Domain | Alias | Key Commands |
|--------|-------|--------------|
| `repository` | `repo` | init, inspect, analyze, sync, audit, staleness, list, compact, cleanup, dump, restore, git, svn |
| `filesystem` | `fs` | read, write, delete, search, tree, watch, usage, audit |
| `codebase` | `cb` | search, analyze, audit, status |
| `scaffolder` | `sc` | list-stacks, get-stack, validate-name, list-licenses, generate, make, create |
| `knowledge` | `kg` | extract, query, status |
| `idegraph` | `ig` | search, ingest, harvest, status |
| `codegraph` | `cg` | build, query, search, audit, relationship, refactor, viz |
| `codeindex` | `ci` | status, index, export, clear, optimize |
| `coderefactor` | `refactor`, `ref` | impact, rename, move, signature, extract, inline, rename-file, move-file, modularize |
| `codetester` | `qa`, `tester` | discover, run, coverage, diagnose, generate |
| `server` | — | status, start, stop |
| `cloud` | — | init, push, pull, sync, status |
| `cct` | — | think-start, analyze, projects, project-add, project-status, code-analyze, code-search |
| `remote` | — | status, connect, disconnect |
| `ai` | — | analyze |

---

## 6. Error Handling Protocol

### 6.1 Common Error Codes

| Error Code | Meaning | AI Action |
|------------|---------|-----------|
| `API_400` | Bad request (missing param) | Check required params, ask user for missing info |
| `API_404` | Repo/path not found | Verify path, run `repo:init` if needed |
| `API_409` | Repo already exists | Reuse `existing_repo_id`, do not re-init |
| `API_500` / `*_500` | Internal server error | Retry once, then report to user |
| `CA_001` | Missing target for code_analyze | Ask user for target file/symbol |
| `CA_010` | Missing query for code_search | Ask user for search query |
| `GRPH_004` | Path not found for graph_build | Run `repo:init` first |
| `GRPH_008` | Invalid action or missing repo_id | Provide correct repo_id or path |
| `REF_400` | Invalid refactor action/params | Verify `target_symbol` format (`file::Symbol`) |
| `REMOTE_*` | Remote connection error | Check `CODECORTEX_REMOTE` env var |
| `CCT_CONNECT_ERROR` | CCT server unreachable | Check if CCT server is running |
| `SC_001` | Invalid stack name | Run `scaffolder:list_stacks` to show valid options |
| `SC_002` | Project name validation failed | Run `scaffolder:validate_name` |

### 6.2 AI Must Never

1. **Ignore `success: false`** — Always stop and report.
2. **Assume repo_id exists** — Always verify with `repo:inspect`.
3. **Skip `dry_run` on destructive ops** — Refactoring, cleanup, delete must preview first.
4. **Hallucinate tool outputs** — Only report what the tool returned.
5. **Proceed on `status_code >= 400`** — Treat as blocking error.
6. **Bypass workflow phases** — Follow the exact pipeline in the WFK document.

---

## 7. Token Economy & Performance

### 7.1 Cost-Aware Tool Ordering

| Priority | Tool | Cost | When |
|----------|------|------|------|
| 1 | `repo:inspect` | Zero parsing, instant | Always first |
| 2 | `codebase:status` | Cache read, instant | Quick overview |
| 3 | `codebase:search` | FTS5, fast | Finding symbols |
| 4 | `codebase:graph:query` | Graph traversal, moderate | Relationship analysis |
| 5 | `repo:analyze` | 7-phase pipeline, expensive | Once per repo |
| 6 | `codebase:audit` | Full scan, expensive | Security review |
| 7 | `codebase:graph:build` | Graph construction, expensive | When graph is stale |
| 8 | `repo:sync` | Incremental, cheap | After file changes |
| 9 | `kg:extract` | Doc parsing, moderate | Knowledge building |
| 10 | `cct:think-start` | LLM reasoning, very expensive | Complex decisions only |

### 7.2 Caching Strategy

- `repo:inspect` → always fresh (zero parsing)
- `codebase:status` → check `cached` field; if `true`, data may be stale
- `codebase:search` → uses indexed data; reindex if `staleness` returns > 0
- After file modifications → run `repo:sync` to refresh index
- Graph queries → use `use_cache: true` when data is recent

---

## 8. Workflow Document Registry (Complete)

| Document | Codifications | Purpose |
|----------|---------------|---------|
| `analysis-orchestra-workflow.md` | Hub | Analysis orchestra entry point |
| `deep-analysis-workflow.md` | `WFK_ANA_001` | Deep code analysis |
| `bug-hunting-workflow.md` | `WFK_BUG_001` | Bug hunting & diagnosis |
| `production-readiness-workflow.md` | `WFK_PRD_001` | Production readiness checklist |
| `testing-qa-workflow.md` | `WFK_TST_001` | Testing & QA automation |
| `security-audit-workflow.md` | `WFK_SEC_001` | Security & compliance audit |
| `architecture-audit-workflow.md` | `WFK_ARC_001` | Architecture audit |
| `safe-refactoring-workflow.md` | `WFK_RFC_001` | Safe refactoring pipeline |
| `greenfield-workflow.md` | `WFK_GRN_001-003` | Greenfield project scaffolding |
| `brownfield-workflow.md` | `WFK_LGY_001-005` | Brownfield (legacy) modernization |
| `ide-context-workflow.md` | `WFK_IDE_001` | IDE context & memory |
| `search-discovery-workflow.md` | `WFK_SCH_001` | Advanced search & discovery |
| `multi-repo-workflow.md` | `WFK_MRP_001` | Multi-repository analysis (separate repos) |
| `mono-repo-workflow.md` | `WFK_MNR_001` | Mono-repository workspace analysis |
| `cct-reasoning-workflow.md` | `WFK_CCT_001` | CCT deep reasoning |
| `workflow-index.md` | All | **This file** — decision matrix, tool inventory |

---

*End of Workflow Master Index v2.0*
