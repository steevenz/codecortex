"""
Security guards — SSRF prevention, path traversal, label sanitisation.

:project: CodeCortex
:package: Modules.Codegraph.Core.Security
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

from src.core.security import (  # noqa: F401
    validate_url,
    ssrf_guarded_socket,
    safe_fetch,
    safe_fetch_text,
    validate_graph_path,
    sanitize_label,
    escape_html_label,
)
