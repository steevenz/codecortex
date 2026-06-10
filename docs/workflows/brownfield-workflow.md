---
description: Brownfield (Legacy) Code Modernization — knowledge building, safe changes, incremental migration, and service extraction
title: WFK_LGY_001-005 — Brownfield Code Modernization
workflow_id: WFK_LGY_001, WFK_LGY_002, WFK_LGY_003, WFK_LGY_004, WFK_LGY_005
version: 1.0.0
author: Steeven Andrian
standard: Aegis-Workflow-v2.0
---

# WFK_LGY_001-005: Brownfield Code Modernization

> **Goal**: Build knowledge graphs from brownfield codebases and execute safe, incremental modernization — from understanding to microservice extraction.
> **Trigger**: User asks to understand, modernize, migrate, or work with existing/legacy code.
> **Time**: 2-15 minutes (depends on repo size and workflow depth).
> **Cost**: Medium-to-high (full indexing + graph build + audits).
> **Research Basis**: Brownfield AI Development best practices (Tests as Boundaries, Documentation as Context, Incrementalism as Risk Management).
> **Codification**: Aegis-Architecture-v1.0 §5

---

## 1. Trigger Phrases

- *"Understand this legacy code"*
- *"Document existing codebase"*
- *"Map brownfield"*
- *"Add feature to old code"*
- *"Modernize / Upgrade framework"*
- *"Migrate to new architecture"*
- *"Strangler fig pattern"*
- *"Extract microservice"*
- *"Refactor legacy"*
- *"Brownfield migration"*

---

## 2. Master Decision Tree

```
User Intent
│
├──► "Understand legacy code / Document existing / Map brownfield"
│      └──► WFK_LGY_001 → Knowledge Graph Construction
│
├──► "Add feature safely / Safe change in old code"
│      └──► WFK_LGY_002 → Safe Feature Addition
│
├──► "Modernize / Upgrade framework / Incremental refactoring"
│      └──► WFK_LGY_003 → Incremental Modernization
│
├──► "Migrate to new architecture / Strangler fig pattern"
│      └──► WFK_LGY_004 → Strangler Fig Migration
│
└──► "Extract microservice / Bounded context / Service split"
       └──► WFK_LGY_005 → Service Extraction
```

---

## 3. WFK_LGY_001: Knowledge Graph Construction

> **Goal**: Make the brownfield codebase legible to future AI agents and human developers.
> **Trigger**: *"I just need to understand it first"*, *"Document this codebase"*, *"Map this project"*
> **Pipeline**: 9 phases — ingestion → analysis → graph → knowledge → audit → security → test discovery → docs → IDE memory.

### Philosophy
Legacy systems lack the structure agents need. Build **institutional memory** incrementally:
1. **Index everything** — AST, symbols, graph.
2. **Extract knowledge** — from docs, comments, READMEs.
3. **Build tests as boundaries** — before any modification.
4. **Audit before touch** — understand blast radius.

### Phase 1 — Full Repository Ingestion
```
MCP: codecortex:repository
  action: "init"
  repo_path: "/path/to/legacy"
  args: {
    vcs_type: "git",
    run_audit: true,
    parallel: true,
    max_workers: 4,
    scope: { exclude: ["vendor/", "node_modules/", "dist/", ".git/"] }
  }
```

### Phase 2 — Deep Analysis & Graph Build
```
MCP: codecortex:repository
  action: "analyze"
  repo_path: "/path/to/legacy"
  args: {
    incremental: false,
    build_graph: true,
    extract_symbols: true,
    store_embeddings: true,
    embedding_model: "codebert",
    parallel: true,
    timeout: 300
  }
```
**AI Must Read**:
| Field | Meaning |
|-------|---------|
| `repo_id` | Save for all subsequent calls |
| `graph_summary.graph_ready` | Must be `true` before graph queries |
| `graph_summary.search_ready` | Must be `true` before semantic search |
| `complexity_metrics.max_cyclomatic` | `> 15` → flag as complex |

### Phase 3 — CodeGraph Relationship Mapping
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "build",
    detect_modular: true,
    build_dependency_graph: true,
    include_core_contracts: true,
    scan_hmvc_p: true,
    max_depth: 5
  }
```

### Phase 4 — Knowledge Extraction from Documentation
```bash
# CLI approach (recommended for docs)
codecortex kg extract /path/to/legacy \
  --types architecture,api,decision,adr,guide,security
```

Or MCP:
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "README CHANGELOG ADR architecture",
    search_type: "text",
    file_pattern: "*.md",
    limit: 50
  }
```

