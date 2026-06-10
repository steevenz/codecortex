---
description: Greenfield Project Creation — scaffolding new projects from scratch with DDD, clean architecture, and AI-ready structure
title: WFK_GRN_001-003 — Greenfield Project Creation
workflow_id: WFK_GRN_001, WFK_GRN_002, WFK_GRN_003
version: 1.0.0
author: Steeven Andrian
standard: Aegis-Workflow-v2.0
---

# WFK_GRN_001-003: Greenfield Project Creation

> **Goal**: Create new projects from scratch with DDD-aligned structure, clean architecture, and 100% CodeCortex tool coverage so future AI agents can operate safely.
> **Trigger**: User asks to create, scaffold, bootstrap, or init a new project.
> **Time**: 1-5 minutes (scaffold + validation).
> **Cost**: Low-to-medium (scaffolder + graph validation).
> **Codification**: Aegis-Architecture-v1.0 §5

---

## 1. Trigger Phrases

- *"Create a new project"*
- *"Scaffold a project"*
- *"Bootstrap"*
- *"Init a new repo"*
- *"I know the stack"*
- *"Help me choose the stack"*
- *"Full DDD project"*
- *"Hexagonal architecture"*
- *"Clean architecture scaffold"*
- *"Production-ready project"*

---

## 2. Master Decision Tree

```
User Intent
│
├──► "Create new project / Scaffold / Bootstrap / Init (I know the stack)"
│      └──► WFK_GRN_001 → Stack-Known Scaffolding
│
├──► "I don't know the stack / Help me choose"
│      └──► WFK_GRN_002 → Stack Discovery & Decision
│
└──► "Full DDD / Hexagonal architecture project"
       └──► WFK_GRN_003 → DDD-Aware Full Scaffold
```

---

## 3. WFK_GRN_001: Stack-Known Scaffolding

> **When**: User knows the tech stack (e.g., Python FastAPI, Next.js, Go).
> **Pipeline**: 9 phases from validation to production readiness gate.

### Philosophy
Greenfield is where AI agents excel — clear boundaries, minimal hidden dependencies, no accumulated quirks. The workflow enforces **structure from day one**.

### Phase 1 — Validate Project Identity
```
MCP: codecortex:scaffolder
  action: "validate_name"
  args: { name: "MyAwesomeProject" }
```
**AI Must Read**:
| Field | Usage |
|-------|-------|
| `slug` | URL-friendly name |
| `snake` | Python module naming |
| `pascal` | Class naming convention |
| `kebab` | Package/URL naming |

### Phase 2 — Inspect Stack Capabilities
```
MCP: codecortex:scaffolder
  action: "get_stack"
  args: { stack_name: "python" }
```
**AI Must Read**:
| Field | Usage |
|-------|-------|
| `project_types` | What templates are available (web_api, cli, ddd_hexagonal) |
| `file_conventions` | Naming standards for the stack |
| `extensions` | File extensions used |

### Phase 3 — Dry-Run Project Generation
```
MCP: codecortex:scaffolder
  action: "create_project"
  args: {
    name: "MyAwesomeProject",
    stack: "python",
    project_type: "web_api",
    target_path: "/path/to/output",
    author: "Steeven Andrian",
    email: "steeven@example.com",
    version: "0.1.0",
    license: "MIT",
    dry_run: true,
    overwrite: false
  }
```
**AI Must Read**:
| Field | Decision |
|-------|----------|
| `template_count` | Scope of what will be generated |
| `directory_count` | Folder structure preview |
| `dry_run: true` | **Never skip** — always preview first |

### Phase 4 — Generate Project (User Confirms)
```
MCP: codecortex:scaffolder
  action: "create_project"
  args: {
    name: "MyAwesomeProject",
    stack: "python",
    project_type: "web_api",
    target_path: "/path/to/output",
    author: "Steeven Andrian",
    email: "steeven@example.com",
    version: "0.1.0",
    license: "MIT",
    dry_run: false,
    overwrite: false,
    include_ai: true,
    include_trainer: false
  }
```

### Phase 5 — Generate Core DDD Classes
```
MCP: codecortex:scaffolder
  action: "generate_class"
  args: {
    type: "model",
    name: "User",
    stack: "python",
    module: "models.entities",
    project_name: "MyAwesomeProject",
    author: "Steeven Andrian",
    target_path: "/path/to/output",
    overwrite: false
  }
```
**Repeat for**: `repository`, `service`, `controller`, `dto`, `event`, `middleware`, `factory`.

