# repo_audit: Multi-Layer Security Audit

> **Tool:** repo_audit
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Purpose

Multi-layer security audit — secrets detection (API keys, tokens), PII scanning, misconfig detection, vulnerability patterns (SQL injection, weak crypto), sensitive files, git history scanning, and dependency analysis. Optional LLM validation with confidence scoring.

## Why This Exists

- **Security Gate:** Scans codebase for security vulnerabilities and secrets
- **Secrets Detection:** Finds hardcoded API keys, tokens, passwords
- **PII Scanning:** Identifies personally identifiable information
- **Vulnerability Patterns:** Detects SQL injection, eval, unsafe yaml.load
- **Git History:** Scans commit history for leaked secrets
- **AI Validation:** Optional LLM-based validation with confidence scores

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to repository |
| `detect_secrets` | bool | ❌ | `true` | Scan for hardcoded secrets |
| `include_git_history` | bool | ❌ | `true` | Scan commit history for secrets |
| `use_llm_validation` | bool | ❌ | `false` | Use LLM for pattern validation |
| `output_format` | string | ❌ | `json` | "json" or "markdown" |

## Output

```json
{
  "repo_id": "uuid-v7",
  "repo_path": "/absolute/path",
  "findings": [
    {
      "category": "secrets",
      "severity": "critical",
      "file": "config.py",
      "line": 10,
      "message": "Hardcoded AWS access key detected",
      "code": "CA_SEC_001"
    }
  ],
  "summary": {
    "critical": 1,
    "high": 3,
    "medium": 5,
    "low": 10
  },
  "ai_actions": [
    {
      "priority": "critical",
      "action": "1 CRITICAL secret found. Remove immediately.",
      "command_hint": "repo_audit --repo_path /absolute/path --detect_secrets=true"
    }
  ]
}
```

## AI Actions

1. **Critical Alerts** — Immediate action for critical findings
2. **High Priority** — Security concerns requiring attention
3. **Remediation Commands** — Direct commands for fixing issues
4. **Next Steps** — Suggests re-audit after fixes

## Error Codes

| Code | Severity | Condition |
|------|----------|-----------|
| REP_404 | 404 | Repository not indexed |
| REP_500 | 500 | Audit failed |

## Integration

- **repo_init** — For audit during initialization (run_audit=true)
- **repo_history** — For commit history secret scanning
- **code_audit** — For code-level compliance checks
