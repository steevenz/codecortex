# Security Guards

> **Source:** `src/main.py` (validate_path, validate_uuid) + FilesystemService

## Rules

### Path Traversal Prevention

```
Rule: Reject any path containing ".." or starting with "/"
Reason: Prevents access to files outside the repository root
Enforcement: All fs_* tools + repo initialization
```

### SSRF Prevention

```
Rule: Only accept local file system paths, not URLs
Reason: Prevents server-side request forgery via file operations
Enforcement: repo_init, repo_analyze, all fs_* tools
```

### UUID Validation

```
Rule: All repository_id and file_id parameters must be valid UUIDs
Reason: Prevents injection through ID parameters
Enforcement: graph_build, index_file, fs_tree, etc.
```

### Input Depth Limit

```
Rule: max_depth must be between 1 and 20
Reason: Prevents excessive recursion in large codebases
Enforcement: repo_init, repo_analyze, multi_repo_sync
```

### Dry-Run Requirement

```
Rule: All destructive operations default to dry_run=True
Reason: Prevents accidental data loss
Override: Must explicitly pass dry_run=False to execute
Enforcement: fs_write, fs_manage, fs_batch, refactor_symbol, search_replace
```

### Quota Enforcement

```
Rule: Maximum 50 concurrent repositories
Reason: Prevents resource exhaustion
Enforcement: multi_repo_sync checks CODECORTEX_MAX_REPOS
```
