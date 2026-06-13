---
description: Mono-Repository Analysis — workspace discovery, package dependency graph, affected testing, and unified versioning within a single large repository
title: WFK_MNR_001 — Mono-Repository Analysis
workflow_id: WFK_MNR_001
version: 1.0.0
author: Steeven Andrian
standard: CODDY-Workflow-v2.0
---

# WFK_MNR_001: Mono-Repository Analysis

> **Goal**: Analyze, navigate, and manage large mono-repositories containing multiple packages, apps, or services within a single codebase.
> **Trigger**: User works with a mono-repo (pnpm workspace, Nx, Turborepo, Lerna, Yarn workspaces, npm workspaces).
> **Time**: 2-8 minutes (depends on workspace size).
> **Cost**: Medium (indexing + workspace graph + package dependency analysis).
> **Codification**: CODDY-Architecture-v1.0 §5 — `WFK_MNR_001`

---

## 0. Multi-Repo vs Mono-Repo — Critical Distinction

| Dimension | WFK_MRP_001 (Multi-Repo) | WFK_MNR_001 (Mono-Repo) |
|-----------|-------------------------|------------------------|
| **Definition** | Multiple independent repositories | Single repository containing multiple packages/apps |
| **Examples** | `api-service/`, `web-client/`, `mobile-app/` each in separate repos | `packages/core`, `packages/ui`, `apps/web`, `apps/api` in one repo |
| **VCS** | Multiple `.git` roots | One `.git` root |
| **Dependency mgmt** | Cross-repo via npm registry / git submodules | Internal via workspace links (`workspace:*`) |
| **CodeCortex focus** | Compare repos, cross-repo search | Package graph, affected testing, workspace boundaries |
| **CLI tool** | `repo:list`, `repo:inspect` per repo | `codebase:graph` with modular detection, `repo:analyze` with scope |

**Golden Rule**: If the project has a `pnpm-workspace.yaml`, `nx.json`, `turbo.json`, `lerna.json`, or `workspaces` in `package.json` → **use WFK_MNR_001**, not WFK_MRP_001.

---

## 1. Trigger Phrases

- *"This is a mono-repo"*
- *"pnpm workspace / Yarn workspaces"*
- *"Nx / Turborepo / Lerna project"*
- *"Affected tests in this workspace"*
- *"Package dependency graph"*
- *"Cross-package refactoring"*
- *"Which packages depend on X?"*
- *"Workspace boundaries"*
- *"Unified versioning / Changesets"*
- *"Build this package and its dependents"*

---

## 2. Pipeline Overview

```
Step 1: Workspace Discovery    (repo:inspect + fs:read config) ───┐
Step 2: Package Graph Build      (cb:graph:build + modular)    ───┤
Step 3: Dependency Analysis    (cb:graph:query deps)        ───┤───► Deliverable
Step 4: Affected Detection       (repo:sync + cb:graph:query)  ───┤
Step 5: Cross-Package Audit      (cb:audit scoped)             ───┘
```

---

## 3. Step 1 — Workspace Discovery

**Purpose**: Detect which mono-repo tool is used and map the workspace structure.

### 3.1 Detect Workspace Tool
```
MCP: codecortex:filesystem
  action: "read"
  path: "/path/to/project/pnpm-workspace.yaml"
  args: { encoding: "utf-8" }
```

```
MCP: codecortex:filesystem
  action: "read"
  path: "/path/to/project/nx.json"
  args: { encoding: "utf-8" }
```

```
MCP: codecortex:filesystem
  action: "read"
  path: "/path/to/project/turbo.json"
  args: { encoding: "utf-8" }
```

```
MCP: codecortex:filesystem
  action: "read"
  path: "/path/to/project/package.json"
  args: { encoding: "utf-8" }
```

### 3.2 Workspace Tool Decision Matrix

