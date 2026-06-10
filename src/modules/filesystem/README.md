# CodeCortex Filesystem Domain

## Overview
The **Filesystem Domain** provides safe, sandboxed file system operations for the MCP protocol. It includes file browsing, reading, writing, searching, watching, disk usage reporting, auditing, and git/SVN integration with strict path traversal and SSRF guards.

## Architecture
DDD + Hexagonal Architecture:
- **api/**: MCP tool registrations (9 tools)
- **core/**: `FilesystemService` — primary orchestration with MCP safety guards
- **adapters/**: 21 specialized operation adapters

## Key Components
- **FilesystemService**: Central orchestrator with path validation and security enforcement
- **21 adapters**: Specialized, single-responsibility adapters for each operation type

| Adapter | Description |
|---------|-------------|
| `fs_tree` | Directory tree browsing with depth control |
| `fs_reader` | File reading with encoding detection and size limits |
| `fs_writer` | Safe file writing with backup creation |
| `fs_deleter` | File/directory deletion with confirmation |
| `fs_search` | Multi-strategy file search (glob, regex, content) |
| `fs_analyzer` | File content analysis (bugs, TODOs, dead code) |
| `fs_audit` | Security audit (permissions, secrets, misconfig) |
| `fs_df` | Disk usage reporting |
| `fs_watch` | Real-time file change watching |
| `fs_watcher` | Inotify/polling-based file monitoring |
| `fs_walker` | Recursive directory walker with pattern filtering |
| `fs_touch` | File creation and timestamp update |
| `fs_chmod` | Permission modification |
| `fs_chown` | Ownership modification |
| `fs_manager` | General file management operations |
| `fs_git` | Git operations (status, log, diff, commit) |
| `fs_svn` | SVN operations |
| `fs_symlink` | Symbolic link management |
| `fs_xattr` | Extended attribute operations |
| `fs_archiver` | Archive creation and extraction |
| `fs_converter` | File format conversion |

## Tools
| Tool | Description |
|------|-------------|
| `fs_tree` | Browse directory tree |
| `fs_read` | Read file contents |
| `fs_manage` | Create, move, copy, delete files/directories |
| `fs_search` | Search files by name, pattern, or content |
| `fs_watch` | Watch filesystem for changes |
| `fs_df` | Show disk usage |
| `fs_audit` | Security audit of file permissions and structure |
| `fs_git` | Execute git operations |
| `fs_svn` | Execute SVN operations |

## Security
- Path traversal prevention (blocks `..`, absolute paths outside workspace)
- SSRF guards (validates remote URLs)
- Max file size limit: 10 MB
- Blocked system paths: `/etc`, `/proc`, `/sys`, `/dev`, `C:\Windows`, `C:\System32`
- All operations validated before execution

## Dependencies
- **coderepository**: Repository metadata
- **codegraph**: Graph service integration
- **codeindex**: Index service for content-aware operations
- **codetester**: QA integration
- **core**: Database, errors, logging, telemetry
