# CodeCortex Improvements: Implementation Plan

**Source:** GitNexus deep analysis  
**Total Features:** 10  
**Order:** Low Effort/High Impact → High Effort/High Impact (cumulative)

---

## Phase 1: Low Effort, High Impact (Priority 1-6)

### Step 1: Glob-based File Walker (~2h)
**Files:** `docs/drafts/concepts/improvements/01-glob-file-walker.md`
- New: `src/domain/filesystem/infrastructure/glob_walker.py`
- Edit: `src/domain/coderepository/application/service.py`
- Edit: Config `max_file_size_mb` default 1MB
- Test: `tests/test_glob_walker.py`

### Step 2: Concurrent File Stat (~2h)
**Files:** `docs/drafts/concepts/improvements/05-concurrent-file-stat.md`
- New: `src/domain/filesystem/infrastructure/batch_reader.py`
- Edit: `service.py` — integrate batch stat into discovery
- Test: `tests/test_batch_reader.py`

### Step 3: AST Cache (~2h)
**Files:** `docs/drafts/concepts/improvements/06-ast-cache.md`
- New: `src/domain/codeindex/infrastructure/ast_cache.py`
- Edit: `src/core/tree_sitter_manager.py`
- Edit: `src/domain/codeindex/application/service.py`
- Test: `tests/test_ast_cache.py`

### Step 4: Leiden Community Detection (~3h)
**Files:** `docs/drafts/concepts/improvements/02-leiden-communities.md`
- New: `src/domain/codegraph/application/community_leiden.py`
- Edit: `src/core/graph_manager.py` — wire Leiden
- Deps: `leidenalg` (optional, Louvain fallback)
- Test: `tests/test_community_leiden.py`

### Step 5: Global Registry & Staleness (~3h)
**Files:** `docs/drafts/concepts/improvements/04-global-registry-staleness.md`
- New: `src/domain/coderepository/application/registry.py`
- Edit: `src/domain/coderepository/api/tools.py` — add MCP tools
- Edit: `service.py` — update registry on sync
- DB: migration `repositories.last_commit`
- Test: `tests/test_registry.py`

### Step 6: Entry Point Scoring (~4h)
**Files:** `docs/drafts/concepts/improvements/03-entry-point-scoring.md`
- New: `src/domain/codegraph/application/entry_point_scorer.py`
- Edit: CodeGraph analysis report
- DB: migration `symbols.is_entry_point`
- Test: `tests/test_entry_point_scorer.py`

---

## Phase 2: Medium Effort, High Impact (Priority 7-8)

### Step 7: In-Memory Knowledge Graph (~6h)
**Files:** `docs/drafts/concepts/improvements/07-in-memory-graph.md`
- New: `src/domain/codegraph/core/knowledge_graph.py`
- Edit: `src/domain/codegraph/application/service.py`
- Port analysis queries to use graph API
- Test: `tests/test_knowledge_graph.py`

### Step 8: Process Detection (~8h)
**Files:** `docs/drafts/concepts/improvements/08-process-detection.md`
- New: `src/domain/codegraph/application/process_detector.py`
- DB: new `processes` + `process_steps` tables
- Edit: analysis report — include top processes
- MCP Tool: `trace_process`
- Test: `tests/test_process_detector.py`

---

## Phase 3: High Effort, High Impact (Priority 9-10)

### Step 9: Heritage Extraction (~6h)
**Files:** `docs/drafts/concepts/improvements/10-heritage-extraction.md`
- New: `src/domain/codegraph/application/heritage_extractor.py`
- New: per-language heritage parsers (Python, TS, Java)
- Edit: `codegraph_service.py` — add heritage phase
- MCP Tool: `get_class_hierarchy`
- Test: `tests/test_heritage_extractor.py`

### Step 10: Import Resolution Pipeline (~10h)
**Files:** `docs/drafts/concepts/improvements/09-import-resolution-pipeline.md`
- New: `src/domain/codeindex/infrastructure/import_resolvers/`
  - `base.py`, `python.py`, `typescript.py`, `go.py`, `suffix_index.py`
- Edit: `index_service.py` — add import resolution phase
- DB: new `import_edges` table
- MCP Tool: `resolve_imports`
- Test: `tests/test_import_resolvers.py`

---

## Total Effort
| Phase | Features | Hours |
|-------|----------|-------|
| 1 | 6 | ~16h |
| 2 | 2 | ~14h |
| 3 | 2 | ~16h |
| **Total** | **10** | **~46h** |

## Dependencies
- Step 8 (Process Detection) depends on Step 6 (Entry Points) and Step 7 (Knowledge Graph)
- Step 7 depends on nothing — can build in parallel
- All Phase 1 items are independent

## Implementation Order
```
Phase 1: 1 → 2 → 3 → 4 → 5 → 6
Phase 2: 7 → 8
Phase 3: 10 → 9  (heritage first, import pipeline last)
```

Start implementation after approval.
