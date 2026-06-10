# CodeIndex: Execution Flow

> **Pipeline:** Repo Identified -> Files Pre-scanned -> Parsed -> Enriched -> Persisted -> Edges Resolved -> Graph Synced

## Pipeline Stages

```
+------------------+    +------------------+    +-------------------+    +-------------------+
|  1. File Fetch   |--->|  2. Pre-Scan     |--->|  3. AST Parse     |--->|  4. Framework     |
|  (SQLite files   |    |  Python imports  |    |  Tree-Sitter /    |    |  Enrichment       |
|   table)         |    |  for call graph  |    |  ast builtin      |    |  (detector.py)    |
+------------------+    +------------------+    +-------------------+    +-------------------+
       |                                                                          |
       |   +------------------+    +------------------+    +------------------+   |
       |   |  7. Edge         |<---|  6. Scope        |<---|  5. SQLite       |<--+
       |   |  Resolution      |    |  Resolution      |    |  Persistence     |
       |   |  (4 relation     |    |  (multi-pass     |    |  (symbols,       |
       |   |   types)         |    |   cross-file)    |    |   metadata)      |
       |   +------------------+    +------------------+    +------------------+
       |
       v
+------------------+
|  8. Graph Sync   |  (optional -- if codegraph_service injected)
|  (Kuzu/Neo4j/    |
|   FalkorDB)      |
+------------------+
```

## Detailed Sequence

### Phase 1: File Discovery
1. Files are fetched from SQLite `files` + `directories` tables (populated by CodeRepository sync)
2. Only files with `classification = 'code'` are processed
3. Filters: skips files >5MB (`MAX_FILE_SIZE_BYTES`), non-existent files, non-code classifications
4. Python files (`.py`, `.ipynb`) get pre-scanned for import maps before main parsing

### Phase 2: Pre-Scan Python Imports
1. `pre_scan_python()` scans all Python files using Tree-Sitter queries
2. Extracts all class and function definitions -> maps name to file path
3. This imports_map feeds into graph backend sync for cross-file call resolution
4. Runs before main parse so graph sync can batch in one pass

### Phase 3: AST Parsing
1. Dispatch decision: **WorkerPool** (parallel `ThreadPoolExecutor`) if >=15 files or >=512KB total, else **sequential async** with semaphore(10)
2. Each file goes through:
   - Extension -> language name lookup (`ts_parsers` dict -- includes `.css`, `.scss`, `.sass`, `.less`)
   - Content read -> AST cache check (SHA-256 keyed LRU)
   - Cache hit -> skip parse; Cache miss -> `TreeSitterParser.parse()`
   - Python fallback: if Tree-Sitter ImportError, use `ast.parse()` builtin
   - Non-TS languages (Vue, Cobol) -> dedicated regex-based parsers
   - Generic TS languages (Julia, Lua, ObjC, PowerShell, Verilog, Zig) -> `generic_ts.parse_generic()`
3. Timeout guard: 15 seconds per file (`PARSE_TIMEOUT_SECONDS`)
4. All 25 tree-sitter parsers (19 dedicated + 6 generic) output standard format: `functions[]`, `classes[]`, `variables[]`, `imports[]`, `function_calls[]`

### Phase 4: Framework Enrichment
1. `_enrich_frameworks()` calls `RepositoryFrameworkDetector.enrich_file()`
2. Detects: Next.js, React, Flutter, Laravel, Django, FastAPI, Express, Angular, Rails, Symfony, ASP.NET, NestJS, Vue
3. Framework tags are merged into parsed symbol data before persistence
4. Detector cache (`_repo_detector_cache`) bounded to 20 entries to prevent memory leak

### Phase 5: SQLite Persistence
1. `_write_parsed_to_sqlite()` -> `parsed_data_to_raw_symbols()` (converter) -> `_persist_raw_symbols()`
2. Two-pass insert: first pass inserts all symbols, second pass resolves `parent_id` UUIDs using `code_ref` as temporary key
3. Each file gets a sentinel `__file__` symbol storing the file-level variables/imports/function_calls in metadata
4. Metadata JSON preserves: variables, function_calls, imports, language, framework tags