| Config File | Tool | Workspace Declaration | Key Pattern |
|-------------|------|----------------------|-------------|
| `pnpm-workspace.yaml` | pnpm | `packages:` glob list | `workspace:*` deps |
| `package.json` → `workspaces` | npm / Yarn | `workspaces: ["packages/*"]` | `file:` or `workspace:` |
| `nx.json` | Nx | `projects` or `workspaceLayout` | `nx.json` + `project.json` per package |
| `turbo.json` | Turborepo | `pipeline` build graph | `turbo run` commands |
| `lerna.json` | Lerna | `packages` array | `lerna bootstrap` |
| `Cargo.toml` → `workspace` | Cargo | `members` array | Rust mono-repos |
| `go.work` | Go workspaces | `use` directives | Go 1.18+ multi-module |

### 3.3 List Workspace Packages
```
MCP: codecortex:filesystem
  action: "list"
  path: "/path/to/project/packages"
  args: { recursive: false }
```

### AI Must Record
| Field | Meaning |
|-------|---------|
| `workspace_tool` | pnpm / npm / yarn / nx / turbo / lerna / cargo / go |
| `package_count` | Total packages in workspace |
| `app_packages` | Top-level applications |
| `lib_packages` | Shared libraries / packages |
| `root_package_json` | Root-level dependencies |

---

## 4. Step 2 — Package Graph Build

**Purpose**: Build a graph where nodes are packages and edges are inter-package dependencies.

### 4.1 Build with Modular Detection
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

### 4.2 Extract Package-Level Relationships
For **JavaScript/TypeScript** workspaces:
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "\"workspace:\" OR \"file:packages/\" OR \"file:apps/\"",
    search_type: "text",
    file_pattern: "package.json",
    limit: 100
  }
```

For **Cargo** workspaces:
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "path = \"packages/" OR path = \"libs/"",
    search_type: "text",
    file_pattern: "Cargo.toml",
    limit: 100
  }
```

### AI Must Read
| Field | Interpretation |
|-------|---------------|
| `modular_summary.modules` | Detected package boundaries |
| `dependency_graph.layers` | Layered architecture (app → lib → core) |
| `dependency_graph.circular_deps` | Circular package dependencies → BLOCKER |

---

## 5. Step 3 — Package Dependency Analysis

**Purpose**: Understand which packages depend on which, find orphans, identify high-impact packages.

### 5.1 Find Dependents of a Package
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "packages/core-utils",
    query_type: "callers",
    max_depth: 3,
    direction: "upstream"
  }
```

### 5.2 Find Package Dependencies
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "apps/web",
    query_type: "deps",
    max_depth: 2,
    direction: "downstream"
  }
```

### 5.3 Identify High-Impact Packages
Packages with many dependents = high blast radius.
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "audit",
    audit_types: ["god_nodes"],
    degree_threshold: 10,
    include_summary: true
  }
```

---

## 6. Step 4 — Affected Detection

**Purpose**: After a code change, determine which packages are affected and need testing.

### 6.1 Sync and Detect Changes
```
MCP: codecortex:repository
  action: "sync"
  repo_path: "/path/to/mono-repo"
  args: { mode: "auto", reindex_updated: true, remove_deleted: true }
```

### 6.2 Find Affected Packages (Graph Diff)
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "<changed_package>",
    query_type: "all_callers",
    max_depth: 5,
    direction: "both"
  }
```

### 6.3 Affected Test Strategy
```
MCP: codecortex:codebase
  action: "test"
  repo_id: "<repo_id>"
  args: {
    sub_action: "run",
    target_path: ".",
    test_framework: "auto",
    test_filter: "<changed_package>.*",
    max_duration: 300
  }
```

**AI Logic**:
1. Identify changed files from `repo:sync` output.
2. Map files → packages (via workspace structure).
3. Run `cb:graph:query` to find all dependent packages.
4. Run tests only for affected packages + the changed package.

---

## 7. Step 5 — Cross-Package Audit

**Purpose**: Audit scoped to specific packages or across the mono-repo.

### 7.1 Audit Specific Package
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: "packages/core-utils",
    scan_categories: ["secrets", "vulns", "type_hints", "naming"],
    severity_threshold: "medium"
  }
