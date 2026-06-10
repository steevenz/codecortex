# fs_manage Tool

**Tool:** `fs_manage`  
**Category:** Filesystem Management  
**Domain:** Filesystem  
**Version:** 1.0.0  
**AI Coder Impact:** 10/10 ⭐

---

## Overview

The `fs_manage` tool is a **unified filesystem management interface** that consolidates 16 file operations into a single MCP tool. This consolidation reduces tool count while maintaining full functionality for write, append, delete, move, chmod, chown, symlink, touch, archive, xattr, write_batch, convert, tree, tree_sync, and read operations.

> **Note:** `fs_manage` performs **pure file operations only** — it has no Git or SVN integration. For VCS operations (git rm, git mv, svn add, svn delete), use the `repo_git` and `repo_svn` tools in the **CodeRepository domain**.

## Operations

### 1. `write` - Create/Overwrite File

Creates a new file or overwrites an existing file.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"write"` |
| `path` | string | ✅ | - | Target file path |
| `content` | string | ✅ | - | File content (text or base64) |
| `encoding` | string | ❌ | `"utf8"` | `"utf8"` or `"base64"` |
| `overwrite` | boolean | ❌ | `true` | Overwrite existing file |
| `create_parents` | boolean | ❌ | `true` | Create parent directories |
| `backup_existing` | boolean | ❌ | `false` | Backup before overwrite |
| `atomic_write` | boolean | ❌ | `true` | Use temp file + rename |
| `permissions` | integer | ❌ | - | Unix permissions (e.g., 644) |

**Example:**
```json
{
  "operation": "write",
  "path": "/home/user/hello.txt",
  "content": "Halo dunia!",
  "encoding": "utf8",
  "overwrite": true,
  "create_parents": true
}
```

### 2. `append` - Append to File

Adds content to the end of an existing file.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"append"` |
| `path` | string | ✅ | - | Target file path |
| `content` | string | ✅ | - | Content to append |
| `encoding` | string | ❌ | `"utf8"` | `"utf8"` or `"base64"` |
| `create_parents` | boolean | ❌ | `true` | Create parent directories |

**Example:**
```json
{
  "operation": "append",
  "path": "/var/log/app.log",
  "content": "[INFO] Task completed\n"
}
```

### 3. `delete` - Delete Files/Directories

Deletes one or more files or directories.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"delete"` |
| `paths` | array | ✅ | - | List of paths to delete |
| `recursive` | boolean | ❌ | `true` | Delete directory contents |
| `force` | boolean | ❌ | `false` | Treat missing files as deleted |
| `dry_run` | boolean | ❌ | `false` | Simulate without changes |

**Example:**
```json
{
  "operation": "delete",
  "paths": ["src/old.py", "docs/outdated.md"],
  "recursive": true,
  "force": false
}
```

### 4. `move` / `rename` - Move/Rename Files

Moves or renames one or more files.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"move"` or `"rename"` |
| `operations` | array | ✅ | - | Array of `{source, destination}` |
| `create_dest_parents` | boolean | ❌ | `true` | Create destination parents |
| `overwrite` | boolean | ❌ | `false` | Overwrite destination |
| `dry_run` | boolean | ❌ | `false` | Simulate without changes |

**Example:**
```json
{
  "operation": "move",
  "operations": [
    {"source": "/tmp/data.csv", "destination": "/home/user/data.csv"}
  ],
  "create_dest_parents": true,
  "overwrite": false
}
```

### 5. `write_batch` - Write Multiple Files

