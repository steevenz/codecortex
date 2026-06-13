---
description: IDE Context & Memory Management — ingest, search, and persist codebase knowledge across sessions
title: WFK_IDE_001 — IDE Context & Memory Management
workflow_id: WFK_IDE_001
version: 1.0.0
author: Steeven Andrian
standard: CODDY-Workflow-v2.0
---

# WFK_IDE_001: IDE Context & Memory Management

> **Goal**: Persist codebase understanding across AI coding sessions so future agents start with full context instead of cold-starting.
> **Trigger**: User asks to remember a codebase, search previous work, or build persistent knowledge.
> **Time**: 2-5 minutes (one-time ingest), <1s (search).
> **Cost**: Medium (ingest), Zero (search from cached graph).
> **Codification**: CODDY-Architecture-v1.0 §5 — `WFK_IDE_001`

---

## 1. Trigger Phrases

- *"Remember this codebase"*
- *"Ingest this project to memory"*
- *"Search my previous work"*
- *"What did we do last time?"*
- *"Find my notes about X"*
- *"Build knowledge from docs"*
- *"Context for future sessions"*
- *"IDE graph search"*
- *"Harvest IDE memories"*
- *"Persistent project context"*

---

## 2. Pipeline Overview

```
Phase 1: Index & Analyze  (repo:init+analyze) ───┐
Phase 2: Extract Docs    (kg:extract)        ───┤───► Deliverable
Phase 3: Ingest to IDE   (ig:ingest)         ───┤
Phase 4: Verify Search   (ig:search)       ───┘
```

---

## 3. Phase 1 — Index & Analyze (Same as WFK_ANA_001)

**Purpose**: Build AST index, symbol table, and relationship graph.

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
    store_embeddings: true,
    parallel: true,
    timeout: 300
  }
```

**Capture**: `repo_id` (UUID) — required for all subsequent phases.

---

## 4. Phase 2 — Knowledge Extraction from Documentation

**Purpose**: Extract architecture decisions, API docs, and guides from markdown files.

```
CLI: codecortex kg extract <path> --types architecture,api,decision,adr,guide,security
```

Or MCP:
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "README OR ARCHITECTURE OR CHANGELOG OR ADR",
    search_type: "text",
    file_pattern: "*.md",
    limit: 50
  }
```

---

## 5. Phase 3 — Ingest to IDE Graph

**Purpose**: Store the analyzed context in the IDE graph for future sessions.

### MCP Call
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "build",
    detect_modular: true,
    build_dependency_graph: true,
    include_core_contracts: true
  }
```

### CLI (IDE Graph Ingest)
```bash
codecortex ig ingest --project <project_name> --ide claude --repo-id <repo_id>
codecortex ig ingest --project <project_name> --ide cursor --repo-id <repo_id>
```

### Parameters
| Parameter | Required | Description |
|-----------|----------|-------------|
| `--project` | Yes | Human-readable project name |
| `--ide` | Yes | Target IDE: `claude`, `cursor`, `windsurf`, `trae` |
| `--repo-id` | Yes | UUID from `repo:init` |
| `--workspace-key` | No | Workspace identifier (default: `default`) |

---

## 6. Phase 4 — Verify with IDE Graph Search

**Purpose**: Confirm the context is searchable and retrievable.

### Search IDE Memories
```
CLI: codecortex ig search --project <project_name> --query "authentication flow"
```

Or:
```bash
codecortex ig search --project <project_name> --query "main entry points" --limit 20
```

### Harvest from IDE History
```bash
codecortex ig harvest --project <project_name> --ide claude
```

---

## 7. Deliverable Format

```markdown
# IDE Context Report

## 1. Ingestion Status
- **Project**: <name>
- **Repo ID**: <uuid>
- **IDE**: <claude/cursor/windsurf>
- **Files Indexed**: <N>
- **Symbols Extracted**: <N>
- **Knowledge Chunks**: <N>

## 2. Search Verification
| Query | Results | Status |
|-------|---------|--------|
| "entry points" | <N> | ✅ |
| "auth flow" | <N> | ✅ |

## 3. Context Health
- **Graph Ready**: true/false
- **Search Ready**: true/false
- **Last Sync**: <timestamp>

## 4. Future Session Resume
To resume work on this project in a new session:
```
1. Run: codecortex ig search --project <name> --query "<topic>"
2. Or:  codecortex repo inspect <path> → reuse repo_id
```
```

---

## 8. Cross-Session Resume Protocol

When a new AI session starts and the user references a previously ingested project:

```
Step 1: Search IDE graph for existing context
  CLI: codecortex ig search --project <name> --query "overview" --limit 10

Step 2: If found → load key symbols and architecture summary
  MCP: codecortex:codebase
    action: "status"
    repo_id: "<existing_repo_id>"
    args: { include_metrics: true, include_symbols: true }

Step 3: If stale (files changed) → run incremental sync
  MCP: codecortex:repository
    action: "sync"
    repo_path: "<path>"
    args: { mode: "auto", reindex_updated: true }

Step 4: Present context summary to user
  "Resumed <ProjectName>. Indexed <N> files, <N> symbols. Last sync: <time>."
```

---

## 9. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| `include_content: false` in `cb:search` | ~35% | Only fetch file paths during knowledge extraction |
| `limit: 10` for IDE graph search | ~50% | Cap memory search results |
| Skip `cb:graph:build` if `graph_ready=true` | ~40% | Reuse existing graph |
| Phase 1 + Phase 2 can be replaced with `repo:sync` if already indexed | ~60% | Skip full re-index |

### Parallel Execution
- Phase 1 (`repo:init`) + Phase 2 (`repo:analyze`) → sequential by design
- Phase 4 (`CLI:kg:extract`) + Phase 5 (`cb:graph:audit`) can run in parallel after analyze completes
- Phase 6 (`cb:audit`) + Phase 7 (`cb:test:discover`) can run in parallel
- Phase 8 (AGENTS.md generation) + Phase 9 (`CLI:ig:ingest`) are sequential

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| `index_metadata.indexed = true` | Skip Phase 1-2, run `repo:sync` only |
| User only wants to "search previous work" | Skip Phase 1-6, run Phase 7 (`CLI:ig:search`) only |
| `CLI:ig:search` returns relevant context | Skip full re-ingest, deliver immediately |
| Project already has `AGENTS.md` and `CLAUDE.md` | Skip Phase 8 |

### Cache Reuse
- `repo_id` is the master cache key — never re-init unless stale
- IDE graph (`CLI:ig:ingest`) persists across AI sessions
- `repo:sync` with `reindex_updated: true` is cheaper than full `repo:analyze`

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [deep-analysis-workflow.md](deep-analysis-workflow.md)*