### Phase 5 — Architecture Audit (Establish Baseline)
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "audit",
    audit_types: ["god_nodes", "circular_deps", "coupling", "dead_code", "complexity", "communities"],
    degree_threshold: 10,
    include_summary: true
  }
```
**Baseline Metrics to Record**:
| Metric | Value | Risk Threshold |
|--------|-------|----------------|
| God nodes | `<N>` | `> 0` with `in_degree > 30` |
| Circular deps | `<N>` | `> 0` → BLOCKER |
| Dead code | `<N>` | `> 20` → significant |
| Max complexity | `<N>` | `> 25` → too complex |

### Phase 6 — Security Baseline
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: ".",
    scan_categories: ["secrets", "pii", "misconfig", "vulns"],
    severity_threshold: "low",
    include_comments: false
  }
```

### Phase 7 — Test Boundary Discovery
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
**AI Must Read**:
| Field | Decision |
|-------|----------|
| `total` | `0` → no tests exist; flag for test generation |
| `frameworks[]` | Which test frameworks are in use |
| `test_files[]` | Coverage area mapping |

### Phase 8 — Generate Agent Context Files
Using extracted knowledge + graph analysis, the AI generates:
- `AGENTS.md` — Agent operating manual for this codebase
- `CLAUDE.md` — Claude-specific context
- `docs/architecture.md` — High-level architecture
- `docs/DEPENDENCIES.md` — Integration maps

### Phase 9 — Store in IDE Graph (for future sessions)
```bash
codecortex ig ingest --project LegacyProject --ide claude --repo-id <repo_id>
```

### Deliverable
A **Knowledge Graph Package**:
- Indexed repository with full AST + semantic search
- Relationship graph (modules, calls, inherits, imports)
- Extracted knowledge chunks from documentation
- Architecture audit baseline
- Security baseline
- Test boundary map
- Agent context files (`AGENTS.md`, `CLAUDE.md`)

---

## 4. WFK_LGY_002: Safe Feature Addition

> **Goal**: Add features to brownfield code without breaking existing functionality.
> **Principle**: Never touch production code without tests. Add tests first, then code.

### Step 1 — Understand the Area (from Knowledge Graph)
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "<feature-area-keyword>",
    search_type: "text",
    semantic: true,
    graph_enrichment: true,
    limit: 20
  }
```

### Step 2 — Trace Call Flow
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<entry_point_for_feature>",
    query_type: "trace_flow",
    max_depth: 5
  }
```

### Step 3 — Impact Analysis
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "impact",
    target_symbol: "<target_file>::<target_function>",
    changes: {}
  }
```
**AI Must Check**:
| Field | Threshold | Action |
|-------|-----------|--------|
| `blast_radius.risk` | `high` | Warn user, request explicit approval |
| `affected_files` | `> 10` | Flag as high blast radius |

### Step 4 — Write Tests (Test-First)
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "generate",
    target_symbol: "<target_function>",
    test_framework: "auto",
    max_duration: 300
  }
```

Or use scaffolder for test boilerplate:
```
MCP: codecortex:scaffolder
  action: "generate_class"
  args: {
    type: "test",
    name: "TestUserService",
    stack: "python",
    module: "tests.unit",
    project_name: "LegacyProject"
  }
```

### Step 5 — Implement Feature
Human or AI implements the feature. Use `fs write` for new files.

### Step 6 — Run Tests
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: ".",
    test_framework: "auto",
    max_duration: 300
  }
```

### Step 7 — Sync & Re-index
```
MCP: codecortex:repository
  action: "sync"
  repo_path: "/path/to/legacy"
  args: { mode: "auto", reindex_updated: true }
```

---

## 5. WFK_LGY_003: Incremental Modernization

> **Goal**: Break migration into discrete, reversible phases. Each phase leaves the system working.

### Phase 1 — Establish Baseline (WFK_LGY_001)
Run full knowledge graph construction if not already done.

### Phase 2 — Tooling Introduction
Add linting, type-checking, build systems WITHOUT touching production logic.
```
MCP: codecortex:scaffolder
  action: "generate_content"
  args: { file_type: "pyproject", project_name: "LegacyProject", author: "..." }
```

### Phase 3 — Structural Extraction
Extract duplicated code, modularize monoliths.
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "extract",
    target_symbol: "src/monolith.py::duplicate_logic",
    changes: { new_name: "shared_util", target_file: "src/utils/common.py" },
    dry_run: true
  }
```

### Phase 4 — Framework Migration (Component by Component)
Use `trace_flow` to identify a bounded component, then modernize it in isolation.
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "UploadModal",
    query_type: "trace_flow",
    max_depth: 2
  }