Writes multiple files in a single batch operation. Useful for creating multiple files at once.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"write_batch"` |
| `items` | array | ✅ | - | Array of file items to write |
| `overwrite` | boolean | ❌ | `true` | Default overwrite for all items |
| `create_parents` | boolean | ❌ | `true` | Default create parents for all items |
| `dry_run` | boolean | ❌ | `false` | Simulate without changes |

**Item Structure:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `path` | string | ✅ | - | Target file path |
| `content` | string | ✅ | `""` | File content |
| `encoding` | string | ❌ | `"utf8"` | `"utf8"` or `"base64"` |
| `overwrite` | boolean | ❌ | - | Override default setting |
| `create_parents` | boolean | ❌ | - | Override default setting |
| `permissions` | integer | ❌ | - | Unix permissions |
| `backup_existing` | boolean | ❌ | `false` | Backup before overwrite |
| `atomic_write` | boolean | ❌ | `true` | Use temp file + rename |

**Example:**
```json
{
  "operation": "write_batch",
  "items": [
    {"path": "/home/user/file1.txt", "content": "Content 1"},
    {"path": "/home/user/file2.txt", "content": "Content 2"},
    {"path": "/home/user/subdir/file3.txt", "content": "Content 3", "create_parents": true}
  ],
  "overwrite": true,
  "create_parents": true
}
```

### 6. `chmod` - Change File Permissions

Changes file permissions (Unix-style). Supports both octal and symbolic notation.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"chmod"` |
| `paths` | array | ✅ | - | List of file/directory paths |
| `mode` | string/int | ✅ | - | Permission mode (e.g., `"755"`, `"u+rwx"`) |
| `recursive` | boolean | ❌ | `false` | Apply to directory contents |
| `dry_run` | boolean | ❌ | `false` | Simulate without changes |

**Examples:**
```json
{
  "operation": "chmod",
  "paths": ["/home/user/script.sh"],
  "mode": "755"
}
```

```json
{
  "operation": "chmod",
  "paths": ["/home/user/projects"],
  "mode": "u+rwx,g-w,o-r",
  "recursive": true
}
```

**Cross-Platform Support:**
| Platform | Support | Notes |
|----------|---------|-------|
| Linux | ✅ Full | POSIX permissions |
| macOS | ✅ Full | POSIX permissions |
| Android (Termux) | ✅ File only | ACL not supported |
| Windows | ⚠️ Limited | Only readonly flag |

### 7. `chown` - Change File Ownership

Changes file owner and/or group. **Not supported on Windows.**

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"chown"` |
| `paths` | array | ✅ | - | List of file/directory paths |
| `owner` | string/int | ❌ | - | Username or UID |
| `group` | string/int | ❌ | - | Group name or GID |
| `recursive` | boolean | ❌ | `false` | Apply to directory contents |
| `dry_run` | boolean | ❌ | `false` | Simulate without changes |

**Example:**
```json
{
  "operation": "chown",
  "paths": ["/var/www/index.html"],
  "owner": "www-data",
  "group": "www-data"
}
```

**Cross-Platform Support:**
| Platform | Support | Notes |
|----------|---------|-------|
| Linux | ✅ Root only | Requires superuser |
| macOS | ✅ Root only | Requires superuser |
| Android (Termux) | ❌ | No root access |
| Windows | ❌ | Not supported |

### 8. `symlink` - Create Symbolic Link

Creates a symbolic link pointing to a target file or directory.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"symlink"` |
| `target` | string | ✅ | - | Target path (file or directory) |
| `link_path` | string | ✅ | - | Path for the new symlink |
| `overwrite` | boolean | ❌ | `false` | Replace existing link |
| `is_directory` | boolean | ❌ | `false` | Hint: target is directory |
| `dry_run` | boolean | ❌ | `false` | Simulate without changes |

**Example:**
```json
{
  "operation": "symlink",
  "target": "/home/user/projects/app",
  "link_path": "/home/user/current_app",
  "overwrite": true
}
```

**Cross-Platform Support:**
| Platform | Support | Notes |
|----------|---------|-------|
| Linux | ✅ Full | Any user |
| macOS | ✅ Full | Any user |
| Android (Termux) | ✅ | Filesystem dependent |
| Windows | ⚠️ Limited | Developer Mode/Admin required |

### 9. `touch` - Create File or Update Timestamps

