---
name: codecortex
description: Use when needing code intelligence, codebase analysis, graph queries, refactoring, architecture audit, cross-IDE memory, project scaffolding, or any code understanding task via MCP CodeCortex server. Trigger: /codecortex
---

# CodeCortex — Code Intelligence at LLM Speed

**6 unified MCP tools · 39+ actions · 35 languages · 18 frameworks · Graph-based understanding**

**Doc**: `docs/` | **Workflows**: `docs/workflows/workflow-index.md` | **Features**: `docs/features/index.md`

---

## Architecture

```
CortexOrchestrator (DI) → 6 domains:
  Repository → CodeIndex → CodeGraph → CodeAnalysis → CodeRefactor → CodeTester
  + Filesystem + KnowledgeGraph + IDEGraph + Scaffolder
```

**DDD + Hexagonal**: `src/main.py` → `ActionRouter` → domain services. No global state.

---

## 6 Unified MCP Tools

All return `{success, status_code, message, data, meta}`.

| Tool | Actions | Module | Docs |
|------|---------|--------|------|
| `codecortex:repository` | init, inspect, analyze, sync, audit, staleness, list, compact, cleanup, dump, restore, git, svn | CodeRepository | `docs/features/coderepository/concept.md` |
| `codecortex:filesystem` | read, write, delete, copy, move, mkdir, list, search, watch, usage, audit | Filesystem | `docs/features/filesystem/concept.md` |
| `codecortex:codebase` | analyze, search, audit, graph, status, index, test, refactor | CodeAnalysis+CodeGraph+CodeIndex+CodeTester+CodeRefactor | `docs/features/codeanalysis/concept.md` |
| `codecortex:scaffolder` | list_stacks, get_stack, validate_name, list_licenses, generate_content, generate_class, create_project | Scaffolder | `docs/features/scaffolder/concept.md` |
| `codecortex:knowledge` | extract, query, status, relationships, validate | KnowledgeGraph | `docs/features/knowledgegraph/concept.md` |
| `codecortex:idegraph` | search, get, list, ingest, refresh, health, stats, compact, workspace, harvest, export, timeline | IDEGraph | `docs/features/idegraph/concept.md` |

---

## Token Economy (18x Compression)

| Pattern | Savings | How |
|---------|---------|-----|
| Symbol-level extraction | ~60% | `{name, file, line, signature}` vs raw source |
| 3-layer search | ~40% | FTS + semantic + graph in one call |
| Call graph traversal | ~70% | "Who calls X" in JSON, not reading 10 files |
| Architecture audit | ~50% | `god_nodes` as lists, not folder walks |
| Incremental sync | ~90% re-index | git-diff based, only changed files |
| Context deduplication | ~15% | SHA-256 prevents re-injecting same symbols |

**Math**: 500-file repo: ~15K tokens raw → ~800 tokens structured JSON. **18x compression**.

---

## Workflow Index (16+ Codified Workflows)

All workflows at `docs/workflows/`. Decision tree: `workflow-index.md §2.1 — Master Intent Router`.

| Code | Workflow | Trigger | Doc |
|------|----------|---------|-----|
| WFK_ANA_001 | Deep Code Analysis | "Analyze this codebase" | `deep-analysis-workflow.md` |
| WFK_BUG_001 | Bug Hunting | "Find bugs / Debug" | `bug-hunting-workflow.md` |
| WFK_PRD_001 | Production Readiness | "Is this production ready?" | `production-readiness-workflow.md` |
| WFK_TST_001 | Testing & QA | "Run tests / Coverage" | `testing-qa-workflow.md` |
| WFK_SEC_001 | Security Audit | "Security audit" | `security-audit-workflow.md` |
| WFK_ARC_001 | Architecture Audit | "Architecture review" | `architecture-audit-workflow.md` |
| WFK_RFC_001 | Safe Refactoring | "Refactor / Rename" | `safe-refactoring-workflow.md` |
| WFK_SCH_001 | Search & Discovery | "Find symbol / Search code" | `search-discovery-workflow.md` |
| WFK_GRN_001-003 | Greenfield Project | "Create new project" | `greenfield-workflow.md` |
| WFK_LGY_001-005 | Brownfield Modernization | "Understand legacy" | `brownfield-workflow.md` |
| WFK_IDE_001 | IDE Context | "Ingest to memory" | `ide-context-workflow.md` |
| WFK_MRP_001 | Multi-Repo | "Compare repos" | `multi-repo-workflow.md` |
| WFK_MNR_001 | Mono-Repo | "Analyze mono-repo" | `mono-repo-workflow.md` |
| WFK_CCT_001 | Deep Reasoning | "Architecture decision" | `cct-reasoning-workflow.md` |

**Routing**: Match user intent → find trigger phrase in workflow-index.md → follow pipeline.

---

## Core Workflow Patterns

### Analyze → Graph → Act (WFK_ANA_001 → WFK_SCH_001 → WFK_RFC_001)
```
1. repo inspect <path>             → health check + repo_id + ai_readiness_score
2. repo init <path> + analyze       → full index if ai_readiness_score < 50
3. cb status args={include_metrics:true} → snapshot: files, LOC, symbols, graph_stats
4. cb analyze args={target, mode}   → AST symbols + relationships
5. cb graph args={sub_action:"build"} → knowledge graph
6. cb search args={query, semantic?, graph_enrichment?} → 3-layer search
7. cb graph args={sub_action:"query", query_type:"callers"} → blast radius
8. cb refactor args={sub_action:"impact"} → read-only before any change
```

### Bug Hunting (WFK_BUG_001)
```
1. cb search args={query:"<error>", semantic:true}  → locate symptom
2. cb graph query callers + trace_flow                → execution path
3. cb audit scan_categories:["secrets","vulns"]       → security context
4. cb test diagnose                                    → flaky/slow tests
```

