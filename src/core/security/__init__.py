"""
Core security package — URL validation, SSRF guards, text sanitisation.

:project: CodeCortex
:package: Core.Security
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from .url_security import (
    validate_url,
    ssrf_guarded_socket,
    safe_fetch,
    safe_fetch_text,
    validate_graph_path,
    sanitize_label,
    escape_html_label,
)

__all__ = [
    "validate_url",
    "ssrf_guarded_socket",
    "safe_fetch",
    "safe_fetch_text",
    "validate_graph_path",
    "sanitize_label",
    "escape_html_label",
]
