# Filesystem: Secure File Operations

> **Domain:** Filesystem
> **Package:** `src/modules/filesystem/`
> **Version:** 1.0.0
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

Filesystem is the **foundational file operations layer** for CodeCortex — provides secure, indexed file operations with path validation, traversal attack prevention, and database index synchronization. It delivers 5 MCP tools for unified file management, search, change watching, disk usage analysis, and security auditing.

## Why This Exists

- **Security Enforcement:** Filesystem enforces path traversal prevention, SSRF guards, and repository scoping for all file operations
- **AI Coder Empowerment:** Provides rich JSON outputs with file_type, size_bytes, context snippets, and dry-run previews for AI-assisted development
- **Index Synchronization:** Keeps database indexes in sync with filesystem changes via tree caching and incremental updates
- **Batch Operations:** Enables multi-file operations in a single MCP call via write_batch for reduced round-trips
- **VCS Integration:** fs_watch and fs_df provide Git/SVN-aware change detection and disk usage categorization
- **Cross-Platform Support:** Handles Linux, macOS, and Windows with platform-specific behavior clearly documented
- **Dry-Run Safety:** All destructive operations default to dry_run=True to prevent accidental data loss

## Theoretical Foundation

- **Path Normalization:** Forward-slash normalization for cross-platform path handling
- **MIME Type Detection:** mimetypes library for file type identification
- **Tree-Sitter Parsing:** For language detection in search operations
- **SentenceTransformers:** (future) Semantic embeddings for content search
- **Polling-Based Watching:** Snapshot comparison for change detection (MCP is synchronous, no streaming)
- **Git/SVN Integration:** subprocess calls to git/svn for VCS-aware operations
- **Recursive Directory Traversal:** Depth-limited tree generation with hidden file filtering
- **Database Caching:** FileIntegrity cache for instant tree retrieval when synced
- **Atomic Writes:** Temp file + rename pattern for safe file writes
- **Permission Handling:** stat_module for Unix permissions, Windows readonly flag
- **Dry-Run Simulation:** Pre-computation of operation impact without execution
- **Token Economy:** Auto-truncation based on token budget with summary mode

## Architecture

```
src/modules/filesystem/
├── api/              → tools.py: 5 MCP tools, cli.py: CLI commands, api_response() compliant
├── adapters/         → 22 adapters: DiskTree, DiskSearch, DiskWatcher, DiskUsage, DiskAudit, etc.
├── core/            → service.py: FilesystemService (DI via constructor), dtos.py: typed DTOs
└── __init__.py        → Package initialization with Aegis-Filesystem-v1.0 standard
```

## Domain Boundary

- **Owns:** `fs_manage`, `fs_search`, `fs_watch`, `fs_df`, `fs_audit`
- **Does NOT own:** `repo_git`, `repo_svn` (handled by CodeRepository domain)
- **Depends on:** DatabaseManager, FileIntegrity (for tree caching)
- **Consumed by:** MCP layer via `api/tools.py`

## CLI Architecture Note

The CLI domain is named `fs` (not `filesystem`) as an intentional UX decision. Users access filesystem operations via `codecortex fs <command>`.

## ~/.aicoders/ Compliance

- **API Standard:** `api_response()` for all tool responses
- **DDD:** `api/` + `adapters/` + `core/` separation
- **DI:** Constructor injection for services (FilesystemService)
- **Boundary:** Data crosses layers only via DTOs
- **Error Handling:** Guard clauses, structured errors via ApiError
- **Logging:** `CodeCortex.Filesystem.*` logger namespace
- **Documentation:** All docs in `docs/features/filesystem/`
- **Standard:** Aegis-Filesystem-v1.0

## VCS Integration Strategy

Filesystem domain follows a **pure filesystem first** approach:

| Tool | VCS Capability | Rationale |
|------|---------------|-----------|
| `fs_manage` | **None** | Pure filesystem operations only — VCS operations belong in CodeRepository domain |
| `fs_search` | **None** | Pure filesystem scan only — VCS search via CodeRepository domain |
| `fs_watch` | `since="git:<rev>"` or `since="svn:<rev>"` | VCS-aware change detection via polling comparison |
| `fs_df` | `vcs_integration="git"` or `"svn"` | VCS-categorized disk usage breakdown |
| `fs_audit` | Metadata-only VCS detection | Detects hidden VCS files (`.git/config`, `.svn/entries`) — metadata scan only |

