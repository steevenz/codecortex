---
description: Deep Code Analysis — understand, document, and map any codebase using CodeCortex
title: WFK_ANA_001 — Deep Code Analysis
workflow_id: WFK_ANA_001
version: 2.0.0
author: Steeven Andrian
standard: Aegis-Workflow-v2.0
codification: Aegis-Architecture-v1.0 §5
---

# WFK_ANA_001: Deep Code Analysis

> **Goal**: Understand what a codebase does, its architecture, entry points, key symbols, and knowledge assets.
> **Trigger**: User asks to analyze, understand, explain, document, or map a codebase.
> **Time**: 30s (cached) to 5min (full index).
> **Cost**: Low-to-medium (escalates from `inspect` → `analyze` → `graph` only as needed).

---

## 1. Trigger Phrases

- *"Analyze this codebase"*
- *"What does this project do?"*
- *"Explain the architecture"*
- *"Document the code"*
- *"Find the entry points"*
- *"Give me an overview of this repo"*
- *"Map the codebase"*
- *"How is this project structured?"*
- *"Identify the main components"*
- *"Summarize the tech stack"*

---

## 2. Pipeline Overview

```
Phase 1: Health Check (repo:inspect) ───────┐
Phase 2: Index & Sync (repo:init → repo:analyze)
Phase 3: Status Snapshot (cb:status) ──────┤───► Deliverable
Phase 4: Symbol Analysis (cb:analyze) ─────┤
Phase 5: Graph Discovery (cb:graph) ───────┤
Phase 6: Knowledge Extraction (cb:search / kg:extract)
```

---

## 3. Phase 1 — Health Check (Zero Parsing)

**Purpose**: Fastest possible overview. Zero AST parsing. Determines if repo needs indexing.

### MCP Call
```
MCP: codecortex:repository
  action: "inspect"
  repo_path: "<user-provided-path>"
  args: {
    include_git_diagnostics: true,
    include_index_metadata: true,
    include_file_stats: true,
    include_dependency_summary: true,
    include_vcs_status: true,
    timeout_seconds: 30
  }
```

### CLI Equivalent
```bash
codecortex repo inspect /path/to/project \
  --include-git-diagnostics --include-index-metadata \
  --include-file-stats --include-dependency-summary
```

### AI Must Read
| Field | Decision Gate |
|-------|---------------|
| `ai_readiness_score` | `< 50` → proceed to Phase 2. `>= 70` → skip to Phase 3. |
| `index_metadata.indexed` | `false` → Phase 2 mandatory. |
| `vcs_status.has_uncommitted_changes` | `> 5` → warn user: "Unstable state, consider committing first." |
| `file_statistics.breakdown` | Language distribution → informs symbol analysis focus. |
| `dependency_summary.package_managers` | Framework detection (npm, pip, cargo, etc.). |
| `git_diagnostics.bus_factor_risk` | `high` → note knowledge silo risk in deliverable. |
| `git_diagnostics.churn_hotspots` | `risk=high` → flag as refactoring candidates. |

### Quick Output Example
```json
{
  "ai_readiness_score": 78,
  "index_metadata": { "indexed": true, "total_files_indexed": 150 },
  "vcs_status": { "has_uncommitted_changes": false },
  "file_statistics": {
    "total_files": 150,
    "breakdown": { "source_code_files": 100, "config_files": 20 }
  },
  "dependency_summary": {
    "package_managers": [{"type": "npm", "file": "package.json"}]
  }
}
```

---

## 4. Phase 2 — Index & Sync (One-Time Cost)

**Purpose**: Build AST index, symbol table, and relationship graph. Required once per repo.

### 4.1 Initialize Repository
```
MCP: codecortex:repository
  action: "init"
  repo_path: "<path>"
  args: {
    vcs_type: "git",
    run_audit: true,
    parallel: true,
    max_workers: 4,
    scope: {
      include: ["src/", "lib/", "app/"],
      exclude: ["vendor/", "node_modules/", "dist/", ".git/", "*.min.js"]
    }
  }
```

**Response**: Capture `repo_id` (UUID). All subsequent phases use this `repo_id`.

### 4.2 Full Analysis
```
MCP: codecortex:repository
  action: "analyze"
  repo_path: "<path>"
  args: {
    incremental: true,
    build_graph: true,
    extract_symbols: true,
    store_embeddings: true,
    embedding_model: "codebert",
    parallel: true,
    max_workers: 4,
    timeout: 300,
    dry_run: false
  }
```

### AI Must Read
| Field | Meaning |
|-------|---------|
| `repo_id` | Save this UUID. Use in all subsequent calls. |
| `index_mode` | `incremental` or `full` — notes scope of work done. |
| `indexing_summary.total_files_scanned` | Validate all expected files were indexed. |
| `indexing_summary.symbols_extracted` | Total symbols in graph. |
| `graph_summary.graph_ready` | Must be `true` before Phase 5. |
| `graph_summary.search_ready` | Must be `true` before Phase 4. |
| `complexity_metrics.max_cyclomatic` | `> 15` → flag as complex function. |
| `recommendations` | CodeCortex's own suggestions — surface to user. |