**Class Type Decision Matrix**:
| Type | When to Generate | Layer |
|------|-----------------|-------|
| `model` | Domain entities / Aggregate roots | Domain |
| `repository` | Data access abstraction | Infrastructure |
| `service` | Business logic | Application |
| `controller` | HTTP/API handlers | Interface |
| `dto` | Data transfer objects | Application |
| `event` | Domain events | Domain |
| `middleware` | Cross-cutting concerns | Interface |
| `factory` | Object creation logic | Domain |

### Phase 6 — Generate DevOps Files
```
MCP: codecortex:scaffolder
  action: "generate_content"
  args: {
    file_type: "dockerfile",
    project_category: "web_api",
    project_name: "MyAwesomeProject",
    author: "Steeven Andrian",
    email: "steeven@example.com",
    license_name: "MIT"
  }
```
**Repeat for**: `docker_compose`, `env`, `gitignore`, `pyproject`, `readme`, `setup_sh`.

### Phase 7 — Initialize Repository & Index
```
MCP: codecortex:repository
  action: "init"
  repo_path: "/path/to/output/MyAwesomeProject"
  args: { vcs_type: "git", run_audit: true, parallel: true }
```

### Phase 8 — First Code Analysis (Validate Structure)
```
MCP: codecortex:codebase
  action: "status"
  repo_path: "/path/to/output/MyAwesomeProject"
  args: { include_metrics: true, include_symbols: true }
```
**Checks**: `summary.files > 0`, `symbols.classes > 0`, `vcs.branch` present.

### Phase 9 — Production Readiness Gate
Run **WFK_PRD_001** (`production-readiness-workflow.md`) on the newly created project.

### CLI Equivalent (One-shot)
```bash
codecortex sc validate-name MyAwesomeProject
codecortex sc get-stack python
codecortex sc create MyAwesomeProject --stack python --project-type web_api \
  --target-path /path/to/output --author "Steeven Andrian" --dry-run

# After user confirms:
codecortex sc create MyAwesomeProject --stack python --project-type web_api \
  --target-path /path/to/output --author "Steeven Andrian" --include-ai

# Generate classes
codecortex sc make entity User --stack python --module models.entities
codecortex sc make repository UserRepository --stack python --module models.repositories
codecortex sc make service UserService --stack python --module services

# Init repo
codecortex repo init /path/to/output/MyAwesomeProject

# Status check
codecortex cb status /path/to/output/MyAwesomeProject
```

---

## 4. WFK_GRN_002: Stack Discovery & Decision

> **When**: User doesn't know which stack to use.
> **Pipeline**: Discover → Compare → Recommend → Proceed to WFK_GRN_001.

### Step 1 — List All Stacks
```
MCP: codecortex:scaffolder
  action: "list_stacks"
  args: {}
```

### Step 2 — Get Detailed Stack Info
```
MCP: codecortex:scaffolder
  action: "get_stack"
  args: { stack_name: "python" }

MCP: codecortex:scaffolder
  action: "get_stack"
  args: { stack_name: "typescript" }
```

### Step 3 — License Selection
```
MCP: codecortex:scaffolder
  action: "list_licenses"
  args: {}
```

### Step 4 — AI Recommendation
LLM synthesizes stack comparison based on:
- User's requirements (web API, CLI, data science, etc.)
- `project_types` supported by each stack
- `file_conventions` (naming standards)
- Team expertise (inferred from conversation)

**Decision Matrix for AI**:
| Requirement | Suggested Stack | Project Type |
|-------------|-----------------|--------------|
| Web API, Python | `python` | `web_api` |
| React full-stack | `typescript` | `nextjs` |
| CLI tool | `python` or `go` | `cli` |
| Data science | `python` | `jupyter` |
| Mobile | `typescript` | `react_native` |
| Microservice | `python` or `go` | `microservice` |

Then proceed to **WFK_GRN_001** with selected stack.

---

## 5. WFK_GRN_003: DDD-Aware Full Scaffold

> **When**: Enterprises requiring strict DDD + Hexagonal Architecture.
> **Pipeline**: Scaffold → Domain → Application → Infrastructure → Interface → Validate.

### Step 1 — Scaffold with DDD project type (if available)
```
MCP: codecortex:scaffolder
  action: "create_project"
  args: {
    name: "OrderManagement",
    stack: "python",
    project_type: "ddd_hexagonal",
    target_path: "/path/to/output",
    dry_run: true
  }
```

### Step 2 — Generate Domain Layer
```bash
# Aggregate Root
codecortex sc make model Order --stack python --module domain.order

# Value Objects
codecortex sc make value_object Money --stack python --module domain.shared

# Domain Events
codecortex sc make event OrderCreated --stack python --module domain.events

# Repository Interface (port)
codecortex sc make interface OrderRepository --stack python --module domain.ports
```