Creates a new file or updates timestamps on an existing file. Useful for creating placeholder files, build artifacts, or updating file modification times.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"touch"` |
| `path` | string | ✅ | - | Target file path |
| `create_if_not_exists` | boolean | ❌ | `true` | Create file if it doesn't exist |
| `set_timestamps` | object | ❌ | - | Custom timestamps: `{"access_time": "ISO8601", "modify_time": "ISO8601"}` |
| `dry_run` | boolean | ❌ | `false` | Simulate without changes |

**Timestamp Format:**
- ISO 8601 format: `"2026-05-23T12:00:00Z"`
- Either `access_time` or `modify_time` can be omitted
- If omitted, current time is used for that timestamp

**Examples:**

Create a new file with current timestamps:
```json
{
  "operation": "touch",
  "path": "/home/user/logs/app.log",
  "create_if_not_exists": true
}
```

Update specific timestamps on existing file:
```json
{
  "operation": "touch",
  "path": "/var/log/nginx/access.log",
  "set_timestamps": {
    "access_time": "2026-05-01T00:00:00Z",
    "modify_time": "2026-05-01T00:00:00Z"
  }
}
```

### 10. `archive` - Archive Operations (list/extract/create)

Creates, lists, or extracts ZIP and TAR archives. Supports all common formats: zip, tar, tar.gz, tar.bz2, tar.xz.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"archive"` |
| `action` | string | ✅ | `"list"` | `"list"`, `"extract"`, or `"create"` |
| `archive_path` | string | ✅ | - | Path to archive file (uses `path` if unset) |
| `target` | string | ❌ | - | For extract: destination directory. For create: source directory |
| `files_to_add` | array | ❌ | - | For create: list of files/dirs to include |
| `overwrite` | boolean | ❌ | `false` | Overwrite existing archive/files |
| `compression_level` | integer | ❌ | `6` | 0-9 compression (zip/gz only) |
| `dry_run` | boolean | ❌ | `false` | Simulate without changes |

**Format auto-detection:**
| Extension | Format |
|-----------|--------|
| `.zip` | ZIP |
| `.tar` | TAR (uncompressed) |
| `.tar.gz`, `.tgz` | TAR + GZip |
| `.tar.bz2`, `.tbz2` | TAR + BZip2 |
| `.tar.xz`, `.txz` | TAR + XZ |

**Security:**
- **Path traversal prevention**: Entries with `..` are rejected during extraction
- **Overwrite guard**: If `overwrite=false` and files exist, extraction aborts with 409

**Examples:**

List archive contents:
```json
{
  "operation": "archive",
  "action": "list",
  "archive_path": "/home/user/backup.zip"
}
```

Extract archive:
```json
{
  "operation": "archive",
  "action": "extract",
  "archive_path": "/home/user/backup.zip",
  "target": "/home/user/restore",
  "overwrite": false
}
```

Create archive from directory:
```json
{
  "operation": "archive",
  "action": "create",
  "archive_path": "/home/user/source_backup.tar.gz",
  "target": "/home/user/project",
  "overwrite": true,
  "compression_level": 9
}
```

### 11. `xattr` - Extended Attributes (list/get/set/remove)

Read and write extended attributes (xattr) on files and directories. **Only supported on Linux/macOS.** On Windows, returns 501.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"xattr"` |
| `action` | string | ✅ | `"list"` | `"list"`, `"get"`, `"set"`, or `"remove"` |
| `path` | string | ✅ | - | Path to file or directory |
| `xattr_name` | string | ❌ | - | Attribute name (required for get/set/remove) |
| `xattr_value` | string | ❌ | - | Attribute value (required for set) |
| `encoding` | string | ❌ | `"utf8"` | `"utf8"` or `"base64"` for binary values |
| `recursive` | boolean | ❌ | `false` | Apply to all files in directory tree |

**Cross-Platform Support:**
| Platform | Support | Notes |
|----------|---------|-------|
| Linux | ✅ Full | Native xattr via `os.listxattr`/`getxattr`/`setxattr` |
| macOS | ✅ Full | Native xattr via `os.*` functions |
| Windows | ❌ 501 | Use NTFS Alternate Data Streams instead |

### 12. `convert` — File Format Conversion

Converts between data formats (CSV, JSON, XLSX, XML, YAML), image formats (PNG, JPEG, WEBP, BMP, TIFF, GIF), and text encodings (UTF-8, UTF-16, ASCII, etc.).

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"convert"` |
| `path` | string | ❌ | - | Source file path |
| `target` | string | ✅ | - | Target file path |
| `convert_type` | string | ❌ | `"data"` | `"data"`, `"image"`, or `"encoding"` |
| `source_content` | string | ❌ | - | Inline content string (alternative to source file) |
| `source_format` | string | ❌ | auto | Format hint (e.g. `"json"`, `"csv"`, `"png"`) |
| `target_format` | string | ❌ | auto | Format hint (e.g. `"xlsx"`, `"jpeg"`, `"utf-16"`) |
| `convert_options` | object | ❌ | `{}` | Type-specific options (see below) |
| `overwrite` | boolean | ❌ | `false` | Overwrite target if exists |
| `dry_run` | boolean | ❌ | `false` | Simulate without writing |

