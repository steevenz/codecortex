# Working Context - CodeCortex MCP

## Current State
- [x] Initial codebase analysis and domain mapping completed.
- [x] FastMCP server initialized and basic tool skeleton registered.
- [x] Multi-domain service architecture established (Repository, Index, Graph, Refactor, FS, QA).
- [x] Circular dependencies resolved in `Orchestrator` and `CodeIndexService`.
- [x] SSE Transport layer implemented in `http_server.py`.
- [x] Node.js Proxy implemented with state management and locking.
- [x] Consolidation Plan (42 -> 27 tools) approved and in progress.
- [x] Phase 0 (Gitignore Fix) - **DONE**: Implemented recursive `.gitignore` and `.codecortexignore` support in `service.py`.

## Targets (Phase 2: Hardening & Best Practices)
1. **Repository Hardening**:
   - [ ] Implement `max_depth` in `repo_init` (default: unlimited, but follows gitignore).
   - [ ] Implement `max_file_size` exclusion (5MB default) for indexing.
   - [ ] Add `arch_analyze` unified tool (merging summary + analysis).
2. **Refactor Hardening**:
   - [ ] Add `diff` preview to `dry_run` results in `RefactorResult`.
   - [ ] Ensure consistent `dry_run=True` default in all refactor tools.
3. **Transport & Reliability**:
   - [ ] Standardize `rpc_error` consistency in `http_server.py`.
   - [ ] Validate `asyncio` loop handling on Windows in all entry points.
   - [ ] Ensure `package.json` bin names match documentation.
4. **Security**:
   - [ ] Remove internal utility tools (`validate_url_safe`, `sanitize_graph_label`) from MCP layer.
   - [ ] Finalize `arch_audit` for security/hygiene.

## Gaps
- [ ] `readline` hang potential on Windows if output exceeds buffer (mitigated by unbuffered python, but needs verification).
- [ ] Stale lock detection is time-based (10s), could be improved with PID check.
- [ ] Circular dependency risk in `http_server.py` (imports `mcp` from `main.py`).

## Target Queue
1. `repo_init` depth parameter and best practice filters.
2. `refactor_*` diff preview implementation.
3. `arch_analyze` and `arch_audit` tool merges.
4. `http_server.py` RPC error standardization.
