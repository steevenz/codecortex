---
name: codecortex-codebase
description: Use when you need to search code, analyze AST symbols, audit security/architecture, build/query code graphs, run tests, get codebase metrics, or perform any code intelligence task via CodeCortex
---

# codecortex:codebase — Code Intelligence

**8 actions**: `analyze | search | audit | graph | status | index | test | refactor`

**Tool**: `codecortex:codebase` | **Workflow Index**: `docs/workflows/workflow-index.md` §2.1

---

## Action: search — 3-Layer Unified Search (WFK_SCH_001)

See: `docs/workflows/search-discovery-workflow.md` | `docs/features/codeindex/tools.md`

```
action: search
args: {query, search_type:"text", symbol_type:"any", semantic?, graph_enrichment?, limit:50, file_pattern:"*"}
```

| Layer | Enable | Returns |
|-------|--------|---------|
| **FTS text** | default | `matches[].{symbol, file, line, score}` |
| **Semantic** | `semantic:true` | `semantic_hits[].{symbol, similarity}` |
| **Graph** | `graph_enrichment:true` | `relationships[].{from, to, relation}` |

**Strategy**: text → semantic → graph (escalate only if needed).
- `matches[].score >= 0.95` = exact match → stop
- Text zero results → re-run with `semantic:true`
- Need relationships → add `graph_enrichment:true`

**Token economy**: Start with `include_content:false`, `limit:10`. Expand if needed.

**Error codes**: `CA_010` (no query), `CA_011` (bad request).

---

## Action: analyze — AST Deep Analysis (WFK_ANA_001 Phase 4)

See: `docs/features/codeanalysis/concept.md` | `docs/features/codeindex/concept.md`

```
action: analyze
args: {target, mode:"auto", max_depth:3, focus?, follow_depth:1, include_docstring:true, page_size:100}
```

| Mode | Use |
|------|-----|
| `auto` | Balanced — symbols + structure |
| `detailed` | Full AST, comments, docstrings |
| `symbol_focus` | Deep dive on specific symbol (signature, calls, references) |
| `overview` | Fast for >1000 files |

Returns `symbols[]` with `{name, kind, file, line, signature, docstring, calls, referenced_by}`.

**Always check** `pagination.next_cursor` for large results.

**Error codes**: `CA_001` (missing target), `CA_002` (not found).

**Token economy**: ~60% savings vs raw file reading.

---

## Action: audit — Standards Compliance Audit (WFK_SEC_001, WFK_PRD_001)

See: `docs/features/codeanalysis/concept.md` | `docs/workflows/security-audit-workflow.md` | `docs/workflows/production-readiness-workflow.md`

```
action: audit
args: {target:".", scan_categories?, severity_threshold:"medium", entropy_threshold:4.5,
       max_file_size_kb:1024, use_ast:true, use_aiignore:true, since:?}
```

**Categories**: secrets, pii, misconfig, vulns, naming, type_hints, file_structure, class_docblock, modular_design, architecture, syntax, error_handling, di_compliance, docblock, logging, api_response, semver, pwa, cross_platform, test_debug, codification, coding_naming (24 total).

Returns `{compliance_score:0-100, findings[], recommendations[]}`.

**Gate**: `compliance_score < 50` = blocking. `50-79` = warnings. `>= 80` = pass.

**Error codes**: `CA_020` (no target), `CA_021` (not found).

---

## Action: graph — Code Graph Operations (WFK_ARC_001, WFK_BUG_001)

See: `docs/features/codegraph/concept.md` | `docs/features/codegraph/tools.md` | `docs/workflows/architecture-audit-workflow.md`

```
action: graph
args: {sub_action, ...}
```

### sub_action: build
```
args: {detect_modular:true, build_dependency_graph:true, scan_hmvc_p:true, max_depth:5, use_cache:true}
```
Run before queries on new repos. `graph_stats.density < 0.01` = good modularity.

### sub_action: query (WFK_SCH_001)
```
args: {target, query_type, max_depth:3, direction:"both", limit:20}
```

| query_type | Use | Returns |
|------------|-----|---------|
| `callers` | "Who calls X?" | `callers[].{name, file, line}` |
| `callees` | "What does X call?" | `callees[].{name, file, line}` |
| `trace_flow` | "What happens when?" | Execution path (BFS) |
| `trace_path` | "Is A connected to B?" | Path between symbols |
| `ancestors` | "Class hierarchy up" | Parent chain |
| `descendants` | "Class hierarchy down" | Children chain |
| `dead_code` | "What's unused?" | Degree-zero symbols |

**Error codes**: `GRPH_002` (symbol not found), `GRPH_008` (invalid action).

### sub_action: audit (WFK_ARC_001)
```
args: {audit_types?, degree_threshold:10, include_summary:?, limit:50}
```