### Step 3 — Generate Application Layer
```bash
# DTOs
codecortex sc make dto CreateOrderRequest --stack python --module application.dtos

# Service / Use Case
codecortex sc make service OrderService --stack python --module application.services
```

### Step 4 — Generate Infrastructure Layer
```bash
# Repository Implementation (adapter)
codecortex sc make repository SqlOrderRepository --stack python --module infrastructure.persistence

# Event Listener
codecortex sc make listener OrderCreatedListener --stack python --module infrastructure.messaging
```

### Step 5 — Generate Interface Layer
```bash
# Controller / API Handler
codecortex sc make controller OrderController --stack python --module interface.http

# Middleware
codecortex sc make middleware AuthMiddleware --stack python --module interface.http.middleware
```

### Step 6 — Validate Architecture with Graph
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "build",
    detect_modular: true,
    build_dependency_graph: true,
    scan_hmvc_p: true
  }
```

**AI Must Validate**:
| Check | Expected | If Violated |
|-------|----------|-------------|
| Dependency direction | Interface → Application → Domain | Flag circular dependency |
| No domain→infra imports | Domain should be pure | Report violation |
| Interface layer isolation | No business logic in controllers | Suggest extraction |

---

## 6. Tool Selection Matrix: Greenfield

| Task | Primary Tool | Secondary |
|------|-------------|-----------|
| Project init | `scaffolder:create_project` | `repo:init` |
| Class generation | `scaffolder:generate_class` | — |
| DevOps files | `scaffolder:generate_content` | — |
| Structure validation | `codebase:graph:build` | `codebase:status` |
| Testing | `codebase:test:generate` | `scaffolder:generate_class type=test` |
| Documentation | `scaffolder:generate_content` (README) | — |
| Security | `codebase:audit` | `repo:audit` |
| Production gate | `WFK_PRD_001` | — |

---

## 7. Anti-Patterns to Avoid

1. **Skipping `dry_run`** — Always preview scaffolding before writing.
2. **No graph validation** — After scaffolding, run `graph build` to verify DDD boundaries.
3. **Ignoring conventions** — Use `get_stack` to learn naming conventions, don't guess.
4. **No production readiness gate** — New projects must pass WFK_PRD_001 before shipping.
5. **Missing DTOs** — Never leak raw models across layers.
6. **No DI setup** — Constructor injection must be wired from day one.

---

## 8. Deliverable Format

```markdown
# Greenfield Scaffold Report

## 1. Project Identity
- **Name**: <name>
- **Slug**: <slug>
- **Stack**: <stack>
- **Project Type**: <type>

## 2. Generated Structure
- **Files**: <N>
- **Directories**: <N>
- **Classes**: <list>

## 3. Layer Coverage (DDD)
| Layer | Files | Key Classes |
|-------|-------|-------------|
| Domain | <N> | <list> |
| Application | <N> | <list> |
| Infrastructure | <N> | <list> |
| Interface | <N> | <list> |

## 4. Validation
- **Graph Build**: <pass/fail>
- **Dependency Direction**: <valid/invalid>
- **Production Gate**: <pass/fail>

## 5. Next Steps
- [ ] Run tests: `codecortex qa run --target .`
- [ ] Add environment variables
- [ ] Configure CI/CD
```

---

## 9. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| `dry_run: true` before any scaffold | ~100% on mistakes | Preview before write |
| `include_ai: true` in `create_project` | ~20% | Include AI templates in one call |
| Batch `generate_class` calls | ~30% | Generate multiple classes in parallel |
| Skip `cb:graph:build` for simple projects (< 10 files) | ~15% | Not enough complexity for graph |

### Parallel Execution
- Phase 3 (`dry_run`) → sequential (must validate before write)
- Phase 5 (`generate_class` × N) can be parallelized
- Phase 6 (`generate_content` for DevOps files) can be parallelized
- Phase 8 (`cb:status`) + Phase 9 (`WFK_PRD_001`) run sequentially

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| `dry_run` shows templates user doesn't want | Abort, adjust params, re-dry_run |
| User already knows exact stack | Skip WFK_GRN_002, go straight to WFK_GRN_001 |
| `ai_readiness_score >= 90` after Phase 8 | Skip Phase 9 (production gate), deliver immediately |
| Project is a script, not a service | Skip DDD layers, use simple scaffold |

### Cache Reuse
- `repo:init` only once — same `repo_id` for all validation
- If scaffold fails, reuse `slug`/`snake`/`pascal` from Phase 1
- Stack info from Phase 2 can be cached across multiple greenfield projects

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [brownfield-workflow.md](brownfield-workflow.md)*
