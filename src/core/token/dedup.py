"""
Context Deduplication — prevents duplicate content across tool responses.

Uses content fingerprinting (SHA-256) to detect and suppress redundant
information. Operates at two levels:
1. Intra-response: dedup within a single result set
2. Inter-response: dedup across multiple tool calls (session-scoped)

:project: CodeCortex
:package: Core.Token.Dedup
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import hashlib
import threading
from typing import Any, Dict, List, Optional, Set

# Session-scoped seen fingerprints (thread-safe)
_seen_fingerprints: Dict[str, Set[str]] = {}
_seen_lock = threading.Lock()


def _normalize(text: str) -> str:
    """Normalize content for fingerprinting: strip whitespace, lowercase."""
    return " ".join(text.lower().split())


def fingerprint(content: str) -> str:
    """SHA-256 fingerprint of normalized content."""
    return hashlib.sha256(_normalize(content).encode("utf-8")).hexdigest()


def fingerprint_dict(item: Dict[str, Any], *keys: str) -> str:
    """Fingerprint a dict by concatenating specified key values."""
    parts = []
    for k in keys:
        v = item.get(k)
        if v is not None:
            parts.append(str(v))
    return fingerprint("|".join(parts))


class ContextDedup:
    """Content deduplication with intra-response and session-scoped modes.

    Usage:
        dedup = ContextDedup(session_id="conv_123")

        # Within a single response
        unique = dedup.dedup_list(results, keys=["name", "file"])

        # Across responses
        if dedup.is_new(content_fp):
            # process new content
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or "default"

    # ── Intra-response dedup ─────────────────────────────

    def dedup_list(
        self,
        items: List[Any],
        keys: Optional[List[str]] = None,
        threshold: int = 1,
    ) -> List[Any]:
        """Remove duplicate items from a list based on content fingerprint.

        Args:
            items: List of dicts or strings to dedup.
            keys: Dict keys to use for fingerprinting (None = use full item).
            threshold: Max occurrences before suppressing (default: 1).

        Returns:
            Deduplicated list with first occurrence preserved.
        """
        seen: Set[str] = set()
        result: List[Any] = []
        for item in items:
            if isinstance(item, dict) and keys:
                fp = fingerprint_dict(item, *keys)
            else:
                fp = fingerprint(str(item))
            if fp not in seen:
                seen.add(fp)
                result.append(item)
        return result

    def dedup_symbols(self, symbols: List[Dict]) -> List[Dict]:
        """Dedup symbol lists by name + file (most common pattern)."""
        return self.dedup_list(symbols, keys=["name", "file"])

    def dedup_edges(self, edges: List[Dict]) -> List[Dict]:
        """Dedup edge lists by from + to + relation."""
        return self.dedup_list(edges, keys=["from", "to", "relation"])

    def dedup_findings(self, findings: List[Dict]) -> List[Dict]:
        """Dedup audit findings by code + file + line."""
        return self.dedup_list(findings, keys=["code", "file", "line"])

    # ── Inter-response (session-scoped) dedup ─────────────

    def is_new(self, fp: str) -> bool:
        """Check if a fingerprint is new in this session."""
        global _seen_fingerprints
        with _seen_lock:
            if self.session_id not in _seen_fingerprints:
                _seen_fingerprints[self.session_id] = set()
            if fp in _seen_fingerprints[self.session_id]:
                return False
            _seen_fingerprints[self.session_id].add(fp)
            return True

    def mark_seen(self, fp: str) -> None:
        """Mark a fingerprint as seen (for custom tracking)."""
        global _seen_fingerprints
        with _seen_lock:
            if self.session_id not in _seen_fingerprints:
                _seen_fingerprints[self.session_id] = set()
            _seen_fingerprints[self.session_id].add(fp)

    def reset_session(self) -> None:
        """Clear all seen fingerprints for this session."""
        global _seen_fingerprints
        with _seen_lock:
            _seen_fingerprints.pop(self.session_id, None)

    @classmethod
    def reset_all(cls) -> None:
        """Clear all sessions (for testing)."""
        global _seen_fingerprints
        with _seen_lock:
            _seen_fingerprints.clear()

    # ── Stats ────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Get dedup statistics."""
        with _seen_lock:
            fps = _seen_fingerprints.get(self.session_id, set())
            return {
                "session_id": self.session_id,
                "unique_fingerprints": len(fps),
                "suppressed_count": max(0, len(fps) - len(set(fps))),
            }
