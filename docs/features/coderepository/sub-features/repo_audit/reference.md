# repo_audit — Multi-Layer Security Audit

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-25

## Overview

`repo_audit` performs **deep security auditing** using multi-layer scanning:

1. **Rule-based** — regex pattern matching for secrets, PII, misconfigs, vulnerabilities
2. **Sensitive files** — detects .env, .pem, .key, credentials.json, etc.
3. **VCS history** — scans git log for secrets committed in the past
4. **Dependency scan** — detects package managers and manifest files

**Difference from `fs_audit`**: `fs_audit` scans file **metadata only** (names, permissions, size). `repo_audit` reads file **contents** and scans for security patterns.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to the repository |
| `scan_categories` | array | ❌ | `["secrets","pii","misconfig","vulns"]` | Categories to scan |
| `detect_secrets` | boolean | ❌ | `true` | Secret detection (AWS keys, tokens, passwords) |
| `detect_pii` | boolean | ❌ | `false` | PII detection (email, phone, SSN, credit card) |
| `detect_misconfig` | boolean | ❌ | `true` | Misconfig detection (debug, wildcard CORS, CI/CD secrets) |
| `detect_vuln_patterns` | boolean | ❌ | `true` | Vulnerability patterns (SQL injection, command injection) |
| `detect_weak_crypto` | boolean | ❌ | `true` | Weak crypto detection (MD5, SHA1) |
| `detect_sensitive_files` | boolean | ❌ | `true` | Sensitive file detection (.env, .pem, .key) |
| `exclude_patterns` | array | ❌ | `["node_modules","__pycache__","dist","build","venv","env",".git",".svn"]` | Directories to ignore |
| `include_git_history` | boolean | ❌ | `true` | Scan git history for secrets |
| `use_llm_validation` | boolean | ❌ | `false` | Validate findings with LLM (requires API key) |
| `llm_model` | string | ❌ | `"claude-3.5-sonnet"` | LLM model for validation |
| `max_workers` | integer | ❌ | `4` | Parallel workers for file scanning |
| `max_file_size_kb` | integer | ❌ | `1024` | Skip files larger than this |
| `timeout_seconds` | integer | ❌ | `600` | Max execution time (10 min) |
| `output_format` | string | ❌ | `"json"` | `"json"` or `"markdown"` |

## Detection Patterns

### Secrets (10 patterns)

| Pattern | Type | Severity |
|---------|------|----------|
| `AKIA[0-9A-Z]{16}` | AWS Access Key | Critical |
| `aws_secret_access_key = "..."` | AWS Secret Key | Critical |
| `ghp_[A-Za-z0-9]{36}` | GitHub Token | Critical |
| `sk_live_...` | Stripe Live Key | Critical |
| `xox[baprs]-...` | Slack Token | High |
| `AIza...` | Google API Key | High |
| `-----BEGIN ... PRIVATE KEY-----` | Private Key | Critical |
| `password = "..."` | Hardcoded Password | High |
| `mongodb://user:pass@host` | Connection String | Critical |
| `eyJ...` | JWT Token | High |

### Sensitive Files

| Pattern | Severity |
|---------|----------|
| `.env`, `.env.*` | Critical |
| `*.pem`, `*.key`, `*.p12` | Critical |
| `credentials.json`, `secrets.yml` | Critical |
| `*.sqlite`, `*.db` | High |
| `*.log` | Low |

### Vulnerabilities

| Pattern | Severity |
|---------|----------|
| SQL Injection | Critical |
| Command Injection | Critical |
| `eval()` usage | High |
| `pickle.load()` | High |
| `yaml.load()` (no SafeLoader) | Medium |
| MD5/SHA1 usage | Medium |

## Flow (7 Phases)

```
PHASE 0: Validate path, detect VCS type
PHASE 1: File discovery (os.walk, extension filter)
PHASE 2: Multi-layer scanning (rule-based for secrets, PII, misconfig, vulns, weak crypto)
PHASE 3: Sensitive files detection (.env, *.pem, *.key, etc.)
PHASE 4: VCS history scanning (git log -p)
PHASE 5: Dependency scanning (package.json, requirements.txt, go.mod, etc.)
PHASE 6: Aggregate & deduplicate findings
PHASE 7: Generate recommendations & response
```

## Response

### Success

```json
{
  "success": true,
  "message": "Repository security audit completed",
  "data": {
    "repo_path": "/home/user/project",
    "duration_seconds": 4.5,
    "scanned_files": 187,
    "summary": {
      "total_findings": 12,
      "by_severity": {"critical": 1, "high": 3, "medium": 5, "low": 3},
      "by_category": {"secrets": 3, "pii": 1, "misconfig": 2, "vulns": 6}
    },
    "findings": {
      "secrets": [{
        "file": "config/app.yml", "line": 12, "severity": "critical",
        "type": "aws_access_key", "value": "AKIAIOSFODNN7EXAMPLE",
        "context": "aws_access_key: AKIAIOSFODNN7EXAMPLE",
        "remediation": "Rotate key immediately. Use AWS Secrets Manager.",
        "confidence": 85
      }]
    },
    "git_history_findings": {
      "enabled": true, "total_commits_scanned": 100,
      "findings": [{"commit": "a1b2c3d", "category": "secrets", "value": "AKIA..."}]
    },
    "dependency_scan": {
      "package_managers": ["npm", "pip"],
      "manifests_found": [{"type": "npm", "file": "package.json"}]
    },
    "recommendations": {
      "secrets_to_rotate": ["AKIA... (aws_access_key in config/app.yml:12)"],
      "gitignore_entries": [".env"],
      "files_to_remove": [".env.production"],
      "code_changes": ["sql_injection: src/query.py:32 → Use parameterized queries"]
    }
  }
}
```

### Error

```json
{
  "success": false,
  "status_code": 404,
  "message": "Repository path does not exist",
  "data": {"repo_path": "/invalid/path"}
}
```

## Integration

| Tool | Role |
|------|------|
| `fs_audit` | Lightweight metadata-only alternative |
| `code_audit` | Lightweight content scanning (subset of repo_audit rules) |
| `repo_analyze` | Full AST/graph analysis (complementary) |
| `repo_inspect` | Fast health check (complementary) |