```

After isolating, refactor:
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "move",
    target_symbol: "src/old/UploadModal",
    changes: { target_file: "src/components/UploadModal.tsx" },
    dry_run: true
  }
```

### Phase 5 — Design System Integration
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: "src/components/",
    scan_categories: ["naming", "type_hints"],
    severity_threshold: "low"
  }
```

### Phase 6 — Continuous Sync
After each phase:
```
MCP: codecortex:repository
  action: "sync"
  repo_path: "/path/to/legacy"
  args: { mode: "auto", reindex_updated: true, remove_deleted: true }
```

### Compromise Hierarchy (AI Decision Priority)
When modernizing, the AI must follow this priority:
1. **BLOCKER**: Security issues and data integrity — fix or flag, no exceptions.
2. **MUST**: Do not break existing functionality.
3. **SHOULD**: Remove dead code, add type hints.
4. **CAN**: Cosmetic refactors, style improvements — defer if risky.
5. **OK temporarily**: Ugly patterns and tech debt between migration steps.

---

## 6. WFK_LGY_004: Strangler Fig Migration

> **Goal**: Gradually replace a legacy system with a new architecture while keeping the old system running.

### Step 1 — Map the Monolith
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "build",
    detect_modular: true,
    build_dependency_graph: true
  }
```

### Step 2 — Identify Strangulation Candidates
Find modules with:
- Low coupling to rest of system (`coupling.score < 0.3`)
- Clear boundaries (community detection)
- High test coverage (from `code_tester`)

```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "relationships",
    target_node: "<candidate_module>",
    relation_type: "CALLS",
    direction: "both",
    depth: 2,
    include_community: true
  }
```

### Step 3 — Scaffold New Service
```
MCP: codecortex:scaffolder
  action: "create_project"
  args: {
    name: "<CandidateService>",
    stack: "<modern_stack>",
    project_type: "microservice",
    target_path: "/path/to/new/services/",
    dry_run: false
  }
```

### Step 4 — Extract and Move
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "move",
    target_symbol: "src/monolith.py::CandidateService",
    changes: { target_file: "services/candidate/src/service.py" },
    dry_run: true
  }
```

### Step 5 — API Facade / Proxy
Use `code_search` to find all callers of the extracted service, then update them to use the new API.

### Step 6 — Verify with Tests
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: ".",
    categories: ["integration", "e2e"],
    max_duration: 600
  }
```

---

## 7. WFK_LGY_005: Service Extraction

> **Goal**: Extract a single bounded context into a standalone service.

### Step 1 — Bounded Context Identification
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "audit",
    audit_types: ["communities"],
    include_summary: true
  }
```
**AI reads**: `communities.clusters` — each cluster is a candidate bounded context.

### Step 2 — Symbol Inventory
```
MCP: codecortex:codebase
  action: "analyze"
  repo_id: "<repo_id>"
  args: {
    target: "<candidate_module_dir>",
    mode: "detailed",
    max_depth: 5,
    include_docstring: true
  }
```

### Step 3 — Dependency Audit
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<candidate_module>",
    query_type: "deps",
    max_depth: 3,
    direction: "both"
  }
```

### Step 4 — Blast Radius Analysis
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "impact",
    target_symbol: "<candidate_module>::*",
    changes: { target_file: "services/new-service/" }
  }
```

### Step 5 — Scaffold New Service
```
MCP: codecortex:scaffolder
  action: "create_project"
  args: {
    name: "<NewService>",
    stack: "<stack>",
    project_type: "microservice",
    target_path: "/path/to/services/<NewService>",
    dry_run: false
  }
```

### Step 6 — Extract & Generate Tests
```
# Move files
MCP: codecortex:filesystem
  action: "copy"
  path: "src/monolith/<candidate>/"
  args: {
    dest: "services/<NewService>/src/<candidate>/",
    create_dest_parents: true
  }

# Generate tests for extracted service
MCP: codecortex:codebase
  action: "test"
  repo_id: "<new_repo_id>"
  args: {
    sub_action: "generate",
    target_path: "services/<NewService>/",
    test_framework: "auto"
  }
```

### Step 7 — Update Callers
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "from <candidate_module> import",
    search_type: "text",
    file_pattern: "*.py",
    limit: 100
  }
```

Then update each caller to use the new service API.

---

## 8. Tool Selection Matrix: Brownfield

