# CodeIndex: Execution Flow

> **Pipeline:** Repository Discovered → File Walked → Parsed → Symbols Extracted → Stored

## Pipeline Stages

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. File     │────>│  2. AST      │────>│  3. Symbol   │────>│  4. Persist  │
│   Discovery  │     │   Parsing    │     │   Extraction │     │   (SQLite)   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                      │                     │
       │  Glob-based walk   │  TreeSitterManager    │  Converters.py     │  INSERT INTO
       │  Respects          │  selects parser by    │  transforms AST    │  symbols, files,
       │  .gitignore        │  file extension       │  data to RawSymbol │  directories
       └────────────────────┴──────────────────────┴─────────────────────┘
```

## Detailed Sequence

### Phase 1: File Discovery
1. `repo_init` or `repo_sync_incremental` triggers file discovery
2. `FilesystemService` walks the directory tree using glob patterns
3. Ignores: `.gitignore`, `.codecortexignore`, binary files, files >10MB
4. Classifies files: code / doc / config / binary / other
5. Writes to `directories` and `files` tables

### Phase 2: AST Parsing
1. `index_repo` tool called → `CodeIndexService.index_repository()`
2. Worker pool dispatches files to thread pool workers
3. Each worker uses `TreeSitterManager` to get the right parser
4. Parser produces a CST (Concrete Syntax Tree) or AST
5. AST cache checked before parsing (keyed by content hash)

### Phase 3: Symbol Extraction
1. `TreeSitterParser` walks AST nodes
2. Extracts: functions, classes, variables, imports, exports
3. Frame extraction captures: inheritance, decorators, generics
4. Framework detection enriches metadata (is this a React component? A FastAPI route?)
5. `converters.py` transforms parser dicts into `RawSymbol` DTOs
6. Scope resolution runs on extracted symbols (multi-pass)

### Phase 4: Storage
1. Symbols written to `symbols` table with file_id, line ranges, signatures
2. Edges created for CALLS, INHERITS, IMPORTS, USES, DEFINES relationships
3. Manifest entries updated for incremental tracking
4. Embeddings generated for semantic search chunks
5. Commit hash recorded for staleness checks

## Key Entry Points

| Trigger | Method | Description |
|---------|--------|-------------|
| `index_repo` tool | `CodeIndexService.index_repository()` | Full re-index of all files |
| `index_file` tool | `CodeIndexService.index_file_with_tree_sitter()` | Single file re-index |
| `repo_analyze` tool | `CortexOrchestrator.analyze()` | End-to-end: discover → index → analyze |
| `repo_sync_incremental` tool | `CodeRepositoryService.sync_repository_incremental()` | Git diff-based partial re-index |
