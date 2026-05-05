# WORKING-CONTEXT.md

## Current State
- **FilesystemService** and **GitService** are migrated to `async`.
- **CodeRefactorService** is migrated to `async`.
- **CodeIndexService** and **CodeGraphService** are still synchronous and require migration.
- **main.py** orchestrator needs propagation of `await` for all tools.

## Gaps
- `CodeIndexService` still uses blocking I/O for file reads and parsing.
- `CodeGraphService` performs heavy calculations on the main event loop thread.
- `CortexOrchestrator` methods are not yet `async`.

## Target Queue
1. Migrate `CodeIndexService` to `async`.
2. Migrate `CodeGraphService` to `async`.
3. Update `CortexOrchestrator` and `main.py` tool handlers.
4. Verify end-to-end async pipeline.

## Done
- Refactored `coderepository` domain.
- Renamed `repository` to `coderepository`.
- Implemented `async` in `GitService` and `FilesystemService`.
