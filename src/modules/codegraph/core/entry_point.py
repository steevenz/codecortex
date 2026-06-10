"""
Entry Point Scorer — scores functions by likelihood of being architectural entry points.
Ported from GitNexus's entry-point-scoring.ts algorithm.

:project: CodeCortex
:package: Modules.Codegraph.Core.Entry_point
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger("CodeCortex.CodeGraph.EntryPointScorer")

UNIVERSAL_ENTRY_PATTERNS = [
    re.compile(r"^(main|init|bootstrap|start|run|setup|configure)$", re.I),
    re.compile(r"^handle[A-Z]"),
    re.compile(r"^on[A-Z]"),
    re.compile(r"Handler$"),
    re.compile(r"Controller$"),
    re.compile(r"Service$"),
    re.compile(r"^process[A-Z]"),
    re.compile(r"^execute[A-Z]"),
    re.compile(r"^dispatch[A-Z]"),
    re.compile(r"^trigger[A-Z]"),
    re.compile(r"^listen[A-Z]"),
    re.compile(r"^middleware"),
]

UTILITY_PATTERNS = [
    re.compile(r"^(get|set|is|has|can|should|will|did)[A-Z]"),
    re.compile(r"^_"),
    re.compile(r"^(format|parse|validate|convert|transform)", re.I),
    re.compile(r"^(log|debug|error|warn|info)$", re.I),
    re.compile(r"^(to|from)[A-Z]"),
    re.compile(r"^(encode|decode|serialize|deserialize)", re.I),
    re.compile(r"^(clone|copy|deepCopy)", re.I),
    re.compile(r"Helper$"),
    re.compile(r"Util$"),
    re.compile(r"Utils$"),
]

PYTHON_FRAMEWORK_PATTERNS = {
    "django": [re.compile(r"urls\.py$"), re.compile(r"views\.py$"), re.compile(r"serializers\.py$")],
    "flask": [re.compile(r"routes\.py$"), re.compile(r"app\.py$")],
    "fastapi": [re.compile(r"routers/"), re.compile(r"main\.py$")],
}

TS_FRAMEWORK_PATTERNS = {
    "nextjs": [re.compile(r"pages/"), re.compile(r"app/"), re.compile(r"api/")],
    "express": [re.compile(r"routes/"), re.compile(r"middleware/")],
    "nestjs": [re.compile(r"modules/"), re.compile(r"controllers/")],
}

class EntryPointScorer:
    """
    Scores functions 0-100 based on how likely they are entry points.

    Score components:
    - Call ratio (40%): callees / (callers + 1) — pure consumers rank higher
    - Export status (20%): exported/public symbols rank higher
    - Name patterns (25%): entry point naming conventions
    - Framework detection (15%): path-based framework inference
    """

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = repo_root

    def score(
        self,
        name: str,
        callers_count: int = 0,
        callees_count: int = 0,
        is_exported: bool = False,
        file_path: Optional[str] = None,
        language: str = "python",
    ) -> Dict:
        """Compute entry point score (0-100) with breakdown."""
        reasons = []

        call_score = self._score_call_ratio(callers_count, callees_count)
        if call_score > 0:
            reasons.append(f"call_ratio={call_score:.2f}")

        export_score = self._score_export(is_exported)
        if export_score > 0:
            reasons.append(f"exported={export_score:.2f}")

        name_score = self._score_name(name, language)
        if name_score > 0:
            reasons.append(f"name={name_score:.2f}")

        framework_score = self._score_framework(file_path, language)
        if framework_score > 0:
            reasons.append(f"framework={framework_score:.2f}")

        utility_penalty = self._score_utility_penalty(name)
        if utility_penalty > 0:
            reasons.append(f"utility_penalty={utility_penalty:.2f}")

        total = (call_score * 0.40 + export_score * 0.20 + name_score * 0.25 + framework_score * 0.15) * (1 - utility_penalty)
        normalized = min(100, max(0, round(total * 100)))

        return {"score": normalized, "reasons": reasons, "is_entry_point": normalized >= 50}

    def _score_call_ratio(self, callers: int, callees: int) -> float:
        if callers == 0 and callees == 0:
            return 0.3  # Unknown — moderate score
        if callers == 0:
            return 0.8  # No callers = high entry point likelihood
        ratio = callees / (callers + 1)
        return min(1.0, ratio * 2)

    def _score_export(self, is_exported: bool) -> float:
        return 1.0 if is_exported else 0.3

    def _score_name(self, name: str, language: str) -> float:
        for p in UTILITY_PATTERNS:
            if p.search(name):
                return 0.1  # Strong utility signal
        for p in UNIVERSAL_ENTRY_PATTERNS:
            if p.search(name):
                return 1.0  # Strong entry point signal
        return 0.3  # Neutral

    def _score_utility_penalty(self, name: str) -> float:
        for p in UTILITY_PATTERNS:
            if p.search(name):
                return 0.6
        return 0.0

    def _score_framework(self, file_path: Optional[str], language: str) -> float:
        if not file_path or not self.repo_root:
            return 0.0
        try:
            rel_path = str(Path(file_path).relative_to(self.repo_root)).replace("\\", "/")
        except ValueError:
            rel_path = file_path or ""

        patterns = PYTHON_FRAMEWORK_PATTERNS if language == "python" else TS_FRAMEWORK_PATTERNS
        for _framework, regexes in patterns.items():
            for r in regexes:
                if r.search(rel_path):
                    return 1.0
        return 0.0

def bulk_score_symbols(symbols: List[Dict], repo_root: Optional[str] = None) -> List[Dict]:
    """Score multiple symbols in bulk."""
    scorer = EntryPointScorer(repo_root)
    results = []
    for sym in symbols:
        result = scorer.score(
            name=sym.get("name", ""),
            callers_count=sym.get("callers_count", 0),
            callees_count=sym.get("callees_count", 0),
            is_exported=sym.get("is_exported", False),
            file_path=sym.get("file_path"),
            language=sym.get("language", "python"),
        )
        results.append({**sym, "entry_score": result["score"], "entry_reasons": result["reasons"]})
    return results
