# CodeCortex Security Reference

## Scope

Security utilities are centralized in `src/domain/codegraph/core/security.py`. They provide SSRF prevention, path traversal guards, and label sanitization. These utilities are exposed as MCP tools and are safe to invoke from any agent context.

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

## Usage in Production

- Always wrap external URL inputs with `validate_url()` before any HTTP call.
- Always pass user-provided file paths through `validate_graph_path()` before reading/writing.
- Never pass raw graph labels to HTML templates — use `escape_html_label()`.
- Security guards are enforced at the domain level in `CodeGraphService` for all graph operations.
