"""
Fragility Analyzer — composite risk score for repository health.

Combines multiple signals into a single fragility score (0-100):
1. Churn score: How frequently files change (from git)
2. Complexity score: Cyclomatic complexity (from AST)
3. Coupling score: Degree of coupling (from graph)
4. Co-change score: Temporal coupling (from git co-change)
5. Freshness score: Knowledge staleness (from integrity)

:project: CodeCortex
:package: Modules.Codegraph.Services.Fragility
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CodeCortex.CodeGraph.Fragility")


class FragilityAnalyzer:
    """Composite fragility scoring for repository health assessment.

    A fragility score of 0 = perfectly healthy, 100 = extremely fragile.
    """

    WEIGHTS = {
        "churn": 0.25,
        "complexity": 0.20,
        "coupling": 0.20,
        "co_change": 0.20,
        "freshness": 0.15,
    }

    def __init__(self, db):
        self.db = db

    def calculate(
        self,
        repo_id: str,
        churn_data: Optional[List[Dict]] = None,
        complexity_data: Optional[Dict] = None,
        coupling_data: Optional[Dict] = None,
        cochange_data: Optional[Dict] = None,
        freshness_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Calculate composite fragility score.

        Args:
            repo_id: Repository UUID.
            churn_data: From git diagnostics (churn_hotspots).
            complexity_data: From repo_analyze (complexity_metrics).
            coupling_data: From graph_audit (coupling + god_nodes).
            cochange_data: From temporal coupling analysis.
            freshness_data: From FreshnessScorer.

        Returns:
            Dict with score, components, hotspots.
        """
        components = {}

        # 1. Churn score
        components["churn"] = self._score_churn(churn_data)

        # 2. Complexity score
        components["complexity"] = self._score_complexity(complexity_data)

        # 3. Coupling score
        components["coupling"] = self._score_coupling(coupling_data)

        # 4. Co-change score
        components["co_change"] = self._score_cochange(cochange_data)

        # 5. Freshness score (inverted: low freshness = high fragility)
        components["freshness"] = self._score_freshness(freshness_data)

        # Composite
        composite = sum(
            components[k]["score"] * self.WEIGHTS.get(k, 0)
            for k in components
        )
        composite = round(min(100, max(0, composite)), 1)

        # Risk level
        if composite >= 70:
            risk = "critical"
        elif composite >= 50:
            risk = "high"
        elif composite >= 30:
            risk = "medium"
        else:
            risk = "low"

        # Collect hotspots
        hotspots = self._collect_hotspots(
            churn_data, complexity_data, coupling_data, cochange_data,
        )

        return {
            "repo_id": repo_id,
            "fragility_score": composite,
            "risk": risk,
            "components": components,
            "hotspots": hotspots[:20],
            "recommendations": self._generate_recommendations(components, hotspots),
        }

    def _score_churn(self, data: Optional[List[Dict]]) -> Dict:
        """Score churn: 0 = no churn, 100 = extreme churn."""
        if not data:
            return {"score": 0, "detail": "No churn data"}
        high = sum(1 for h in data if isinstance(h, dict) and h.get("risk") == "high")
        medium = sum(1 for h in data if isinstance(h, dict) and h.get("risk") == "medium")
        score = min(100, high * 20 + medium * 10)
        return {"score": score, "detail": f"{high} high-risk, {medium} medium-risk hotspots"}

    def _score_complexity(self, data: Optional[Dict]) -> Dict:
        """Score complexity: 0 = simple, 100 = very complex."""
        if not data:
            return {"score": 0, "detail": "No complexity data"}
        max_cpx = data.get("max_cyclomatic", 0) if isinstance(data, dict) else 0
        avg_cpx = data.get("average_cyclomatic", 0) if isinstance(data, dict) else 0
        score = min(100, max_cpx * 3 + avg_cpx * 5)
        return {"score": score, "detail": f"Max cyclomatic: {max_cpx}, Avg: {avg_cpx}"}

    def _score_coupling(self, data: Optional[Dict]) -> Dict:
        """Score coupling: 0 = well-encapsulated, 100 = highly coupled."""
        if not data:
            return {"score": 0, "detail": "No coupling data"}
        gods = data.get("god_nodes", []) if isinstance(data, dict) else []
        coupling = data.get("coupling", []) if isinstance(data, dict) else []
        circ = data.get("circular_deps", {}).get("count", 0) if isinstance(data, dict) else 0
        n_gods = len(gods) if isinstance(gods, list) else 0
        n_coupling = len(coupling) if isinstance(coupling, list) else 0
        score = min(100, n_gods * 10 + n_coupling * 5 + circ * 15)
        return {"score": score, "detail": f"{n_gods} god nodes, {n_coupling} couplings, {circ} circular deps"}

    def _score_cochange(self, data: Optional[Dict]) -> Dict:
        """Score co-change: 0 = no temporal coupling, 100 = heavy."""
        if not data or not isinstance(data, dict) or not data.get("built"):
            return {"score": 0, "detail": "No co-change data"}
        high = data.get("high_risk_pairs", 0)
        medium = data.get("medium_risk_pairs", 0)
        score = min(100, high * 10 + medium * 3)
        return {"score": score, "detail": f"{high} high-risk pairs, {medium} medium-risk pairs"}

    def _score_freshness(self, data: Optional[Dict]) -> Dict:
        """Score freshness: 0 = fresh, 100 = very stale (inverted)."""
        if not data or not isinstance(data, dict):
            return {"score": 0, "detail": "No freshness data"}
        fresh_score = data.get("score", 100)
        score = max(0, 100 - fresh_score)
        stale_ratio = data.get("stale_file_ratio", 0)
        return {"score": round(score, 1), "detail": f"Freshness: {fresh_score}/100, stale ratio: {stale_ratio}"}

    def _collect_hotspots(self, *datas: Optional[List]) -> List[Dict]:
        """Collect all hotspots from various data sources."""
        hotspots = []
        for data in datas:
            if isinstance(data, list):
                hotspots.extend(data)
        hotspots.sort(key=lambda h: h.get("score", 0) if isinstance(h, dict) else 0, reverse=True)
        return hotspots

    def _generate_recommendations(
        self, components: Dict, hotspots: List,
    ) -> List[str]:
        """Generate actionable recommendations based on scores."""
        recs = []
        for key, comp in components.items():
            score = comp.get("score", 0) if isinstance(comp, dict) else 0
            if score >= 50:
                labels = {
                    "churn": "High churn — stabilize volatile files",
                    "complexity": "High complexity — refactor complex functions",
                    "coupling": "High coupling — reduce hidden dependencies",
                    "co_change": "High temporal coupling — extract shared concerns",
                    "freshness": "Stale knowledge — re-index repository",
                }
                if key in labels:
                    recs.append(labels[key])
        if hotspots:
            top = hotspots[0] if isinstance(hotspots, list) else None
            if isinstance(top, dict):
                name = top.get("file") or top.get("name", "Unknown")
                recs.append(f"Highest risk item: {name}")
        return recs
