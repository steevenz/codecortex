# Git Audit

> **Source:** `GitService.git_audit()`

## Concept

Git audit scans commit history for hardcoded secrets: API keys, passwords, private keys, AWS credentials, GitHub tokens, and connection strings.

## Detection Patterns

| Pattern | Risk | Example |
|---------|------|---------|
| API Key (alphanumeric 32+ chars) | High | `sk_live_abc123...` |
| AWS Access Key | Critical | `AKIAIOSFODNN7EXAMPLE` |
| Private Key | Critical | `-----BEGIN RSA PRIVATE KEY-----` |
| GitHub Token | Critical | `ghp_xxxxxxxxxxxx` |
| Connection String | High | `postgres://user:pass@host/db` |
| Password Assignment | Medium | `password = "secret123"` |

## Output

```json
{
  "findings": [
    {
      "type": "hardcoded_api_key",
      "file": "src/config.py:15",
      "commit": "abc123def",
      "author": "dev@example.com",
      "date": "2026-05-01",
      "risk": "high",
      "snippet": "API_KEY = \"sk-...\""
    }
  ],
  "total_findings": 3,
  "commits_scanned": 100
}
```

## Usage

```bash
codecortex --git-audit /path/to/repo --limit 500
```

## Limits

- Default: last 100 commits scanned
- Configurable via `limit` parameter
- Scans diffs, not file snapshots — finds only introduced secrets
