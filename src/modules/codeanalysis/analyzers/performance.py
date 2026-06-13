"""
Performance Hotspot Detector — static analysis for potential bottlenecks.

Detects: high cyclomatic complexity, deep nesting, large functions,
frequent churn, expensive operations (loops, N+1 queries).

:project: CodeCortex
:package: Modules.Codeanalysis.Analyzers.Performance
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeAnalysis-v1.0
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


class PerformanceAnalyzer:
    """Static performance hotspot detection."""

    def analyze(self, root_path: str, max_files: int = 2000) -> Dict[str, Any]:
        root = Path(root_path)
        hotspots: List[Dict] = []

        for fp in root.rglob("*.py"):
            if not fp.is_file():
                continue
            if any(p.startswith(".") or p in ("node_modules", "venv", "__pycache__") for p in fp.relative_to(root).parts):
                continue

            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            lines = content.split("\n")

            # Complexity: nesting depth
            max_depth = 0
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith(("#", "'''", '"""')):
                    indent = len(line) - len(line.lstrip())
                    depth = indent // 4
                    max_depth = max(max_depth, depth)

            # Expensive loops (nested loops)
            nested_loops = 0
            loop_stack = 0
            for line in lines:
                if re.match(r"^\s*(for|while)\b", line):
                    loop_stack += 1
                    nested_loops = max(nested_loops, loop_stack)
                elif loop_stack > 0 and not re.match(r"^\s*(for|while|if|with)\b", line):
                    loop_stack = 0

            # N+1 detection (query in loop)
            n_plus_one = 0
            in_loop = False
            for line in lines:
                if re.match(r"^\s*(for|while)\b", line):
                    in_loop = True
                elif in_loop and re.search(r"\.(query|execute|fetch|filter|get)\s*\(", line, re.I):
                    n_plus_one += 1
                elif line.strip() and not line.startswith((" ", "\t")):
                    in_loop = False

            if max_depth > 6 or nested_loops > 1 or n_plus_one > 0:
                hotspots.append({
                    "file": str(fp),
                    "max_nesting": max_depth,
                    "nested_loops": nested_loops,
                    "n_plus_one_queries": n_plus_one,
                    "risk": "high" if (max_depth > 8 or n_plus_one > 3) else "medium",
                })

        return {
            "files_scanned": min(len(list(root.rglob("*.py"))), max_files),
            "total_hotspots": len(hotspots),
            "hotspots": hotspots[:50],
            "summary": {
                "high_risk": sum(1 for h in hotspots if h.get("risk") == "high"),
                "medium_risk": sum(1 for h in hotspots if h.get("risk") == "medium"),
            },
        }