### CLI Equivalent (One-shot)
```bash
codecortex repo init /path/to/project --run-audit --parallel
codecortex repo analyze /path/to/project --build-graph --extract-symbols --parallel
```

---

## 5. Phase 3 — Codebase Status Snapshot

**Purpose**: Quantitative overview — files, lines, languages, symbols, graph stats.

### MCP Call
```
MCP: codecortex:codebase
  action: "status"
  repo_id: "<repo_id>"
  args: {
    include_metrics: true,
    include_vcs: true,
    include_symbols: true,
    language: null
  }
```

### AI Must Read
| Field | Threshold / Insight |
|-------|---------------------|
| `summary.files` | Total file count. |
| `summary.total_lines` | LOC estimate. |
| `summary.languages` | Dominant language(s). |
| `summary.comment_ratio` | `< 0.1` → under-documented. `> 0.3` → over-commented. |
| `symbols.classes` | OOP density. |
| `symbols.functions` | Function count. |
| `graph_stats.nodes` | Graph complexity. |
| `graph_stats.density` | `< 0.01` → modular architecture. `> 0.05` → tightly coupled. |
| `graph_stats.components` | `> 10` in small repo → fragmentation risk. |
| `vcs.branch` | Current branch. |
| `vcs.uncommitted_changes` | `> 0` → note in report. |
| `cached` | `true` → data from cache; may be stale if files changed. |

---

## 6. Phase 4 — Symbol-Level Analysis

**Purpose**: Deep dive into symbols — classes, functions, methods, with signatures, docstrings, call relationships.

### 6.1 Overview Mode (for large repos >1000 files)
```
MCP: codecortex:codebase
  action: "analyze"
  repo_id: "<repo_id>"
  args: {
    target: "src/",
    mode: "overview",
    max_depth: 2,
    include_docstring: false,
    page_size: 100
  }
```

### 6.2 Detailed Mode (for focused analysis)
```
MCP: codecortex:codebase
  action: "analyze"
  repo_id: "<repo_id>"
  args: {
    target: "src/",
    mode: "detailed",
    max_depth: 3,
    focus: ["class", "function", "method"],
    follow_depth: 1,
    include_docstring: true,
    include_comments: false,
    page_size: 100
  }
```

### 6.3 Symbol Focus Mode (for tracing a specific symbol)
```
MCP: codecortex:codebase
  action: "analyze"
  repo_id: "<repo_id>"
  args: {
    target: "src/core/service.py::UserService",
    mode: "symbol_focus",
    max_depth: 5,
    follow_depth: 2,
    include_docstring: true,
    include_comments: true,
    page_size: 50
  }
```

### AI Must Read
| Field | Usage |
|-------|-------|
| `symbols[].name` | Symbol name for referencing. |
| `symbols[].kind` | `class`, `function`, `method`, `variable` — taxonomy. |
| `symbols[].file` | File location. |
| `symbols[].line_start` / `line_end` | Exact location. |
| `symbols[].signature` | Type signature (if available). |
| `symbols[].docstring` | Documentation quality indicator. |
| `symbols[].calls` | Outbound calls → build call graph. |
| `symbols[].referenced_by` | Inbound references → popularity/importance. |
| `edges[].relation` | `CALLS`, `INHERITS`, `IMPORTS` → coupling detection. |
| `tree` | Directory → symbol map for navigation. |
| `meta.pagination` | `has_more` → paginate if needed. |

### Coupling Detection Rule
If `edges` contains both `INHERITS` and `CALLS` from different modules → flag as **potential architectural smell**.

---

## 7. Phase 5 — Graph Relationship Discovery

**Purpose**: Build and query the relationship graph — module boundaries, entry points, call flows.

### 7.1 Build Graph
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
    max_depth: 5,
    use_cache: true
  }
```

### 7.2 Trace Entry Points
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "main",
    query_type: "trace_flow",
    max_depth: 5,
    direction: "both"
  }
```

### 7.3 Find All Callers of a Service
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "src/services/order.py::OrderService",
    query_type: "all_callers",
    max_depth: 3,
    direction: "upstream"
  }
```

### 7.4 Find Dead Code (unused functions)
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "*",
    query_type: "dead_code",
    limit: 50
  }
```

### 7.5 Visualize (CLI)
```bash
# Generate Mermaid diagram for a module
codecortex cg query visualize OrderModule --repo-id <repo_id> --viz-format mermaid

# Generate DOT for Graphviz
codecortex cg query visualize OrderModule --repo-id <repo_id> --viz-format dot
```

---

## 8. Phase 6 — Knowledge Extraction

**Purpose**: Extract engineering documentation, architecture decisions, and API contracts from markdown/doc files.

