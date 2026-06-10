# Filesystem Operations

**Version**: 1.0.0  
**Last Updated**: 2026-06-01

---

## Overview

The Filesystem module provides secure, audited file operations with support for:
- File read/write/delete operations
- Directory management
- Search and discovery
- Backup and recovery
- Performance monitoring

---

## Directory Structure

```
project-root/
├── logs/                      # Application logs
│   └── filesystem.log         # Filesystem operation logs
├── database/
│   └── backups/               # Automatic backups
├── outputs/                   # Generated outputs
├── src/modules/filesystem/
│   ├── __init__.py
│   ├── config.py              # Configuration
│   ├── operations.py          # Core operations
│   └── security.py            # Security utilities
└── .config/                   # Configuration files
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FILESYSTEM_BASE_PATH` | `./` | Base path for operations |
| `FILESYSTEM_MAX_SIZE` | 100MB | Maximum file size |
| `FILESYSTEM_ENABLE_ENCRYPTION` | true | Encrypt sensitive files |
| `FILESYSTEM_LOG_LEVEL` | INFO | Logging level |

### Configuration Class

```python
from src.modules.filesystem.config import FilesystemConfig

config = FilesystemConfig(base_path="/path/to/project")
config.is_safe_path(Path("/path/to/file"))  # Security check
config.is_sensitive(Path("credentials.env"))  # Sensitivity check
```

---

## Available Actions

### filesystem read
Read file contents.
```bash
codecortex_filesystem --action read --args '{"path": "/path/to/file.py"}'
```

### filesystem write
Write content to file.
```bash
codecortex_filesystem --action write --args '{"path": "/path/to/file.py", "content": "# code"}'
```

### filesystem delete
Delete file or directory.
```bash
codecortex_filesystem --action delete --args '{"path": "/path/to/file.py"}'
```

### filesystem list
List directory contents.
```bash
codecortex_filesystem --action list --args '{"path": "/path/to/dir"}'
```

### filesystem search
Search for files.
```bash
codecortex_filesystem --action search --args '{"path": "/path", "pattern": "*.py"}'
```

### filesystem audit
Security audit of files.
```bash
codecortex_filesystem --action audit --args '{"path": "/path"}'
```

---

## Security Features

1. **Path Traversal Prevention**: All paths are validated against base path
2. **Sensitive File Detection**: Auto-detects `.env`, `.key`, `.sql` files
3. **Permission Checking**: Validates read/write permissions
4. **Operation Logging**: All operations logged with user context

---

## Performance Standards

| Operation | Max Latency | Target |
|-----------|-------------|--------|
| read | 100ms | < 50ms |
| write | 200ms | < 100ms |
| delete | 100ms | < 50ms |
| list | 500ms | < 200ms |
| search | 1000ms | < 500ms |

---

## Maintenance Procedures

### Daily
- Check disk space usage
- Rotate log files

### Weekly
- Run filesystem audit
- Verify backup integrity

### Monthly
- Review access patterns
- Update security rules

---

## Error Handling

| Error Code | Description | Resolution |
|------------|-------------|------------|
| FS_001 | Path not allowed | Check base path config |
| FS_002 | Permission denied | Check file permissions |
| FS_003 | File too large | Reduce file size |
| FS_004 | Sensitive file | Use encrypted storage |

---

## Support

For issues, check logs at `logs/filesystem.log` or contact the DevOps team.