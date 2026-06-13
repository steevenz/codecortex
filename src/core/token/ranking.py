"""
Context Ranking — combines FTS score, semantic similarity, graph centrality,
and freshness into a single relevance score for AI context injection.

Enables: context ranking (5.4), relevance scoring, result pruning.

:project: CodeCortex
:package: Core.Token.Ranking
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CodeCortex.Core.Token.Ranking")

# Default weights for each signal in the composite score
DEFAULT_WEIGHTS = {
    "fts": 0.30,
    "semantic": 0.25,
    "graph": 0.20,
    "freshness": 0.10,
    "precision": 0.15,
}

# Minimum composite score to include a result
DEFAULT_MIN_SCORE = 0.05

# Maximum results after ranking
DEFAULT_MAX_RESULTS = 50


class ContextRanker:
    """Ranks code search results by combining multiple relevance signals.

    Each result can have:
    - fts_score: 0-1 from FTS5 text search
    - semantic_score: 0-1 from embedding similarity
    - graph_score: 0-1 from graph centrality/relevance
    - freshness_score: 0-1 from last modified time
    - precision_score: 0-1 from exact match bonus
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        min_score: float = DEFAULT_MIN_SCORE,
        max_results: int = DEFAULT_MAX_RESULTS,
    ):
        self.weights = {**DEFAULT_WEIGHTS, **(weights or {})}
        self.min_score = min_score
        self.max_results = max_results

    def rank(
        self,
        results: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Rank and prune search results by composite relevance score.

        Args:
            results: List of result dicts with optional * _score fields.
            query: Original query for exact match bonus.

        Returns:
            Ranked results sorted by composite_score descending,
            each result now includes composite_score and rank_signals.
        """
        if not results:
            return []

        ranked = []
        for item in results:
            signals = self._extract_signals(item, query)
            composite = self._compute_composite(signals)
            if composite >= self.min_score:
                item["composite_score"] = round(composite, 3)
                item["rank_signals"] = signals
                ranked.append(item)

        ranked.sort(key=lambda x: x["composite_score"], reverse=True)
        return ranked[:self.max_results]

    def rank_symbols(
        self,
        symbols: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Rank symbol list (common for graph_search results).

        Symbols typically have: name, file, kind, line.
        Computes signals from name matching against query.
        """
        ranked = []
        for sym in symbols:
            name = sym.get("name", "")
            file_path = sym.get("file", "")
            signals = self._compute_symbol_signals(name, file_path, query)
            composite = self._compute_composite(signals)
            if composite >= self.min_score:
                sym["composite_score"] = round(composite, 3)
                sym["rank_signals"] = signals
                ranked.append(sym)

        ranked.sort(key=lambda x: x["composite_score"], reverse=True)
        return ranked[:self.max_results]

    def rank_files(
        self,
        files: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Rank file list (common for fs_search results).

        Files typically have: path, size, matches.
        """
        ranked = []
        for f in files:
            path = f.get("path", "")
            matches = f.get("matches", [])
            signals = self._compute_file_signals(path, matches, query)
            composite = self._compute_composite(signals)
            if composite >= self.min_score:
                f["composite_score"] = round(composite, 3)
                f["rank_signals"] = signals
                ranked.append(f)

        ranked.sort(key=lambda x: x["composite_score"], reverse=True)
        return ranked[:self.max_results]

    # ── Internal ──────────────────────────────────────────

    def _extract_signals(
        self, item: Dict, query: Optional[str],
    ) -> Dict[str, float]:
        """Extract available relevance signals from a result item."""
        signals: Dict[str, float] = {}

        # Direct score fields
        signals["fts"] = max(0.0, min(1.0, item.get("fts_score", 0.0)))
        signals["semantic"] = max(0.0, min(1.0, item.get("semantic_score", item.get("similarity", 0.0))))
        signals["graph"] = max(0.0, min(1.0, item.get("graph_score", 0.0)))

        # Compute precision score from name match
        signals["precision"] = self._compute_precision(
            item.get("name", ""),
            item.get("file", ""),
            query or "",
        )

        # Compute freshness from recency
        signals["freshness"] = self._compute_freshness(
            item.get("last_modified"),
            item.get("line_start", 0),
        )

        return signals

    def _compute_symbol_signals(
        self, name: str, file_path: str, query: Optional[str],
    ) -> Dict[str, float]:
        """Compute signals from symbol metadata."""
        signals: Dict[str, float] = {}
        q = (query or "").lower()

        # Name-based precision
        signals["precision"] = self._compute_precision(name, file_path, q)

        # FTS approximation from name match
        if q and name:
            name_lower = name.lower()
            if q in name_lower:
                signals["fts"] = min(1.0, len(q) / max(len(name_lower), 1) + 0.3)
            elif any(word in name_lower for word in q.split()):
                signals["fts"] = 0.3
            else:
                signals["fts"] = 0.0
        else:
            signals["fts"] = 0.0

        signals["semantic"] = 0.0
        signals["graph"] = 0.0
        signals["freshness"] = 0.5
        return signals

    def _compute_file_signals(
        self, path: str, matches: List, query: Optional[str],
    ) -> Dict[str, float]:
        """Compute signals from file metadata."""
        signals: Dict[str, float] = {}
        q = (query or "").lower()

        signals["precision"] = self._compute_precision(path, "", q)
        signals["fts"] = 0.5 if matches else 0.0
        signals["semantic"] = 0.0
        signals["graph"] = 0.0
        signals["freshness"] = self._compute_freshness(None, 0)
        return signals

    def _compute_precision(self, name: str, file_path: str, query: str) -> float:
        """Compute precision score: exact matches > partial > none."""
        combined = f"{name} {file_path}".lower()
        if not query or not combined:
            return 0.0

        # Exact phrase match
        if query in combined:
            return 1.0

        # All words match (in any order)
        words = [w for w in query.split() if len(w) > 2]
        if words and all(w in combined for w in words):
            return 0.8

        # Any word matches
        if words and any(w in combined for w in words):
            ratio = sum(1 for w in words if w in combined) / len(words)
            return 0.3 + 0.4 * ratio

        return 0.0

    def _compute_freshness(self, last_modified: Any, line_start: int) -> float:
        """Compute freshness score: newer = higher score."""
        if last_modified is not None:
            try:
                from datetime import datetime, timezone
                if isinstance(last_modified, str):
                    dt = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
                else:
                    dt = last_modified
                days_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
                return max(0.0, min(1.0, 1.0 - days_ago / 365.0))
            except Exception:
                pass
        # Default: slight preference for earlier lines (entry points)
        return max(0.0, 1.0 - line_start / 1000) if line_start else 0.5

    def _compute_composite(self, signals: Dict[str, float]) -> float:
        """Compute weighted composite score from signals."""
        score = 0.0
        for signal_name, weight in self.weights.items():
            value = signals.get(signal_name, 0.0)
            score += value * weight
        return max(0.0, min(1.0, score))

    def get_contribution(
        self, signal_name: str, signals: Dict[str, float],
    ) -> float:
        """Get a single signal's contribution to the composite score."""
        value = signals.get(signal_name, 0.0)
        weight = self.weights.get(signal_name, 0)
        return value * weight