### Phase 6: Scope Resolution
1. `_parsed_to_symbols()` converts flat tree-sitter output (classes/functions keys) into hierarchical symbol list
2. `build_workspace_index()` builds `ScopeTree` per file (module -> class -> function hierarchy)
3. `resolve_workspace_references()` runs multi-pass reference resolution:
   - Pass 1: Local scope (same file)
   - Pass 2: Import resolution (cross-file via imports_map)
   - Pass 3: Global index (name match across all files)
4. Stats logged: total_references, resolved, unresolved, resolution_rate
5. Unresolved references stored as `insights` with category `lint`

### Phase 7: Edge Resolution (4 Relation Types)
1. `_resolve_edges_sqlite()` builds 4 edge types from symbol metadata:

   **CALLS** -- From `function_calls` metadata on each function/method symbol:
   - Reads `function_calls` list from metadata JSON
   - Looks up callee by name in the global symbol table
   - Creates edges with `relation_type='CALLS'`, skipping self-calls
   - Edge IDs: `{source_id}--{target_id}--CALLS` with `ON CONFLICT DO UPDATE weight += 1`

   **INHERITS** -- From `parent_id` chain (method -> parent class):
   - Reads each symbol's `parent_id` field
   - If non-null, creates `INHERITS` edge from child to parent
   - Edge IDs: `{child_id}--{parent_id}--INHERITS`

   **CLASS_INHERITS** -- From class signature bases:
   - For each class symbol, parses the `signature` column for base class names
   - Looks up base class by name in the symbol table
   - Creates edges with `relation_type='CLASS_INHERITS'`
   - Example: `class A extends B` -> `A --CLASS_INHERITS--> B`

   **IMPORTS** -- From `__file__` sentinel symbol metadata JSON:
   - Reads `imports` list from the file's `__file__` symbol metadata
   - Looks up each imported symbol in the global symbol table
   - Creates edges with `relation_type='IMPORTS'`

2. All edges use deterministic ID format with `ON CONFLICT` upsert for deduplication

### Phase 8: Graph Backend Sync (Optional)
1. If `codegraph_service` is injected, `write_repository_graph()` syncs parsed files + imports_map to Kuzu/Neo4j/FalkorDB
2. Single pass to avoid duplicate edges

## Key Entry Points

| Trigger | Method | Description |
|---------|--------|-------------|
| `code_index(action="index")` MCP tool | `CodeIndexService.index_repository()` | Full re-index |
| `code_index(action="incremental")` MCP tool | `CodeRepositoryService.sync_repository_incremental()` + `index_files()` | Git diff-based partial re-index |
| `code_index(action="files")` MCP tool | `CodeIndexService.index_files()` | Specific files by relative path |
| `code_index(action="pre_scan")` MCP tool | `CodeIndexService.pre_scan_repository()` | Pre-scan Python imports only |
| `code_index(action="status")` MCP tool | Direct SQLite queries (symbol/file counts) | Status check |
| `repo_analyze` tool (orchestrator) | `CortexOrchestrator.analyze()` | End-to-end: sync -> index -> graph -> VCS |

## Parallel vs Sequential Path

The pipeline uses two execution paths depending on repository size:

| Path | Condition | Mechanism |
|------|-----------|-----------|
| **WorkerPool (parallel)** | >=15 files OR >=512KB total | `ThreadPoolExecutor(max_workers=cpu_count)` -- CPU-bound parsing dispatched to threads |
| **Sequential (async)** | <15 files AND <512KB total | `asyncio.gather` with `asyncio.Semaphore(10)` -- avoids thread pool overhead |

The sequential path avoids thread overhead for small repos. Each file is processed by `_process_file()` which handles enrichment + SQLite write in a single async pass. The WorkerPool path collects results before enrichment + SQLite write done asynchronously via `asyncio.gather(_write_parsed(...))`.
