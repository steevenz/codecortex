"""
Mixin for security hardening: SSRF protection and path guards.

:project: CodeCortex
:package: Modules.Codegraph.Services.Mixins.Security
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

import ipaddress
import re
import socket
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


_ALLOWED_SCHEMES = frozenset({"http", "https"})
_BLOCKED_HOSTS = frozenset({
    "169.254.169.254",  # AWS/GCP/Azure metadata
    "metadata.google.internal",
    "100.100.100.200",  # Alibaba Cloud
})


class ArchitecturalSecurityMixin:
    """Mixin for security hardening: SSRF protection and path guards."""

    def validate_url(self, url: str) -> str:
        """Raise ValueError if *url* is not http or https, or targets a private/internal IP."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            raise ValueError(f"Blocked URL scheme '{parsed.scheme}' - only http and https are allowed.")

        hostname = parsed.hostname
        if hostname:
            if hostname.lower() in _BLOCKED_HOSTS:
                raise ValueError(f"Blocked cloud metadata endpoint '{hostname}'.")

            try:
                infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                for info in infos:
                    addr = info[4][0]
                    ip = ipaddress.ip_address(addr)
                    if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
                        raise ValueError(f"Blocked private/internal IP {addr} (resolved from '{hostname}').")
            except socket.gaierror as exc:
                raise ValueError(f"DNS resolution failed for '{hostname}': {exc}.") from exc

        return url

    def validate_safe_path(self, path: Union[str, Path], base: Path) -> Path:
        """Resolve *path* and verify it stays inside *base*."""
        base = base.resolve()
        resolved = Path(path).resolve()
        try:
            resolved.relative_to(base)
        except ValueError:
            raise ValueError(f"Path {path!r} escapes the allowed directory {base}.")
        return resolved

    def sanitize_label(self, text: Optional[str]) -> str:
        """Strip control characters and cap length."""
        if text is None:
            return ""
        # Strip control characters
        text = re.sub(r"[\x00-\x1f\x7f]", "", str(text))
        if len(text) > 256:
            text = text[:256]
        return text

    def _audit_security_hygiene(self, repo_id: str) -> List[Dict]:
        """Scan for sensitive patterns or missing masks in the graph.
        
        Note: requires 'self.db' to be available on the inheriting class.
        """
        patterns = ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]
        results = []
        seen_ids: set = set()

        for p in patterns:
            # 1. Fast path: name match (uses index on symbols.name)
            cursor = self.db.conn.execute("""
                SELECT s.id, s.name, d.relative_path, s.start_line, s.symbol_type
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                JOIN directories d ON f.directory_id = d.id
                WHERE s.repository_id = ? AND s.name LIKE ?
            """, (repo_id, f"%{p}%"))
            for row in cursor.fetchall():
                sid = row["id"]
                if sid not in seen_ids:
                    seen_ids.add(sid)
                    results.append(dict(row))

            # 2. Slower path: code match only for Variable / Function
            if seen_ids:
                placeholders = ",".join(["?"] * len(seen_ids))
                code_sql = f"""
                    SELECT s.id, s.name, d.relative_path, s.start_line, s.symbol_type
                    FROM symbols s
                    JOIN files f ON s.file_id = f.id
                    JOIN directories d ON f.directory_id = d.id
                    WHERE s.repository_id = ?
                      AND s.symbol_type IN ('variable', 'function', 'method')
                      AND s.code LIKE ?
                      AND s.id NOT IN ({placeholders})
                """
                code_params = (repo_id, f"%{p}%") + tuple(seen_ids)
            else:
                code_sql = """
                    SELECT s.id, s.name, d.relative_path, s.start_line, s.symbol_type
                    FROM symbols s
                    JOIN files f ON s.file_id = f.id
                    JOIN directories d ON f.directory_id = d.id
                    WHERE s.repository_id = ?
                      AND s.symbol_type IN ('variable', 'function', 'method')
                      AND s.code LIKE ?
                """
                code_params = (repo_id, f"%{p}%")
            
            cursor = self.db.conn.execute(code_sql, code_params)
            for row in cursor.fetchall():
                sid = row["id"]
                if sid not in seen_ids:
                    seen_ids.add(sid)
                    results.append(dict(row))

        return results