### Security Audit (WFK_SEC_001)
```
1. cb audit scan_categories:["secrets","pii","misconfig","vulns"]
2. repo audit secrets:true, include_git_history:true
3. fs audit target:"."
4. cb graph audit audit_types:["security"]
```

---

## Error Handling

| Signal | Means | Fix |
|--------|-------|-----|
| `success: false` + `error_code: "CA_001"` | Missing target parameter | Provide `target` |
| `error_code: "GRPH_002"` | Symbol not found in graph | Run `graph build` first |
| `error_code: "REP_404"` | Repo not indexed | Run `repo init` |
| `error_code: "REP_409"` | Already exists | Use existing `repo_id` |
| `error_code: "FS_001"` | No path provided | Provide absolute path |
| `compliance_score < 50` | Critical issues | Address all critical findings |
| `validation_result.passed: false` | Refactor conflict | Do NOT apply |
| `blast_radius.risk: "high"` | >10 files affected | Stop, ask user |
| `cached: true` | Data from cache | Call with `force: true` to refresh |

All responses include `request_id` for traceability. Service errors include error_code from `docs/features/codeanalysis/concept.md`.

---

## Environment & Config

From `pyproject.toml`, `docker-compose.yml`, `k8s.yaml`:

| Aspect | Default | Override |
|--------|---------|----------|
| Transport | stdio | `CODECORTEX_TRANSPORT=http` → SSE/HTTP at `127.0.0.1:8001` |
| DB path | `./database/codecortex.db` | Set `db_path` in orchestrator |
| Graph backend | SQLite | KuzuDB / Neo4j / FalkorDB via `docker-compose up -d` |
| Webhook | `/webhook/git-event` | Set `CODECORTEX_WEBHOOK_SECRET` |
| Embeddings | all-MiniLM-L6-v2 | Set `embedding_model` in analyze args |
| Max repos | 50 | Hard limit |

---

## Supported Languages & Frameworks

**See**: `docs/features/support-matrix.md`

**35 languages**: Python, TS, JS, TSX, Go, Rust, Java, Kotlin, PHP, Ruby, Swift, Dart/Flutter, C, C++, C#, Elixir, Haskell, Perl, Lua, Zig, Bash, SQL (+ more)

**18 frameworks**: Next.js, React, Vue, Angular, NestJS, SvelteKit, SolidJS, FastAPI, Django, Flask, Express, Laravel, Rails, Symfony, ASP.NET Core, Tauri, Astro, Flutter

---

## Tool Discovery Pattern

When unsure:
1. `repo inspect` → `ai_readiness_score` + `repo_id`
2. `cb status` → files, languages, graph density
3. `cb graph build` → ensure graph ready
4. `cb search` → locate target
5. Route to action based on findings

**Always pass `repo_id`** between calls. Get it from `repo init` or `repo inspect`.

---

## Common Reference

| Intent | Tool | Action | Key Args | Workflow |
|--------|------|--------|----------|----------|
| New repo setup | repository | init | repo_path, run_audit:true | WFK_GRN_001 |
| Fast health check | repository | inspect | repo_path, include_git_diagnostics:true | WFK_ANA_001 |
| Full analysis | repository | analyze | repo_path, build_graph:true | WFK_ANA_001 |
| Deep symbol dive | codebase | analyze | target, mode:"symbol_focus" | WFK_ANA_001 |
| Text search | codebase | search | query, search_type:"text" | WFK_SCH_001 |
| Semantic search | codebase | search | query, semantic:true | WFK_SCH_001 |
| Graph-enriched search | codebase | search | query, graph_enrichment:true | WFK_SCH_001 |
| Build graph | codebase | graph | sub_action:"build" | WFK_ARC_001 |
| Query callers | codebase | graph | sub_action:"query", query_type:"callers" | WFK_BUG_001 |
| Dead code | codebase | graph | sub_action:"audit", audit_types:["dead_code"] | WFK_ARC_001 |
| Architecture audit | codebase | graph | sub_action:"audit" | WFK_ARC_001 |
| Security scan | codebase | audit | scan_categories:["secrets","vulns"] | WFK_SEC_001 |
| Code hygiene | codebase | audit | scan_categories:["naming","type_hints"] | WFK_PRD_001 |
| Impact analysis | codebase | refactor | sub_action:"impact" | WFK_RFC_001 |
| Rename symbol | codebase | refactor | sub_action:"rename", dry_run:true | WFK_RFC_001 |
| Run tests | codebase | test | sub_action:"run" | WFK_TST_001 |
| Generate tests | codebase | test | sub_action:"generate" | WFK_TST_001 |
| Scaffold project | scaffolder | create_project | name, stack, dry_run:true | WFK_GRN_001 |
| Extract docs | knowledge | extract | repo_path | WFK_LGY_001 |
| Query knowledge | knowledge | query | task / regex / fts_query | WFK_LGY_001 |
| Search IDE memories | idegraph | search | query | WFK_IDE_001 |
| Ingest IDE memories | idegraph | ingest | (none) | WFK_IDE_001 |
| Incremental sync | repository | sync | repo_path | WFK_SYN_001 |
| Multi-repo setup | repository | init | (per repo path) | WFK_MRP_001 |

---

## Response Shape Reference

All tools: `{success, status_code, message, data, meta{timestamp, request_id, duration_ms, error_code?}}`

Feature docs detail each action's response fields: `docs/features/codegraph/output.md`, `docs/features/codeindex/output.md`, etc.

**Cross-ref**: `docs/guides/mcp-tools-insight.md` — full field-by-field AI insight per tool.
**CLI**: `docs/guides/how-to-use-cli.md` — all CLI equivalents with `codecortex` binary.