### 8.1 Search for Documentation Files
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "architecture OR README OR ADR OR API",
    search_type: "text",
    file_pattern: "*.md",
    semantic: false,
    limit: 30
  }
```

### 8.2 Knowledge Graph Extraction (CLI)
```bash
codecortex kg extract /path/to/project \
  --types architecture,api,decision,adr,guide,security \
  --repo-id <repo_id>
```

### 8.3 Read Key Documentation Files
```
MCP: codecortex:filesystem
  action: "read"
  path: "/path/to/project/README.md"
  args: { encoding: "utf-8", limit: 200 }
```

---

## 9. Deliverable Format

The AI must synthesize findings into this structured report:

```markdown
# Codebase Analysis Report

## 1. Overview
- **Project**: <name> (from repo metadata or package.json/pyproject)
- **Languages**: <primary> (<files> files), <secondary> (<files> files)
- **Total Files**: <N> | **LOC**: <N> | **Symbols**: <N> classes, <N> functions
- **Framework**: <detected> (Next.js, FastAPI, Django, etc.)
- **AI Readiness Score**: <score>/100

## 2. Architecture
- **Structure**: <modular/monolithic/microservice>
- **Entry Points**: <list from trace_flow>
- **Key Modules**: <from modular_summary>
- **Graph Density**: <value> (< 0.01 = modular, > 0.05 = coupled)
- **Diagram**: <Mermaid from cg viz>

## 3. Key Symbols (Top 10)
| Symbol | Kind | File | Lines | Calls | Referenced By |
|--------|------|------|-------|-------|---------------|
| ... | ... | ... | ... | ... | ... |

## 4. VCS Health
- **Branch**: <branch>
- **Uncommitted Changes**: <N>
- **Churn Hotspots**: <files with risk=high>
- **Bus Factor Risk**: <low/medium/high>

## 5. Findings & Recommendations
- **Critical**: <none or list>
- **Warnings**: <list>
- **Suggestions**: <from recommendations field>

## 6. Knowledge Assets
- **Docs Found**: <N> files
- **Key Documents**: <README, architecture.md, ADRs>
- **Missing Docs**: <what's absent>
```

---

## 10. Common Variations

### 10.1 Quick Analysis (Under 30 Seconds)
Skip Phase 2-5. Use only:
1. `repo:inspect` → overview
2. `cb:status` → metrics

### 10.2 Framework-Specific Analysis
After Phase 3, use framework detection to run specific queries:
- **FastAPI**: Search for `@app.get/post` decorators
- **Django**: Search for `urlpatterns`, `models.Model`
- **Next.js**: Search for `getServerSideProps`, `app/` or `pages/`
- **React**: Search for `useEffect`, `useState` hooks

### 10.3 Incremental Re-Analysis
If repo was previously analyzed:
```
MCP: codecortex:repository
  action: "sync"
  repo_path: "<path>"
  args: { mode: "auto", reindex_updated: true, remove_deleted: true }
```
Then run Phase 3-6 on the synced index.

---

## 11. Error Handling

| Error | Cause | AI Action |
|-------|-------|-----------|
| `repo:inspect` 404 | Path doesn't exist | Ask user for correct path |
| `repo:init` 409 | Already indexed | Use `existing_repo_id`, skip Phase 2 |
| `cb:status` 404 | repo_id invalid | Re-run `repo:inspect` to resolve |
| `cb:graph:build` fails | Graph backend not configured | Falls back to SQLite edges table |
| Timeout (>300s) | Repo too large | Use `max_depth: 2`, `page_size: 50` |

---

## 12. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| `include_content: false` in search | ~30% | Only fetch file paths, not full source |
| `limit: 20` vs no limit | ~50% | Cap result size |
| Skip `semantic: true` when text match found | ~20% | Don't run embeddings if FTS5 already hit |
| Reuse `repo_id` across phases | ~10% | Avoid redundant `repo:init` |
| `cb:status` before `cb:analyze` | ~15% | Skip heavy analysis if metrics already sufficient |

### Parallel Execution
These steps are independent and can be launched in parallel after Phase 2:
- Phase 3 (`cb:status`) + Phase 4 (`cb:analyze`)
- Phase 5 (`cb:graph:build`) + Phase 6 (`CLI:kg:extract` from docs)

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| `ai_readiness_score >= 85` AND `index_metadata.indexed=true` | Skip Phase 2, go straight to Phase 3 |
| `cb:search` returns exact symbol match with full context | Skip Phase 4-5 for that symbol |
| User only asks "tech stack summary" | Run Phase 1 only, deliver immediately |
| Repo < 20 files | Skip `cb:graph:build`, use `cb:analyze` only |

### Cache Reuse
- If `repo_id` exists from previous session → skip `repo:init`
- If graph was built within last sync → skip `cb:graph:build`, use `cb:graph:query` directly
- If `cb:status` ran in last 5 minutes → reuse metrics

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [analysis-orchestra-workflow.md](analysis-orchestra-workflow.md)*
