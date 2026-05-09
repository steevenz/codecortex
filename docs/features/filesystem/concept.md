# Filesystem: File Operations

> **Domain:** Filesystem
> **Package:** `src/domain/filesystem/`

## Concept

The Filesystem domain provides secure, indexed file operations. Instead of direct disk access, all operations go through a service layer that validates paths, prevents traversal attacks, and keeps the database indexes in sync.

## MCP Tools

| Tool | Function |
|------|----------|
| `fs_tree` | Get the full directory and file tree from index |
| `fs_read` | Read file content from repository index |
| `fs_write` | Write or overwrite a file (CAUTION: replaces entire file) |
| `fs_manage` | Delete or move/rename files in the repository |
| `fs_glob` | List files matching a glob pattern |
| `fs_batch` | Execute multiple file operations in one call |

## Security

All file operations validate:
1. **Path traversal:** `..` and absolute paths are rejected
2. **SSRF:** URLs are not accepted as file paths
3. **Repository scope:** Operations are scoped to the repository root
4. **Dry-run by default:** All write/delete/move operations require explicit `dry_run=False`

## Sub-Features

- [Batch Operations](sub-features/batch-operations/concept.md) — Multi-file operations in one call
- [File Watcher](sub-features/file-watcher/concept.md) — Auto-detect file changes
- [Security Guards](sub-features/security-guards/rules.md) — Path traversal, SSRF prevention
