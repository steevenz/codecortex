# CodeGraph Documentation Gap Analysis

**Date:** 2026-05-29
**Domain:** CodeGraph
**Reference:** `docs/features/codeanalysis` (template)
**Analysis Type:** Documentation Structure & Completeness Audit

---

## Executive Summary

**Overall Documentation Quality:** 6.5/10 ⚠️

CodeGraph documentation exists but lacks the structural rigor and completeness of the CodeAnalysis reference template. Key gaps: missing metadata headers, incomplete architecture sections, no error codes, sparse examples, and inconsistent sub-feature documentation.

---

## File-by-File Analysis

### 1. `concept.md` — Domain Overview

**Status:** ⚠️ Incomplete (40% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Metadata header (Domain, Package, Version, AI Impact, Production Readiness) | ✅ Partial | Wrong package path | Package path shows `src/domain/codegraph/` instead of `src/modules/codegraph/` |
| Business Context | ✅ | Good | — |
| Why This Exists | ✅ | Good | — |
| Theoretical Foundation | ✅ | Good | — |
| Architecture | ❌ | Missing | Should show `src/modules/codegraph/` structure like codeanalysis |
| Domain Boundary | ❌ | Missing | Should list owned tools, dependencies, consumers |
| CLI Architecture Note | ❌ | Missing | Should explain CLI domain naming (`codegraph` vs `cg`) |
| ~/.aicoders/ Compliance | ❌ | Missing | Should list compliance with API Standard, DDD, DI, etc. |
| Error Codes | ❌ | Missing | Should list error code prefixes (GRPH_0xx) |
| Audit Categories | ❌ | Missing | Not applicable (but could list refactor types) |

**Required Updates:**
- Fix package path to `src/modules/codegraph/`
- Add metadata: Version (2.0.0), AI Coder Impact (9/10), Production Readiness (100%)
- Add Architecture section with folder structure
- Add Domain Boundary section
- Add CLI Architecture Note
- Add ~/.aicoders/ Compliance section
- Add Error Codes table

---

### 2. `flow.md` — Execution Flow

**Status:** ✅ Good (80% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Pipeline diagram | ✅ | Good | — |
| Detailed sequence | ✅ | Good | — |
| Key entry points table | ✅ | Good | — |
| Error codes | ❌ | Missing | Should list error codes for each stage |
| Performance metrics | ❌ | Missing | Should include timing, scalability notes |

**Required Updates:**
- Add Error Codes section
- Add Performance section (timing, scalability)

---

### 3. `output.md` — Response Data

**Status:** ✅ Good (75% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Response shapes (JSON examples) | ✅ | Good | — |
| Graph backend storage | ✅ | Good | — |
| Error codes | ❌ | Missing | Should list error codes for response failures |

**Required Updates:**
- Add Error Codes section

---

### 4. `llm-impact.md` — LLM Impact

**Status:** ✅ Good (85% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Before/After comparison | ✅ | Good | — |
| Concrete improvements table | ✅ | Good | — |
| Error codes | ❌ | Missing | Not critical but could add |

**Required Updates:**
- None (optional: add error codes)

---

### 5. `ai-impact-token-efficiency.md` — Token Efficiency

**Status:** ✅ Excellent (95% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Overall metrics | ✅ | Good | — |
| Tool-by-tool analysis | ✅ | Excellent | — |
| Error codes | ❌ | Missing | Not critical |

**Required Updates:**
- None (optional: add error codes)

---

### 6. `tools.md` — Tool Reference

**Status:** ✅ Updated (90% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Tool reference (6 tools) | ✅ | Good | Recently updated with new params |
| Error codes | ❌ | Missing | Should list error code prefixes per tool |

**Required Updates:**
- Add Error Codes table

---

## Sub-Features Analysis

### 7. `sub-features/knowledge-graph/concept.md`

**Status:** ✅ Good (80% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Concept | ✅ | Good | — |
| Architecture diagram | ✅ | Good | — |
| Key operations table | ✅ | Good | — |
| Node types table | ✅ | Good | — |
| Relationship types table | ✅ | Good | — |
| Error codes | ❌ | Missing | Should list KG_0xx errors |
| Performance | ❌ | Missing | Should note O(1) complexity |

**Required Updates:**
- Add Error Codes section
- Add Performance section

---

### 8. `sub-features/execution-flow/concept.md`

**Status:** ✅ Good (75% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Concept | ✅ | Good | — |
| How It Works (diagram) | ✅ | Good | — |
| BFS Traversal | ✅ | Good | — |
| Depth Configuration table | ✅ | Good | — |
| Error codes | ❌ | Missing | Should list EF_0xx errors |
| Performance | ❌ | Missing | Should note O(V+E) complexity |

**Required Updates:**
- Add Error Codes section
- Add Performance section

---

### 9. `sub-features/architecture-audit/concept.md`

**Status:** ✅ Good (80% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Concept | ✅ | Good | — |
| Audit Types (god nodes, dead code, security, complexity) | ✅ | Good | — |
| Combined output example | ✅ | Good | — |
| Error codes | ❌ | Missing | Should list AA_0xx errors |
| Performance | ❌ | Missing | Should note centrality calc cost |

**Required Updates:**
- Add Error Codes section
- Add Performance section

---

### 10. `sub-features/graph-backends/concept.md`

**Status:** ✅ Good (85% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Concept | ✅ | Good | — |
| Supported backends table | ✅ | Good | — |
| Backend selection | ✅ | Good | — |
| Graph schema (Cypher) | ✅ | Good | — |
| Docker setup | ✅ | Good | — |
| Error codes | ❌ | Missing | Should list GB_0xx errors |

**Required Updates:**
- Add Error Codes section

---

### 11. `sub-features/route-extraction/concept.md`

**Status:** ✅ Good (80% of reference)

| Section | Present | Quality | Gap |
|---------|---------|--------|-----|
| Concept | ✅ | Good | — |
| Supported frameworks table | ✅ | Good | — |
| Output example | ✅ | Good | — |
| Impact | ✅ | Good | — |
| Error codes | ❌ | Missing | Should list RE_0xx errors |
| Performance | ❌ | Missing | Should note regex cost |

**Required Updates:**
- Add Error Codes section
- Add Performance section

---

### 12. `sub-features/community-detection/concept.md`

**Status:** ⚠️ Not reviewed (file exists but not read)

**Gap:** Should verify structure matches reference template.

---

### 13. `sub-features/entry-point-scoring/concept.md`

**Status:** ⚠️ Not reviewed (file exists but not read)

**Gap:** Should verify structure matches reference template.

---

### 14. `sub-features/heritage-extraction/concept.md`

**Status:** ⚠️ Not reviewed (file exists but not read)

**Gap:** Should verify structure matches reference template.

---

### 15. `sub-features/orm-dataflow/concept.md`

**Status:** ⚠️ Not reviewed (file exists but not read)

**Gap:** Should verify structure matches reference template.

---

## Examples Directory

**Status:** ❌ Sparse (1 file)

| File | Purpose | Gap |
|------|---------|-----|
| `graph-query-callers.json` | Example response for graph_query | Only 1 example; should add examples for all 6 tools |

**Required Updates:**
- Add example responses for:
  - `graph_search` (symbol, relation, semantic, modular)
  - `graph_build` (full_build, incremental_cache_hit)
  - `graph_audit` (with fix_suggestions)
  - `graph_relationship` (with community detection)
  - `graph_refactor` (impact, preview, apply, undo_list)

---

## Cross-Cutting Gaps

### 1. Error Codes (Critical)

**Status:** ❌ Missing across all files

**Reference:** CodeAnalysis concept.md has:
```
| Prefix | Tool |
|--------|------|
| CA_0xx | code_analyze |
| CA_01x | code_search |
```

**CodeGraph Should Have:**
```
| Prefix | Tool |
|--------|------|
| GRPH_001 | graph_build (repo not found) |
| GRPH_002 | graph_query (node not found) |
| GRPH_003 | graph_search (invalid action) |
| GRPH_004 | graph_audit (repo not found) |
| GRPH_005 | graph_relationship (node not found) |
| GRPH_006 | graph_refactor (invalid refactor_type) |
| GRPH_007 | graph_refactor (target not found) |
| GRPH_008 | graph_refactor (undo_id not found) |
| GRPH_009 | graph_refactor (apply failed) |
| GRPH_010 | graph_build (cache error) |
| GRPH_011 | graph_query (invalid query_type) |
| GRPH_012 | graph_refactor (validation failed) |
```

---

### 2. Performance Sections (High)

**Status:** ❌ Missing across most files

**Reference:** CodeAnalysis sub-features include performance notes (e.g., AST caching, parallel processing).

**CodeGraph Should Add:**
- Time complexity for each algorithm (BFS O(V+E), Leiden O(n log n), etc.)
- Scalability notes (graph size limits, memory usage)
- Caching strategy (AST cache, graph cache, incremental build)

---

### 3. Architecture Section (Critical)

**Status:** ❌ Missing from concept.md

**Reference:** CodeAnalysis concept.md has:
```
src/modules/codeanalysis/
├── api/              → tools.py: 4 MCP tools, cli.py: CLI commands
├── services/         → Service classes: DI via constructor
├── core/            → dtos.py: typed DTOs
└── analyzers/       → Domain analyzers
```

**CodeGraph Should Have:**
```
src/modules/codegraph/
├── api/              → tools.py: 6 MCP tools, cli.py: CLI commands
├── services/         → Service classes: DI via constructor
│   ├── CODDY.py      → Graph build (CODDY)
│   ├── search.py     → Unified search (CODDYGraphSearch)
│   ├── trace.py      → Execution flow tracing (CODDYGraphTrace)
│   ├── relationship.py → Relationship exploration (CODDYGraphRelationship)
│   ├── audit.py      → Architectural audit (CODDYGraphAudit)
│   ├── refactor.py   → Refactoring (CODDYGraphRefactor)
│   └── graph.py      → Graph operations (CodeGraphService)
├── core/            → dtos.py: typed DTOs
└── mixins/           → Reusable graph operations
```

---

### 4. Domain Boundary Section (High)

**Status:** ❌ Missing from concept.md

**Reference:** CodeAnalysis concept.md has:
```
- Owns: code_analyze, code_search, code_audit, code_status
- Does NOT own: code_refactor (handled by coderefactor domain)
- Depends on: DatabaseManager, FilesystemService
- Consumed by: MCP layer via api/tools.py
```

**CodeGraph Should Have:**
```
- Owns: graph_build, graph_search, graph_query, graph_audit, graph_relationship, graph_refactor
- Does NOT own: code_index (symbol extraction), code_refactor (file-level refactoring)
- Depends on: DatabaseManager, GraphManager (Kuzu/Neo4j/FalkorDB), FilesystemService
- Consumed by: MCP layer via api/tools.py, CLI via cli.py
```

---

### 5. CLI Architecture Note (Medium)

**Status:** ❌ Missing from concept.md

**Reference:** CodeAnalysis concept.md has:
```
The CLI domain is named `codebase` (not `codeanalysis`) as an intentional UX decision.
```

**CodeGraph Should Have:**
```
The CLI domain is named `codegraph` (alias `cg`) to align with the MCP tool naming.
```

---

### 6. ~/.aicoders/ Compliance Section (High)

**Status:** ❌ Missing from concept.md

**Reference:** CodeAnalysis concept.md has:
```
- API Standard: api_response() for all tool responses
- DDD: api/ + services/ + core/ separation
- DI: Constructor injection for all services
- Boundary: Data crosses layers only via DTOs
- Error Handling: Guard clauses, structured errors
- Logging: CodeCortex.CodeAnalysis.* logger namespace
- Documentation: All docs in docs/features/codeanalysis/
```

**CodeGraph Should Have:**
```
- API Standard: api_response() for all tool responses
- DDD: api/ + services/ + core/ separation
- DI: Constructor injection for all services
- Boundary: Data crosses layers only via DTOs
- Error Handling: Guard clauses, structured errors
- Logging: CodeCortex.CodeGraph.* logger namespace
- Documentation: All docs in docs/features/codegraph/
```

---

## Priority Recommendations

### P0 (Critical — Must Fix)

1. **Add Error Codes table to all files** — Critical for troubleshooting and integration
2. **Complete concept.md metadata header** — Fix package path, add Version, AI Impact, Production Readiness
3. **Add Architecture section to concept.md** — Show actual folder structure
4. **Add Domain Boundary section to concept.md** — Define ownership, dependencies, consumers

### P1 (High — Should Fix)

5. **Add Performance sections to all sub-features** — Time complexity, scalability, caching
6. **Add CLI Architecture Note to concept.md** — Explain `codegraph` vs `cg` naming
7. **Add ~/.aicoders/ Compliance section to concept.md** — List compliance with standards
8. **Populate examples directory** — Add example responses for all 6 tools

### P2 (Medium — Nice to Have)

9. **Standardize sub-feature concept.md structure** — Ensure all 9 sub-features have consistent sections
10. **Add version metadata to sub-features** — Include Version, AI Impact, Production Readiness
11. **Add error codes to sub-features** — Specific error prefixes per sub-feature

---

## Action Plan

1. Update `concept.md` with missing sections (Architecture, Domain Boundary, CLI Note, Compliance, Error Codes)
2. Add Error Codes table to `tools.md`, `flow.md`, `output.md`
3. Add Error Codes and Performance sections to all 9 sub-features
4. Create 5 additional example JSON files in `examples/`
5. Standardize sub-feature structure to match codeanalysis template

---

## Conclusion

CodeGraph documentation is **functional but incomplete**. It covers the basics (concepts, flow, tools) but lacks the structural rigor of the CodeAnalysis reference template. The most critical gaps are:
- Missing error codes (troubleshooting)
- Incomplete concept.md (architecture, domain boundary, compliance)
- Sparse examples (only 1 of 6 tools documented)
- Missing performance sections (scalability, complexity)

**Estimated Effort:** 4-6 hours to bring CodeGraph documentation to 100% parity with CodeAnalysis standards.