**VCS Operations (CodeRepository domain):**
- `repo_git` — Full Git operations (status, commit, push, pull, branch, etc.)
- `repo_svn` — Full SVN operations (status, commit, update, etc.)
- `code_audit` — Content-based code audit with `include_git_history=True`

## Security Model

All file operations enforce multiple security layers:

### Core Security Rules

1. **Path Traversal Prevention**
   - **Rule:** Rejects paths containing `..` or starting with `/` (absolute paths)
   - **Reason:** Prevents access to files outside the repository root
   - **Enforcement:** All fs_* tools + repo initialization

2. **SSRF Prevention**
   - **Rule:** Only accepts local filesystem paths, not URLs
   - **Reason:** Prevents server-side request forgery via file operations
   - **Enforcement:** repo_init, repo_analyze, all fs_* tools

3. **UUID Validation**
   - **Rule:** All repository_id and file_id parameters must be valid UUIDs
   - **Reason:** Prevents injection through ID parameters
   - **Enforcement:** graph_build, index_file, fs_tree, etc.

4. **Input Depth Limit**
   - **Rule:** max_depth must be between 1 and 20
   - **Reason:** Prevents excessive recursion in large codebases
   - **Enforcement:** repo_init, repo_analyze, multi_repo_sync

5. **Dry-Run Requirement**
   - **Rule:** All destructive operations default to dry_run=True
   - **Reason:** Prevents accidental data loss
   - **Override:** Must explicitly pass dry_run=False to execute
   - **Enforcement:** fs_manage, fs_search, refactor_symbol

6. **Repository Scope**
   - Operations are scoped to the repository root via repo_id validation
   - Prevents cross-repository access without explicit authorization

7. **Blocked Paths**
   - System directories blocked (`/etc`, `/proc`, `/sys`, `/dev`, `C:\Windows`, `C:\System32`)
   - Prevents access to system-critical files

8. **Max File Size**
   - 10MB limit enforced (configurable via security settings)
   - Prevents resource exhaustion on large file operations

9. **Quota Enforcement**
   - Maximum 50 concurrent repositories
   - Prevents resource exhaustion
   - Enforced by multi_repo_sync checks CODECORTEX_MAX_REPOS

## Error Codes

| Prefix | Tool |
|--------|------|
| FS_0xx | fs_manage |
| FS_01x | fs_search |
| FS_02x | fs_watch |
| FS_03x | fs_df |
| FS_04x | fs_audit |
| FS_5xx | Internal error |

## 10/10 AI Coder Impact Features

1. **Rich JSON Metadata:** Every operation returns file_type, size_bytes, timestamps, permissions for context awareness
2. **Dry-Run Previews:** All destructive operations provide impact analysis before execution
3. **Context Snippets:** fs_search returns surrounding lines for LLM context
4. **Diff Preview:** Search-and-replace with unified diff format
5. **Tree Caching:** Database-backed tree retrieval for instant directory structure
6. **VCS-Aware Change Detection:** Git/SVN integration in fs_watch and fs_df
7. **Batch Operations:** write_batch reduces round-trips for multi-file operations
8 **Platform-Specific Notes:** Clear documentation of Windows vs Unix behavior in responses
9. **Security Scanning:** fs_audit detects sensitive files with severity categorization
10. **Language Detection:** Automatic language detection for source code files

## Token Economy

All responses pass through `api_response()` which auto-truncates data exceeding token budget when `summary_mode=True`.

---

## Related Sub-Features

All filesystem documentation is organized under tool-specific concept documents in the sub-features directory.

## Tool Reference

For detailed tool reference, see sub-feature concept documents:

- [fs_manage](sub-features/fs_manage/concept.md) — Unified filesystem management (16 operations)
- [fs_search](sub-features/fs_search/concept.md) — Filesystem search with content regex and replace
- [fs_watch](sub-features/fs_watch/concept.md) — File change watcher with Git/SVN integration
- [fs_df](sub-features/fs_df/concept.md) — Disk usage analyzer with VCS integration
- [fs_audit](sub-features/fs_audit/concept.md) — Filesystem security audit
