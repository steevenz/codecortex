# CodeCortex Security Reference

## Scope

CodeCortex has two security layers:

1. **Domain Security** (`src/domain/codegraph/core/security.py`) — SSRF prevention, path traversal guards, label sanitization. Exposed as MCP tools.
2. **Service Security** (`src/services/security_filter.py`) — Sensitive file/content detection, content masking, vulgar detection, .gitignore/.aiignore parsing. Integrated into all file-accessing search providers.

Both layers are safe to invoke from any agent context.

## Modules

### `validate_url(url: str) -> str`

**Threat Model**: Server-Side Request Forgery (SSRF), cloud metadata exfiltration.

**Checks**:
1. Scheme whitelist — only `http`, `https`.
2. Blocked host list — `metadata.google.internal`, `metadata.google.com`.
3. DNS resolution + IP validation — rejects `private`, `reserved`, `loopback`, `link-local` IPs.

**Raises**: `ValueError` with descriptive message on violation.

```python
from src.domain.codegraph.core.security import validate_url
validate_url("http://169.254.169.254/latest/meta-data/")
# ValueError: Blocked private IP 169.254.169.254 ...
```

### `safe_fetch(url, max_bytes=52_428_800, timeout=30) -> bytes`

Layered protections:
1. Calls `validate_url()` upfront.
2. SSRF-guarded `socket.getaddrinfo()` context manager — re-validates every DNS resolution during the request lifecycle.
3. Custom `HTTPRedirectHandler` — re-validates redirect targets.
4. Streaming read with byte cap — aborts if response exceeds `max_bytes` (default 50 MB).

```python
from src.domain.codegraph.core.security import safe_fetch
raw = safe_fetch("https://example.com/config.json", max_bytes=1_048_576)
```

### `safe_fetch_text(url, max_bytes=10_485_760, timeout=15) -> str`

Convenience wrapper around `safe_fetch()` that decodes UTF-8 with replacement characters for invalid bytes.

### `validate_graph_path(path, base=None) -> Path`

**Threat Model**: Path traversal / directory escape.

**Logic**:
1. Resolves `base` (defaults to `graphify-out/`).
2. Resolves `path`.
3. Checks `path.relative_to(base)` — raises `ValueError` if escape detected.
4. Verifies file exists — raises `FileNotFoundError` if missing.

```python
from src.domain.codegraph.core.security import validate_graph_path
validate_graph_path("report.json", base="/safe/output")
# Path('/safe/output/report.json')
```

### `sanitize_label(text) -> str`

Strips control characters (`\x00-\x1f`, `\x7f`) and truncates to 256 chars. Used for graph node/edge label safety.

### `escape_html_label(text) -> str`

Applies `html.escape()` after `sanitize_label()`. Use before embedding graph labels into HTML reports.

## MCP Tool Exposure

Security utilities are registered as MCP tools in `src/domain/codegraph/api/tools.py`:

| Tool | Function | Input |
|------|----------|-------|
| `validate_url_safe` | `validate_url()` | `url: str` |
| `validate_graph_path_safe` | `validate_graph_path()` | `path: str`, `base_path: str` (optional) |
| `sanitize_graph_label` | `sanitize_label()` | `text: str` |

## Service Security: SecurityFilter

**Package:** `src/services/security_filter.py`

`SecurityFilter` provides content-level security for all file-accessing search operations. It is not exposed as a standalone MCP tool — instead, it is embedded within `UnifiedSearchEngine` providers that read file content.

### Key Capabilities

| Capability | Description |
|-----------|-------------|
| **Sensitive file detection** | 18 sensitive extensions + 50+ exact filenames — always blocked |
| **Sensitive content masking** | 41 regex patterns across 4 severity levels — masked in default mode |
| **Vulgar content blocking** | Always blocked, never shown to agent |
| **Strict mode toggle** | `CODECORTEX_SECURITY_STRICT=true` blocks all sensitive content |
| **Ignore file parsing** | `.gitignore` / `.aiignore` rule loading and glob matching |

### Integration Points

| Provider | Integration | Method |
|----------|------------|--------|
| `UnifiedSearch._search_filesystem()` | Per-file check | `check_file(path, content)` |
| `UnifiedSearch._search_repowt()` | Git status filter | `check_file(path)` |
| `UnifiedSearch._search_knowledge()` | Chunk content filter | `process_content(text)` |
| `UnifiedSearch._search_agentart()` | Per-file check | `check_file()` + `process_content()` |

### 3-Layer Pipeline

```
check_file(path, content)
  │
  ├── Layer 1: Path Validation
  │     ├── traversal prevention (.. / outside project root)
  │     ├── sensitive extension match (.env, .key, .pem, ...)
  │     ├── sensitive exact name match (id_rsa, .npmrc, ...)
  │     ├── sensitive path substring (/secret/, /credentials/)
  │     └── .gitignore / .aiignore rule matching
  │
  ├── Layer 2: Vulgar Detection (always first)
  │     └── if vulgar content → block entirely, never shown
  │
  └── Layer 3: Sensitive Content Analysis
        ├── 41 regex patterns matched against file text
        ├── non-strict → mask matches with ***MASKED***
        └── strict     → block entire file
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CODECORTEX_SECURITY_STRICT` | `false` | `false` = mask sensitive content; `true` = block entirely |

### Behavior Matrix

| Content Type | Default Mode | Strict Mode |
|-------------|-------------|-------------|
| Safe code | Allowed | Allowed |
| Password / API key | Masked (`***MASKED***`) | Blocked |
| .env file | Blocked (file-level) | Blocked |
| NSFW / vulgar | Blocked | Blocked |

Full reference: [Security Filter](../features/unified-search/sub-features/security-filter/concept.md)

## Usage in Production

- Always wrap external URL inputs with `validate_url()` before any HTTP call.
- Always pass user-provided file paths through `validate_graph_path()` before reading/writing.
- Never pass raw graph labels to HTML templates — use `escape_html_label()`.
- Security guards are enforced at the domain level in `CodeGraphService` for all graph operations.
- `SecurityFilter` is automatically active in every UnifiedSearch provider — no manual invocation needed.
- Set `CODECORTEX_SECURITY_STRICT=true` in environments where no sensitive data should reach the AI agent.
