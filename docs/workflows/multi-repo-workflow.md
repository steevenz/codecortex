---
description: Multi-Repository Analysis — compare, cross-reference, and analyze up to 50 repositories simultaneously
title: WFK_MRP_001 — Multi-Repository Analysis
workflow_id: WFK_MRP_001
version: 1.0.0
author: Steeven Andrian
standard: Aegis-Workflow-v2.0
---

# WFK_MRP_001: Multi-Repository Analysis

> **Goal**: Analyze, compare, and cross-reference multiple repositories simultaneously (up to 50).
> **Trigger**: User mentions multiple projects, cross-repo dependencies, or wants a portfolio-wide analysis.
> **Time**: 1-10 minutes (depends on repo count and size).
> **Cost**: High (scales with repo count).
> **Codification**: Aegis-Architecture-v1.0 §5 — `WFK_MRP_001`

---

## 1. Trigger Phrases

- *"Compare these repos"*
- *"Analyze all my projects"*
- *"Cross-repo dependencies"*
- *"Portfolio-wide audit"*
- *"Which repo has the best test coverage?"*
- *"Find shared code across projects"*
- *"Multi-repo status"*
- *"Organizational code health"*
- *"All my repositories"*
- *"Cross-project analysis"*

---

## 2. Pipeline Overview

```
Step 1: List Repos     (repo:list)              ───┐
Step 2: Inspect Each   (repo:inspect × N)        ───┤
Step 3: Status Each    (cb:status × N)           ───┤───► Deliverable
Step 4: Compare        (metrics comparison)      ───┤
Step 5: Cross-Search   (cb:search across repos)  ───┘
```

---

## 3. Step 1 — List All Repositories

**Purpose**: Discover all registered repositories.

### MCP Call
```
MCP: codecortex:repository
  action: "list"
  args: {
    limit: 50,
    order_by: "last_analyzed",
    offset: 0
  }
```

### AI Must Read
| Field | Usage |
|-------|-------|
| `repos[]` | List of all registered repos. |
| `repos[].repo_id` | UUID for each repo. |
| `repos[].repo_path` | Absolute path. |
| `repos[].last_analyzed` | Staleness indicator. |
| `total_count` | How many repos are registered. |

### CLI
```bash
codecortex repo list --limit 50 --order-by last_analyzed
```

---

## 4. Step 2 — Inspect Each Repository

**Purpose**: Quick health check for each repo — zero parsing, instant.

```
# For each repo in the list:
MCP: codecortex:repository
  action: "inspect"
  repo_path: "<repo_path>"
  args: {
    include_git_diagnostics: true,
    include_index_metadata: true,
    include_file_stats: true
  }
```

**Batch CLI**:
```bash
# Get health scores for all repos
for path in /path/to/repos/*/; do
  codecortex repo inspect "$path" --include-git-diagnostics --include-index-metadata
done
```

---

## 5. Step 3 — Status Snapshot per Repo

**Purpose**: Quantitative metrics for each repo — LOC, languages, symbols, graph stats.

```
# For each repo_id:
MCP: codecortex:codebase
  action: "status"
  repo_id: "<repo_id>"
  args: { include_metrics: true, include_symbols: true }
```

---

## 6. Step 4 — Comparative Analysis

**Purpose**: Compare metrics across repositories to identify outliers.

### Metrics to Compare
| Metric | What It Tells You |
|--------|-----------------|
| `ai_readiness_score` | Which repos are easiest for AI to work with |
| `summary.total_lines` | Size comparison |
| `summary.languages` | Tech stack diversity |
| `comment_ratio` | Documentation health |
| `graph_stats.density` | Architecture coupling |
| `vcs.uncommitted_changes` | Stability |
| `test_coverage` (from `cb:test:run`) | Quality gate compliance |

### Deliverable: Comparison Table
```markdown
| Repo | Files | LOC | Languages | Readiness | Density | Coverage |
|------|-------|-----|-----------|-----------|---------|----------|
| api-service | 150 | 12K | Python | 85 | 0.008 | 78% |
| web-client | 300 | 25K | TypeScript | 72 | 0.015 | 45% |
| legacy-batch | 80 | 5K | Java | 45 | 0.042 | 12% |
```

---

## 7. Step 5 — Cross-Repository Search

**Purpose**: Find shared patterns, duplicated code, or cross-repo dependencies.

```
# Search for shared library usage across repos
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id_1>"
  args: {
    query: "from shared_lib import",
    search_type: "text",
    file_pattern: "*.py",
    limit: 50
  }
```

Repeat for each repo, then compare findings.

---

## 8. Deliverable Format

```markdown
# Multi-Repository Analysis Report

## 1. Portfolio Overview
- **Total Repos**: <N>
- **Total Files**: <N>
- **Total LOC**: <N>
- **Languages**: <unique list>

## 2. Health Scorecard
| Repo | Readiness | Coverage | Density | Issues |
|------|-----------|----------|---------|--------|
| ... | ... | ... | ... | ... |

## 3. Outliers
- **Best**: <repo> (readiness <N>, coverage <N>%)
- **Needs Attention**: <repo> (readiness <N>, coverage <N>%)
- **Stale Index**: <repo> (last analyzed <date>)

## 4. Cross-Repo Findings
- **Shared Dependencies**: <list>
- **Duplicated Code**: <list>
- **Inconsistent Patterns**: <list>

## 5. Recommendations
- <repo-specific actions>
```

---

## 6. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| `limit: 50` on `repo:list` | ~30% | Cap portfolio size |
| `include_metrics: false` on `cb:status` for quick health | ~20% | Skip symbol detail |
| Run `repo:inspect` (zero parsing) before `cb:status` | ~40% | Skip heavy analysis on stale repos |
| Cross-search only on repos with shared stack | ~25% | Filter by language first |

### Parallel Execution
- Step 1 (`repo:list`) → then Steps 2-3 per repo are parallelizable
- All `repo:inspect` calls can run in parallel
- All `cb:status` calls can run in parallel (after inspect)
- Step 5 (`cb:search` cross-repo) is sequential per repo

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| `repo:list` returns 0 repos | Inform user: "No repos indexed. Run `repo:init` first." |
| Only 1 repo in portfolio | Skip multi-repo comparison, run WFK_ANA_001 instead |
| User only asks "which repo has highest coverage?" | Run Step 1 + Step 3 only |

### Cache Reuse
- `repo:list` result valid until new repo added
- `repo:inspect` results cache for 1 hour
- Reuse previous portfolio report if no repos changed

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [deep-analysis-workflow.md](deep-analysis-workflow.md)*
