# Global Registry & Staleness Detection

**Domain:** CodeRepository  
**Effort:** Low | **Impact:** Medium | **Priority:** 4

## Current State
CodeCortex manages repos only via SQLite per-project. No cross-session discovery:
- No way to list all previously indexed repos
- No staleness detection (is index behind HEAD?)
- No canonical path resolution (symlinks, worktrees)
- No validation that analysis completed successfully

## Proposed Improvement
Implement a global registry at `~/.codecortex/registry.json` matching GitNexus's approach:
1. **Registry file**: JSON array of `{name, path, storagePath, lastCommit, remoteUrl, indexedAt, stats}`
2. **Staleness Check**: `git rev-list --count {lastCommit}..HEAD` via subprocess
3. **Canonical Path**: `Path.resolve().absolute()` + `realpath` on Windows
4. **MCP Tools**: `list_repos`, `check_staleness(repo_id)`, `get_registry_path(repo_id)`

## Architecture
```
~/.codecortex/registry.json
  └── [{name: "my-app", path: "/home/user/projects/my-app", lastCommit: "abc123", ...}]

check_staleness(path, lastCommit) → {is_stale: bool, commits_behind: int}
canonicalize_path(path) → resolved_path
```

## Key Changes in CodeCortex
- **`src/domain/coderepository/application/registry.py`**: New module with RegistryManager  
- **`src/domain/coderepository/api/tools.py`**: Add `list_repos`, `check_staleness`, `get_repo_info`  
- **`src/domain/coderepository/application/service.py`**: Add registry update after sync  
- **DB**: Add `last_commit` to `repositories` table (migration)

## Dependencies
- Pure Python (json, pathlib, subprocess)

## Effort Breakdown
- `registry.py`: ~120 lines  
- Edit `tools.py`: ~80 lines  
- Edit `service.py`: ~20 lines  
- Tests: ~70 lines  
- **Total: ~3 hours**