| Task | Primary Tool | Notes |
|------|-------------|-------|
| **Project init** | `repo:init` → `repo:analyze` | Full indexing required |
| **Code generation** | N/A | Code already exists |
| **Structure validation** | `cb:graph:build` | Detect violations, not enforce DDD |
| **Testing** | `cb:test:discover` first, then `cb:test:generate` | May need to bootstrap tests |
| **Documentation** | `CLI:kg:extract` | From existing docs |
| **Security** | `codebase:audit` + `repo:audit` | Find existing issues |
| **Refactoring** | `cb:refactor:impact` → `preview` → `apply` | Heavy use, always dry_run first |
| **Knowledge persistence** | `CLI:ig:ingest` + `CLI:ig:harvest` | Build from history |
| **Sync after changes** | `repo:sync` | **Critical** — stale graphs mislead |

---

## 9. Anti-Patterns to Avoid

### Brownfield Anti-Patterns
1. **Wholesale change** — "Modernize the application" is not tractable. Use bounded phases.
2. **No tests first** — Never modify without test boundaries. Use `cb:test:generate` if none exist.
3. **Skipping impact analysis** — Always `cb:refactor:impact` before any code movement.
4. **Stale index** — Run `repo:sync` after every modification. Stale graphs mislead the AI.
5. **Guessing context** — When docs are missing, use `CLI:kg:extract` to build context, don't hallucinate.
6. **Breaking the monolith all at once** — Use strangler fig or service extraction, not big-bang rewrite.

---

## 10. CCT Integration for Brownfield

For complex architectural decisions in brownfield modernization:

```bash
# Start a thinking session for a hard migration problem
codecortex neocortex think-start "Should we extract the payment module first or the auth module?" \
  --profile critical --project-id LegacyModernization

# Analyze a specific code context
codecortex neocortex analyze "Evaluate the coupling between monolith modules" \
  --repo-path /path/to/legacy --format insight
```

**When to use CCT**:
- Multi-domain architectural decisions
- Security vs performance trade-offs
- Framework selection debates
- Complex refactoring strategies

**When NOT to use CCT**:
- Simple file operations (use `fs` directly)
- One-off symbol lookups (use `codebase:search`)
- Test execution (use `codebase:test`)

---

## 11. Deliverable Format

```markdown
# Brownfield Modernization Report

## 1. Knowledge Baseline
- **Repo**: <name>
- **Repo ID**: <uuid>
- **Files**: <N> | **LOC**: <N> | **Symbols**: <N>
- **Graph Density**: <N> (< 0.01 = modular)

## 2. Audit Baseline
| Metric | Value | Risk |
|--------|-------|------|
| God nodes | <N> | <low/medium/high> |
| Circular deps | <N> | <BLOCKER if > 0> |
| Dead code | <N> | <warning if > 20> |
| Max complexity | <N> | <warning if > 25> |

## 3. Security Baseline
- **Compliance Score**: <N>/100
- **Critical Findings**: <N>
- **High Findings**: <N>

## 4. Test Boundary Map
- **Frameworks**: <list>
- **Test Files**: <N>
- **Coverage**: <N>%

## 5. Knowledge Assets Generated
- [x] `AGENTS.md`
- [x] `CLAUDE.md`
- [x] `docs/architecture.md`
- [x] `docs/DEPENDENCIES.md`

## 6. Recommendations
### Immediate
- <action>

### Short-term (1-2 sprints)
- <action>

### Long-term (1-3 months)
- <action>
```

---

## 12. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| `incremental: true` for `repo:analyze` | ~50% | Only index changed files |
| `max_depth: 3` for graph queries | ~30% | Most legacy deps are shallow |
| `semantic: false` when text search works | ~20% | Avoid embeddings for literal matches |
| Skip `kg:extract` if README < 100 lines | ~15% | No meaningful docs to extract |

### Parallel Execution
- Phase 1 (`repo:init`) → then Phase 2-3 can parallelize
- Phase 4 (`CLI:kg:extract`) + Phase 5 (`cb:graph:audit`) can run in parallel
- Phase 6 (`cb:audit`) + Phase 7 (`cb:test:discover`) can run in parallel
- Phase 8-9 (documentation generation) can happen while graph builds

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| `index_metadata.indexed = true` from previous session | Skip Phase 1, go straight to Phase 3 |
| User only wants to "add a feature" | Skip Phase 4-9, run WFK_LGY_002 directly |
| `graph_summary.graph_ready = true` | Skip Phase 3 (`cb:graph:build`) |
| Repo has no tests at all | Skip Phase 7 (`cb:test:discover`), generate tests instead |

### Cache Reuse
- `repo_id` from WFK_ANA_001 or WFK_IDE_001 can be reused directly
- If graph built in last session → skip Phase 3
- If audit ran in last 24h → use incremental audit
- Store knowledge graph package to avoid re-generating AGENTS.md

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [greenfield-workflow.md](greenfield-workflow.md)*