**Supported formats:**
| Type | Formats |
|------|---------|
| Data | CSV, JSON, XLSX, XML, YAML |
| Image | PNG, JPEG, WEBP, BMP, TIFF, GIF |
| Encoding | UTF-8, UTF-16, ASCII, Latin-1, CP1252 |

**Dependencies:**
- **Data**: pandas (recommended), openpyxl (for XLSX), PyYAML (for YAML)
- **Image**: Pillow (PIL)
- **Encoding**: Built-in Python `codecs`

All dependencies are optional — fallback modes use built-in modules when available.

### 13. `tree` - Directory Tree Structure

Generates a directory tree structure with optional database caching.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"tree"` |
| `path` | string | ✅ | - | Target directory path |
| `max_depth` | integer | ❌ | unlimited | Maximum tree depth |
| `include_hidden` | boolean | ❌ | `false` | Include hidden files/dirs |
| `repo_id` | string | ❌ | - | Repository UUID for DB cache lookup |

### 14. `tree_sync` - Sync Tree to Database Cache

Synchronizes directory tree to the database cache for fast retrieval.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"tree_sync"` |
| `path` | string | ✅ | - | Target directory path |
| `repo_id` | string | ❌ | - | Repository UUID |

### 15. `read` - Read File Content

Reads file content with encoding detection and line counting.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `operation` | string | ✅ | - | Must be `"read"` |
| `path` | string | ✅ | - | Target file path |
| `encoding` | string | ❌ | auto | File encoding (auto-detect if omitted) |
| `include_line_numbers` | boolean | ❌ | `false` | Include line numbers in output |
| `max_lines` | integer | ❌ | unlimited | Maximum lines to read |

## VCS Operations

`fs_manage` does **not** perform Git or SVN operations. It is a pure filesystem tool.

For VCS-aware file operations, use the **CodeRepository domain** tools:

| Use Case | Tool |
|----------|------|
| `git rm` (remove tracked files) | `repo_git` with `action="delete"` |
| `git mv` (rename with history) | `repo_git` with `action="move"` |
| `svn delete` | `repo_svn` with appropriate action |
| View git log / diff | `repo_git` with `action="log"` or `"diff"` |

> **Design decision:** Separating VCS operations into the CodeRepository domain keeps `fs_manage` lightweight, testable, and VCS-agnostic. Use `repo_id` parameters where path resolution against a registered repository is needed.

## repo_id Parameter

Most operations accept an optional `repo_id` (Repository UUID). When provided, relative paths are resolved against the registered repository root, allowing shorter paths in requests.

```json
{
  "operation": "write",
  "repo_id": "abc-123-def-456",
  "path": "src/main.py",
  "content": "print('hello')"
}
```

Without `repo_id`, all paths must be absolute. Use `repo list` or `repo inspect` to find your repository UUID.

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| FS_000 | high | Path traversal not allowed |
| FS_001 | high | Path does not exist |
| FS_002 | high | Permission denied |
| FS_003 | high | Invalid operation or parameters |
| FS_004 | high | Unknown operation |
| FS_5xx | critical | Internal error |

## See Also

- [File Watcher](../file-watcher/concept.md) — Auto-detect file changes
- [Security Guards](../security-guards/rules.md) — Path traversal, SSRF prevention
