"""
URL security guards — SSRF prevention, URL validation, safe HTTP fetching,
and path traversal validation for graph files.

:project: CodeCortex
:package: Core.Security.Url_security
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

import contextlib
import html
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Generator

_ALLOWED_SCHEMES = {"http", "https"}
_MAX_FETCH_BYTES = 52_428_800   # 50 MB
_MAX_TEXT_BYTES = 10_485_760    # 10 MB
_BLOCKED_HOSTS = {"metadata.google.internal", "metadata.google.com"}

# ── URL Validation ────────────────────────────────────────────────────

def validate_url(url: str) -> str:
    """Validate a URL for SSRF safety.

    Blocks:
    - Non-HTTP/HTTPS schemes
    - Cloud metadata endpoints
    - Private, reserved, loopback, and link-local IPs

    Returns the URL unchanged if valid, raises ValueError otherwise.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"Blocked scheme '{parsed.scheme}'; only http/https allowed. Got: {url!r}"
        )
    hostname = parsed.hostname
    if hostname:
        if hostname.lower() in _BLOCKED_HOSTS:
            raise ValueError(
                f"Blocked cloud metadata endpoint '{hostname}'. Got: {url!r}"
            )
        try:
            infos = socket.getaddrinfo(
                hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
            for info in infos:
                addr = info[4][0]
                ip = ipaddress.ip_address(addr)
                if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
                    raise ValueError(
                        f"Blocked private IP {addr} from '{hostname}'. Got: {url!r}"
                    )
        except socket.gaierror as exc:
            raise ValueError(
                f"DNS failed for '{hostname}': {exc}. Got: {url!r}"
            ) from exc
    return url

# ── SSRF Socket Guard ──────────────────────────────────────────────────

@contextlib.contextmanager
def ssrf_guarded_socket() -> Generator[None, None, None]:
    """Context manager that patches ``socket.getaddrinfo`` to block SSRF.

    Yields with the guard active; restores original on exit.
    """
    original = socket.getaddrinfo

    def guarded(host, port, *args, **kwargs):
        results = original(host, port, *args, **kwargs)
        for info in results:
            addr = info[4][0]
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
                raise OSError(
                    f"SSRF blocked: {addr} from '{host}' is private/reserved"
                )
        return results

    socket.getaddrinfo = guarded
    try:
        yield
    finally:
        socket.getaddrinfo = original

# ── Safe HTTP Fetching ─────────────────────────────────────────────────

class _NoFileRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def _build_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_NoFileRedirectHandler)

def safe_fetch(url: str, max_bytes: int = _MAX_FETCH_BYTES, timeout: int = 30) -> bytes:
    """Fetch a URL with SSRF protection and size limit.

    Args:
        url: The URL to fetch (http/https only).
        max_bytes: Maximum bytes to read (default 50 MB).
        timeout: Connection timeout in seconds.

    Returns:
        Response body as bytes.
    """
    validate_url(url)
    opener = _build_opener()
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 codecortex/1.0"}
    )
    with ssrf_guarded_socket(), opener.open(req, timeout=timeout) as resp:
        status = getattr(resp, "status", None) or getattr(resp, "code", None)
        if status is not None and not (200 <= status < 300):
            raise urllib.error.HTTPError(url, status, f"HTTP {status}", {}, None)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = resp.read(65_536)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise OSError(
                    f"Response exceeds size limit ({max_bytes // 1_048_576} MB)."
                )
            chunks.append(chunk)
    return b"".join(chunks)

def safe_fetch_text(url: str, max_bytes: int = _MAX_TEXT_BYTES, timeout: int = 15) -> str:
    """Fetch a URL and return its body as text (UTF-8, lossy decode).

    Args:
        url: The URL to fetch.
        max_bytes: Maximum bytes to read (default 10 MB).
        timeout: Connection timeout in seconds.

    Returns:
        Response body as a string.
    """
    raw = safe_fetch(url, max_bytes=max_bytes, timeout=timeout)
    return raw.decode("utf-8", errors="replace")

# ── Graph Path Validation ─────────────────────────────────────────────

def validate_graph_path(path: str | Path, base: Path | None = None) -> Path:
    """Validate that a graph file path is within the allowed base directory.

    Args:
        path: The graph file path to validate.
        base: The allowed base directory. Auto-detects ``codecortex-out`` if None.

    Returns:
        Resolved Path if valid.

    Raises:
        ValueError: If the path escapes the base directory.
        FileNotFoundError: If the file does not exist.
    """
    if base is None:
        resolved_hint = Path(path).resolve()
        for candidate in [resolved_hint, *resolved_hint.parents]:
            if candidate.name == "codecortex-out":
                base = candidate
                break
        if base is None:
            base = Path("codecortex-out").resolve()
    base = base.resolve()
    if not base.exists():
        raise ValueError(f"Graph base directory does not exist: {base}")
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(f"Path {path!r} escapes allowed directory {base}.")
    if not resolved.exists():
        raise FileNotFoundError(f"Graph file not found: {resolved}")
    return resolved

# ── Text Sanitisation ──────────────────────────────────────────────────

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_MAX_LABEL_LEN = 256

def sanitize_label(text: str | None) -> str:
    """Strip control characters and truncate to 256 chars."""
    if text is None:
        return ""
    text = _CONTROL_CHAR_RE.sub("", str(text))
    if len(text) > _MAX_LABEL_LEN:
        text = text[:_MAX_LABEL_LEN]
    return text

def escape_html_label(text: str | None) -> str:
    """HTML-escape a label after sanitisation."""
    return html.escape(sanitize_label(text))
