# fs_audit Tool

**Tool:** `fs_audit`  
**Category:** Filesystem Security Audit  
**Domain:** Filesystem  
**Version:** 1.0.0  
**AI Coder Impact:** 10/10 ⭐

---

## Overview

The `fs_audit` tool scans filesystem **metadata** (file names, permissions, sizes, locations) to detect security risks. It does **not** read file contents — for content-level scanning, use `code_audit` in the CodeAnalysis domain instead.

## Capabilities

### Detection Categories

| Category | Examples | Severity |
|----------|----------|----------|
| **Credentials** | `.env`, `*.key`, `id_rsa`, `*.p12`, `secrets.yml`, `credentials.json` | Critical |
| **Config sensitive** | `config.json`, `application.properties`, `database.yml` | High |
| **Database dumps** | `dump*.sql`, `*.dump`, `*.sqlite`, `*.db` | High |
| **Hidden VCS** | `.git/config`, `.git/credentials`, `.svn/entries` | High |
| **Permissions** | World-writable files (`o+w`) | High |
| **Backup/tmp** | `*.bak`, `*.old`, `*.swp`, `*~`, `*.tmp` | Medium |
| **Binary executables** | `*.exe`, `*.dll`, `*.bin` in source folders | Medium |
| **Suspicious names** | `token*`, `*secret*`, `*credential*`, `*auth*` | Medium |
| **Build artifacts** | `*.pyc`, `__pycache__/`, `*.class`, `*.o` | Low |
| **Large logs** | `*.log` > 50 MB | Low |
| **Dependencies** | `node_modules/`, `vendor/` | Low |

### Key Features

- **Metadata-Only Scanning:** Fast and safe — does not read file contents
- **Severity Categorization:** Critical, high, medium, low severity levels
- **Permission Analysis:** Detects world-writable and unusual executable permissions
- **Hidden VCS Detection:** Identifies exposed VCS configuration files
- **Recommendations:** Provides actionable remediation steps for each finding
- **Severity Filtering:** Filter findings by severity level
- **Exclusion Patterns:** Exclude specific paths from audit
- **Size Limits:** Skip large files to improve performance

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target` | string | ✅ | — | Absolute path to directory to audit |
| `recursive` | boolean | ❌ | `true` | Scan subdirectories recursively |
| `severity_filter` | array | ❌ | all | Filter: `["critical","high","medium","low"]` |
| `check_permissions` | boolean | ❌ | `true` | Check world-writable and unusual executable permissions |
| `check_hidden` | boolean | ❌ | `true` | Include hidden files/dirs (`.` prefix) |
| `max_file_size_mb` | integer | ❌ | `100` | Ignore files larger than this |
| `exclude_patterns` | array | ❌ | `[".git",".svn","node_modules"]` | Glob patterns to exclude |
| `limit` | integer | ❌ | `200` | Maximum findings to report |

## Output

### Result Structure

```json
{
  "success": true,
  "status_code": 200,
  "message": "Audit completed: 3 findings",
  "data": {
    "target": "/home/user/project",
    "summary": { "critical": 1, "high": 2, "medium": 0, "low": 0 },
    "findings": [
      {
        "severity": "critical",
        "category": "credentials",
        "path": ".env",
        "permissions": "644",
        "reason": "File .env contains secret keys and credentials.",
        "recommendation": "Remove from repo, add to .gitignore, rotate secrets."
      },
      {
        "severity": "high",
        "category": "permissions",
        "path": "script.sh",
        "permissions": "777",
        "reason": "World-writable file — anyone can modify.",
        "recommendation": "Use chmod 644 or 755."
      }
    ]
  }
}
```

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| FS_040 | high | Target path does not exist |
| FS_041 | medium | Invalid severity filter value |

## Examples

### 1. Full audit with all categories
```json
{
  "target": "/home/user/project"
}
```

### 2. Audit specific severity levels
```json
{
  "target": "/home/user/project",
  "severity_filter": ["critical", "high"]
}
```

### 3. Exclude dependencies and build artifacts
```json
{
  "target": "/home/user/project",
  "exclude_patterns": ["node_modules/", "vendor/", "__pycache__", "*.pyc"]
}
```

### 4. Skip permission checks
```json
{
  "target": "/home/user/project",
  "check_permissions": false
}
```

### 5. Limit findings and increase file size limit
```json
{
  "target": "/home/user/project",
  "max_file_size_mb": 500,
  "limit": 50
}
```

## Integration with Other Tools

| Tool | Integration |
|------|-------------|
| `code_audit` | `fs_audit` scans metadata, `code_audit` scans content — complementary |
| `fs_watch` | Use `fs_watch` to detect new files, then `fs_audit` to audit them |
| `fs_manage` | Use `fs_manage` to fix issues found (delete, chmod, write .gitignore) |
| `repo_git` | Commit fixes found by audit via `repo_git(subcommand="commit")` |

## Design Notes

- **Metadata-Only:** fs_audit does not read file contents — for speed and safety
- **Pattern Matching:** Uses glob patterns and regex for filename detection
- **Permission Parsing:** Uses stat_module for Unix permission analysis (octal to symbolic conversion)
- **Platform Differences:** Permission checks only apply on Unix systems (Linux/macOS)
- **Recommendation Generation:** Each finding includes a specific remediation recommendation

## See Also

- [File Watcher](../file-watcher/concept.md) — Auto-detect file changes
- [Security Guards](../security-guards/rules.md) — Path traversal, SSRF prevention
- [code_audit](../../codeanalysis/sub-features/code_audit/concept.md) — Content-level security audit
