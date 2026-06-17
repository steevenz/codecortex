# Security Filter

> **Package:** `src/services/security_filter.py`
> **Class:** `SecurityFilter`
> **Version:** 1.0.0
> **Severity Levels:** 4 (critical, high, medium, low)
> **Vulgar Detection:** Always-block (never shown)

## Why It Exists

The SecurityFilter protects AI agents and users from accidentally accessing or displaying sensitive information during code search and file operations. It replaces the previous bare-path-validation approach with a comprehensive 3-layer pipeline:

1. **File-level guards** — reject sensitive files by name/extension/path substring
2. **Content-level analysis** — detect and mask/block sensitive data within file contents
3. **Vulgar content detection** — always block inappropriate content (never masked)

Without SecurityFilter, sensitive files (`.env`, `.key`, `secrets.yml`) or content (passwords, tokens, API keys) could leak through filesystem search or knowledge retrieval directly into AI agent context.

## Parameters

### SecurityFilter Constructor

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `project_root` | string | no | `None` | Project root for relative path resolution |
| `strict_mode` | bool | no | `false` | Override env var; block vs mask |

### check_file()

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file_path` | string | yes | — | Absolute path to the file |
| `content` | string | no | `None` | File content to analyze |
| `rel_path` | string | no | `None` | Override relative path for ignore rules |

### process_content()

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | yes | — | Content to analyze |

## Output Format (check_file)

```json
{
  "allowed": true,
  "content_action": "mask",
  "masked_content": "***MASKED***",
  "reasons": ["Sensitive content masked"],
  "details": {
    "content": ["Password assignment (password) [medium]"],
    "file": ["Sensitive extension (.env)"]
  }
}
```

**Fields:**
- `allowed` — whether the file can be included in search results
- `content_action` — `"allow"` / `"mask"` / `"block"`
- `masked_content` — masked version if `action="mask"`, else `None`
- `reasons` — human-readable summary of why the file was affected
- `details` — structured breakdown by category (file, content, path)

## Output Format (process_content)

```json
{
  "action": "mask",
  "text": "***MASKED***",
  "severity": "medium",
  "matches": [
    {"pattern": "password", "severity": "medium", "match": "password = \"***\""}
  ]
}
```

**Fields:**
- `action` — `"allow"` / `"mask"` / `"block"`
- `text` — processed text (masked or empty if blocked)
- `severity` — highest severity found (`low`/`medium`/`high`/`critical`)
- `matches` — all matched patterns with severity and masked content

## Algorithm

### Layer 1: File Path Validation

```
check_file(path, content):
  ├── resolve absolute path
  ├── reject if path traversal (.. or outside project_root)
  ├── reject if sensitive file extension (.env, .key, .pem, etc.)
  ├── reject if sensitive exact name (id_rsa, .npmrc, .gitconfig)
  ├── reject if sensitive path substring (/secret/, /credentials/)
  ├── check .gitignore / .aiignore (loaded via load_ignore_files)
  │     if ignored → return { allowed: false }
  └── if content provided → process_content(content)
```

### Layer 2: Content Analysis (process_content)

```
process_content(text):
  ├── vulgar content check (always first)
  │     └── if vulgar detected → return { action: "block", text: "" }
  ├── iterate 41 sensitive patterns (ordered by severity)
  │     ├── each pattern: (regex, severity, label)
  │     ├── on match:
  │     │     ├── collect match info (severity, label, masked snippet)
  │     │     └── replace match with *** in text copy
  │     └── continue scanning (all matches reported)
  ├── if any matches:
  │     ├── non-strict → return { action: "mask", masked_text }
  │     └── strict     → return { action: "block", text: "" }
  └── if no matches → return { action: "allow", text }
```

## Sensitive Patterns (41 Total)

| Severity | Count | Examples |
|----------|-------|---------|
| **Critical** | 9 | AWS secret key, GitHub token, JWT, PKI private key, SSH private key, npm auth token, nuget API key, Git credential, Slack token |
| **High** | 15 | Generic password, connection string, hashed password, SSL certificate, Facebook token, Twitter token, Google API key, Heroku API key, MailChimp API key, Mailgun API key, PayPal token, AWS access key, Azure connection string, Docker config, Kubernetes secret |
| **Medium** | 14 | Password assignment, API key, secret variable, token variable, credential variable, auth header, bearer token, basic auth, session cookie, database URL, MongoDB URI, Redis URL, encryption key, private key var |
| **Low** | 3 | Secret file path reference, key file reference, credential file import |

## Sensitive File Detection

**By Extension (18 extensions):**
`.env`, `.env.*`, `.secret`, `.secrets`, `.key`, `.pem`, `.p12`, `.pfx`, `.jks`, `.keystore`, `.crt`, `.cert`, `.csr`, `.ovpn`, `.kubeconfig`, `.netrc`, `.npmrc`, `.yaml` / `.yml` in combination with sensitive names

**By Exact Name (50+ names):**
`id_rsa`, `id_dsa`, `config.yml`/`yaml` containing `secret` parent, `.npmrc`, `.gitconfig`, `.git-credentials`, `.docker/config.json`, `credentials.yml`, `.env.example`, `secrets.yml`, `sensitive.py`, `settings.py` in `secret/` folder

**By Path Substring (7 substrings):**
`/secret/`, `/secrets/`, `/credentials/`, `/keys/`, `/certificates/`, `/vault/`, `/password/`

## Vulgar Pattern (1)

Always blocked, never masked. If detected, the entire content is excluded from search results.

- `vulgar_content` — matches NSFW, explicit, or inappropriate content

## Environment Configuration

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `CODECORTEX_SECURITY_STRICT` | `true` / `false` | `false` | `false` = mask sensitive content; `true` = block all sensitive content |

## Use Cases

| Scenario | Mode | Result |
|----------|------|--------|
| Search finds `.env` file | Default | File excluded entirely (sensitive extension) |
| Search finds `password = "admin123"` in settings.py | Default | File included, content masked as `password = "***"` |
| Search finds `password = "admin123"` in settings.py | Strict | File excluded entirely |
| Search finds NSFW text in README.md | Any | File excluded entirely (vulgar, never shown) |
| Search finds safe Python code | Any | File included, content unchanged |
| Agent reads `.gitconfig` via filesystem tool | Default | File excluded (sensitive name) |

## Error Cases

| Condition | Behavior |
|-----------|----------|
| Traversal attempt (`../`) | Blocked with `Path traversal` reason |
| Missing project_root | All paths allowed relative to CWD |
| Invalid regex in patterns | Pattern skipped with log warning |
| .gitignore parse error | Continues without that rule |
| Content None | File-level checks only (no content analysis) |

## Integration Points

| Location | Usage |
|----------|-------|
| `unified_search.py:_search_filesystem()` | Each file read passes through `check_file()` |
| `unified_search.py:_search_repowt()` | Git status results checked via `check_file()` |
| `unified_search.py:_search_knowledge()` | Knowledge chunk text via `process_content()` |
| `unified_search.py:_search_agentart()` | .agents artifacts via `check_file()` + `process_content()` |

---

*This document follows CODDY Codeworks documentation standards.*
