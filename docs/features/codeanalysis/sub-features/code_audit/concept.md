# Code Audit Tool

**Tool:** `code_audit`  
**Category:** Compliance Audit  
**Domain:** CodeAnalysis  
**Version:** 2.0.0  
**AI Coder Impact:** 10/10 ⭐

---

## Overview

The `code_audit` tool performs comprehensive compliance auditing against ~/.aicoders/ standards. It validates code across 24 categories including security, coding standards, architecture, and syntax. Returns actionable findings with error codes, remediation steps, and a compliance score (0-100).

## Audit Categories (24)

### Security Categories

| Category | Code Prefix | Checks | Severity |
|----------|-------------|--------|----------|
| **secrets** | CA_SEC | Hardcoded API keys, tokens, passwords | critical/high |
| **pii** | CA_PII | Email, SSN, credit card | critical/high |
| **misconfig** | CA_MIS | Debug mode, wildcard CORS | high |
| **vulns** | CA_VUL | SQL injection, eval, pickle | critical |

### Coding Standards

| Category | Code Prefix | Checks | Severity |
|----------|-------------|--------|----------|
| **comments** | CA_CMT | TODO, FIXME, HACK, STUB, BUG | low/medium |
| **naming** | CA_NAM | PascalCase/SnakeCase compliance | low |
| **type_hints** | CA_TYP | Missing type hints on public API | medium |
| **file_structure** | CA_STR | Header DocBlock validation | medium |
| **class_docblock** | CA_DOC | Class-level DocBlock validation | medium |
| **modular** | CA_MOD | God class, direct cross-module instantiation | medium |
| **modular_structure** | CA_MDL | Folder structure compliance | medium |
| **error_handling** | CA_ERR | Bare except, try without catch | high |
| **di_compliance** | CA_DI | Direct instantiation instead of DI | medium |
| **docblock** | CA_DOC | Method DocBlock validation | medium |
| **logging** | CA_LOG | Logger usage validation | medium |
| **api_response** | CA_API | API standard compliance | high |
| **codification** | CA_COD | UUID v4 vs v7, code field validation | medium |
| **coding_naming** | CA_CNAM | Directory naming, interface naming, constants | low |

### Architecture

| Category | Code Prefix | Checks | Severity |
|----------|-------------|--------|----------|
| **architecture** | CA_ARCH | Circular imports, service locator, high coupling, framework coupling | medium/high |

### Syntax

| Category | Code Prefix | Checks | Severity |
|----------|-------------|--------|----------|
| **syntax** | CA_SYN | Unclosed brackets, mismatched brackets, mixed indentation, trailing whitespace, missing semicolons, unclosed quotes | critical/high |

### Optional Categories

| Category | Code Prefix | Checks | Severity |
|----------|-------------|--------|----------|
| **semver** | CA_SEM | Semantic versioning validation | medium |
| **pwa** | CA_PWA | PWA compliance checks | medium |
| **crossplatform** | CA_CRO | Cross-platform validation | medium |
| **test_debug** | CA_TD | Test file conventions | medium |

## Capabilities

### Auto-Fix Generation

Generate automatic fix suggestions for common issues with diff preview:

- ✅ Trailing whitespace → auto-remove
- ✅ Blank line whitespace → auto-remove
- ✅ Missing semicolons → auto-add
- ✅ Unclosed brackets → suggestion with expected closing
- ⚠️ Mixed indentation → manual fix needed
- ⚠️ Unclosed quotes → manual fix needed

### Incremental Scanning

Only scan files modified since a given timestamp:

```python
request = AuditRequest(
    target="src/",
    since="2024-01-01T00:00:00Z",  # ISO 8601 timestamp
)
```

Perfect for CI/CD pipelines (10x faster than full scan).

### Dry-Run Safety

Preview fixes before applying them:

```python
request = AuditRequest(
    target="src/",
    enable_auto_fix=True,  # Generate fixes
    apply_auto_fix=True,    # Apply to files
    dry_run=True,        # Safety: don't actually modify
)
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target` | string | Yes | - | File or directory path to audit |
| `scan_categories` | list[string] | No | All 24 categories | Categories to scan |
| `severity_threshold` | string | No | "medium" | Filter by severity: low, medium, high, critical |
| `entropy_threshold` | float | No | 4.5 | Entropy threshold for secrets detection |
| `include_comments` | bool | No | false | Include comments for tag detection |
| `max_file_size_kb` | int | No | 1024 | Max file size (max 5000) |
| `files` | list[string] | No | - | Specific files to audit |
| `output_format` | string | No | "json" | Output format: json, csv, report |
| `use_ast` | bool | No | true | Use cached AST for accuracy |
| `use_aiignore` | bool | No | true | Read .aiignore for exclusions |
| `repository_id` | string | No | - | Repository UUID for persistence |
| `since` | string | No | - | ISO 8601 timestamp for incremental scan |
| `enable_auto_fix` | bool | No | false | Generate auto-fix suggestions |
| `apply_auto_fix` | bool | No | false | Apply auto-fixes to files (DANGEROUS) |
| `dry_run` | bool | No | true | Safety mode - don't modify files even with apply_auto_fix=true |

## Output

### Result Structure

```json
{
  "target": "/path/to/code",
  "scan_categories": ["secrets", "pii", "vulns"],
  "scanned_files": 150,
  "compliance_score": 85,
  "summary": {
    "critical": 2,
    "high": 5,
    "medium": 12,
    "low": 8
  },
  "findings": [
    {
      "category": "secrets",
      "severity": "critical",
      "file": "src/config.py",
      "line": 45,
      "column": 20,
      "code": "CA_SEC_001",
      "message": "Hardcoded API key detected",
      "details": {
        "entropy": 6.2,
        "line_content": "API_KEY = 'sk-1234567890'"
      },
      "context": "API_KEY = 'sk-1234567890'",
      "confidence": 0.95,
      "remediation": "Move to environment variable",
      "standard_ref": "security-standard (Secrets)",
      "auto_fix_available": false,
      "auto_fix_code": null,
      "auto_fix_description": "",
      "fix_applied": false,
      "fix_diff": null
    }
  ],
  "recommendations": {
    "gitignore_entries": ["config.py"],
    "secrets_to_rotate": ["config.py"]
  },
  "errors": []
}
```

### Auto-Fix Fields

Each finding may include auto-fix information:

- `auto_fix_available` — Whether an automated fix is possible
- `auto_fix_code` — The fix code/snippet
- `auto_fix_description` — Description of what the fix does
- `fix_applied` — Whether fix was applied
- `fix_diff` — Unified diff of the fix

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| CA_020 | high | Target is required for audit |
| CA_021 | high | Invalid category name |
| CA_500 | critical | Internal error |

## Examples

### Basic Audit

```python
# Full audit with all categories
result = code_audit(target="src/")

# Audit specific categories
result = code_audit(
    target="src/",
    scan_categories=["secrets", "pii", "vulns"],
    severity_threshold="high",
)
```

### Incremental Scan

```python
# Only scan files modified since date
result = code_audit(
    target="src/",
    since="2024-01-01T00:00:00Z",
)
```

### Auto-Fix Generation

```python
# Generate auto-fix suggestions
result = code_audit(
    target="src/",
    enable_auto_fix=True,
    dry_run=True,  # Preview only
)

# Review auto-fixes
for finding in result.findings:
    if finding.auto_fix_available:
        print(f"Auto-fix: {finding.fix_diff}")
```

### Apply Auto-Fixes

```python
# Apply fixes (DANGEROUS - use with caution)
result = code_audit(
    target="src/",
    enable_auto_fix=True,
    apply_auto_fix=True,
    dry_run=False,  # Actually modify files
)
```

## Performance

- **Incremental Scanning** — 10x faster for CI/CD
- **AST Caching** — Reuse parsed AST for performance
- **Parallel File Processing** — Concurrent file analysis
- **Smart Caching** — Query hash-based cache with TTL

## Security

- **Path Validation** — Traversal prevention
- **Entropy Detection** — Identify potential secrets
- **.aiignore Support** - Exclude patterns
- **Dry-Run Safety** - Preview before applying changes

## See Also

- [Analyze Tool](../sub-features/code_analyze/concept.md)
- [Search Tool](../sub-features/code_search/concept.md)
- [Status Tool](../sub-features/code_status/concept.md)