```

### 7.2 Audit All Packages (Portfolio Style)
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: ".",
    scan_categories: ["secrets", "vulns", "misconfig"],
    severity_threshold: "low",
    use_aiignore: true
  }
```

---

## 8. Tool Selection Matrix: Mono-Repo

| Task | Primary Tool | Mono-Repo Specific |
|------|-------------|-------------------|
| **Workspace discovery** | `fs:read` (config files) | Detect pnpm/nx/turbo/lerna |
| **Package graph** | `cb:graph:build` + `detect_modular` | Package-level nodes |
| **Cross-package deps** | `cb:graph:query` (deps/callers) | Internal `workspace:*` links |
| **Affected testing** | `cb:test:run` + `test_filter` | Only affected packages |
| **Refactoring impact** | `cb:refactor:impact` | Cross-package blast radius |
| **Security audit** | `cb:audit` (scoped per package) | Per-package or repo-wide |
| **Versioning** | `repo:git` | Changesets / semantic-release |
| **Build orchestration** | CLI `turbo run` / `nx run` | External to CodeCortex |

---

## 9. Anti-Patterns to Avoid

1. **Treating mono-repo as single package** — Always scope analysis to package level.
2. **Running all tests on every change** — Use affected detection (Step 4).
3. **Ignoring workspace boundaries** — Cross-package imports should follow workspace protocol.
4. **Refactoring without cross-package impact analysis** — `cb:refactor:impact` must cover all dependent packages.
5. **Circular package dependencies** — Flag as BLOCKER, break immediately.

---

## 10. Deliverable Format

```markdown
# Mono-Repo Analysis Report

## 1. Workspace Overview
- **Tool**: <pnpm/nx/turbo/lerna/npm/yarn>
- **Total Packages**: <N>
- **Apps**: <N> | **Libraries**: <N>
- **Root Package Manager**: <pnpm/npm/yarn>

## 2. Package Inventory
| Package | Type | Path | Dependents | Dependencies |
|---------|------|------|------------|--------------|
| core-utils | lib | packages/core-utils | 5 | 2 |
| web-app | app | apps/web | 0 | 4 |

## 3. Package Dependency Graph
```
core-utils
  → ui-components
    → web-app
  → api-service
```

## 4. High-Impact Packages
| Package | In-Degree | Risk |
|---------|-----------|------|
| core-utils | 12 | high |

## 5. Circular Dependencies
| Cycle | Packages | Action |
|-------|----------|--------|
| ... | ... | Break cycle |

## 6. Audit Results (Per Package)
| Package | Compliance Score | Critical | High |
|---------|-----------------|----------|------|
| ... | ... | ... | ... |

## 7. Affected Test Strategy
- **Changed Package**: <name>
- **Affected Packages**: <list>
- **Tests to Run**: <list>
```

---

## 11. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| `detect_modular: true` in one `cb:graph:build` | ~30% | Avoid multiple graph queries |
| `file_pattern: "package.json"` for workspace discovery | ~50% | Only read config files |
| `max_depth: 2` for package deps | ~25% | Packages rarely deeper than 2 hops |
| Skip `fs:search` for build artifacts if `.gitignore` exists | ~15% | Trust ignore rules |

### Parallel Execution
- Step 1 (config file reads) are all parallel
- Step 2 (`cb:graph:build`) → then Steps 3-5 can parallelize
- Step 3 (dependency analysis) + Step 5 (cross-package audit) can run in parallel
- Step 4 (affected detection) runs after changes detected

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| No workspace config found | Not a mono-repo. Inform user, suggest WFK_ANA_001 |
| Only 1 package in workspace | Skip package graph analysis, treat as single project |
| User only asks "affected tests for this change" | Skip Steps 1-3, run Step 4 directly |
| No code changes since last sync | Skip affected detection, deliver cached results |

### Cache Reuse
- Workspace structure rarely changes → cache package inventory
- Package dependency graph valid until `repo:sync` detects changes
- Affected test map can be cached per commit hash

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [multi-repo-workflow.md](multi-repo-workflow.md)*