| Type | What | Reading |
|------|------|---------|
| `god_nodes` | High in-degree symbols | `in_degree > 30` = God Class |
| `dead_code` | No callers | Ready to delete |
| `complexity` | Cyclomatic complexity | `> 15` = refactor |
| `circular_deps` | Circular imports | Must break |
| `coupling` | Cross-module | `score > 0.7` = smell |
| `communities` | Leiden clusters | Actual module boundaries |

**Error codes**: `GRPH_009`.

### sub_action: relationships
```
args: {target_node, relation_type?, depth:1, include_community?, limit:100}
```
`min_confidence`: `EXTRACTED` (AST) > `INFERRED` (naming) > `AMBIGUOUS`.

**Error codes**: `GRPH_011`.

---

## Action: status — Codebase Snapshot (WFK_ANA_001 Phase 3)

```
action: status
args: {include_metrics:true, include_vcs:true, include_symbols:true, language:?}
```

Returns `{files, loc, symbols, graph_stats, vcs}`.

**Heuristics**: `graph_stats.density < 0.01` = modular. `comment_ratio < 0.1` = under-documented. `vcs.uncommitted_changes > 10` = unstable.

**Error codes**: `CA_030` (no path), `CA_031` (not found).

---

## Action: index — AST Index Management

```
action: index
args: {sub_action, files?}
```

| sub_action | Purpose |
|------------|---------|
| `build`/`rebuild` | Build/rebuild AST index |
| `remove` | Remove all index data |
| `status` | Index statistics (files/symbols) |

---

## Action: test — Test Runner (WFK_TST_001)

See: `docs/features/codetester/concept.md` | `docs/workflows/testing-qa-workflow.md`

```
action: test
args: {sub_action, target_path?, test_framework:"auto", test_filter?, categories?, coverage_format:"summary", max_duration:300}
```

| sub_action | Purpose |
|------------|---------|
| `discover` | Find test files + frameworks |
| `run` | Execute tests → `summary.{passed, failed, skipped, duration}` |
| `diagnose` | Detect flaky/slow tests + suggestions |
| `generate` | Generate missing tests from AST |

**28 framework adapters**: pytest, jest, vitest, mocha, go test, cargo test, junit, phpunit, rspec, etc.

---

## Action: refactor — Safe Semantic Refactoring (WFK_RFC_001)

**CRITICAL**: Always start with `sub_action: "impact"` (read-only).

See: `docs/workflows/safe-refactoring-workflow.md` | `docs/features/coderefactor/concept.md`

Protocol: `impact` → `preview (dry_run:true)` → `apply (dry_run:false)` after user confirms.

| sub_action | Purpose |
|------------|---------|
| `impact` | Blast radius: affected files, symbols, risk |
| `rename` | Rename symbol across all references |
| `move` | Move code element to new file |
| `extract` | Extract function from code block |
| `inline` | Inline function call |
| `signature` | Change function signature + update callers |

**Full workflow**: See `codecortex-refactor` skill.

---

## CLI Equivalents

All codebase actions have CLI via `codecortex cb <action> ...`. See `docs/guides/how-to-use-cli.md`.

```bash
codecortex cb search "query" --semantic --graph
codecortex cb analyze src/service.py --mode symbol_focus
codecortex cb audit . --scan-categories secrets,vulns
codecortex cg build /path/to/repo
codecortex cg query callers --target src/service.py::process_order
codecortex cg audit --god-nodes --dead-code
```

---

## Error Codes Reference

| Code | Meaning | Fix |
|------|---------|-----|
| CA_001 | Missing target param | Provide `target` |
| CA_002 | Target not found | Check path/symbol name |
| CA_010 | No search query | Provide `query` |
| CA_020 | No audit target | Provide `target: "."` |
| CA_030 | No status path | Provide path or repo_id |
| CA_500 | Internal error | Check logs |
| GRPH_002 | Symbol not in graph | Run `graph build` |
| GRPH_008 | Invalid action | Use valid sub_action |
| GRPH_009 | Audit failed | Check repo_id |
| REF_400 | Invalid refactor params | Check sub_action |
| REF_500 | Refactor execution error | Check conflicts |

---

## Feature Docs per Action

| Action | Feature Doc | AI-Impact |
|--------|-------------|-----------|
| search | `docs/features/codeindex/tools.md` | `docs/features/codeindex/ai-impact-token-efficiency.md` |
| analyze | `docs/features/codeanalysis/concept.md` | `docs/features/codeanalysis/ai-impact-token-efficiency.md` |
| audit | `docs/features/codeanalysis/concept.md` | `docs/features/codeanalysis/ai-impact-token-efficiency.md` |
| graph | `docs/features/codegraph/tools.md` | `docs/features/codegraph/ai-impact-token-efficiency.md` |
| test | `docs/features/codetester/concept.md` | `docs/features/codetester/ai-impact-token-efficiency.md` |
| refactor | `docs/features/coderefactor/concept.md` | `docs/features/coderefactor/ai-impact-token-efficiency.md` |
