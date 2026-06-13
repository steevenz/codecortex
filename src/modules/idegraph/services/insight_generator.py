"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.services
:standard: CODDY-IdeGraph-v1.0

InsightGenerator — Generates AI Coder insights from project artifacts and chat history.
"""

import json
import yaml
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.modules.idegraph.domain.engram import Engram
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)
AGENTS_HOME = Path.home() / ".aicoders" / ".agents"


class InsightGenerator:
    def __init__(self, search_service):
        self._search = search_service

    def generate_project_insights(self, project_name: str, limit: int = 50) -> Dict[str, Any]:
        engrams = self._search.search("", project_name=project_name, limit=limit)
        if not engrams:
            return {"error": "No interactions found for this project"}

        insights = {
            "project_name": project_name,
            "total_interactions": len(engrams),
            "timeline": self._build_timeline(engrams),
            "code_patterns": self._extract_code_patterns(engrams),
            "problem_solutions": self._extract_problem_solutions(engrams),
            "tool_usage": self._analyze_tool_usage(engrams),
            "ide_distribution": self._analyze_ide_distribution(engrams),
            "recommendations": self._generate_recommendations(engrams),
        }
        return insights

    def _build_timeline(self, engrams: List[Engram]) -> List[Dict[str, Any]]:
        timeline = []
        for e in sorted(engrams, key=lambda x: x.created_at):
            timeline.append({
                "id": e.id[:8],
                "date": e.created_at.strftime("%Y-%m-%d %H:%M"),
                "title": e.title or "Interaction",
                "source": e.source,
            })
        return timeline

    def _extract_code_patterns(self, engrams: List[Engram]) -> Dict[str, Any]:
        patterns = {"languages": Counter(), "frameworks": Counter(), "tools": Counter()}
        for e in engrams:
            for msg in e.messages:
                content = msg.content or ""
                if "```python" in content or "python" in content.lower():
                    patterns["languages"]["python"] += 1
                if "```javascript" in content or "```typescript" in content:
                    patterns["languages"]["js/ts"] += 1
                if "react" in content.lower() or "next" in content.lower():
                    patterns["frameworks"]["react/next"] += 1
                if "fastapi" in content.lower() or "flask" in content.lower():
                    patterns["frameworks"]["fastapi/flask"] += 1
        return {k: dict(v) for k, v in patterns.items()}

    def _extract_problem_solutions(self, engrams: List[Engram]) -> List[Dict[str, Any]]:
        solutions = []
        for e in engrams:
            for msg in e.messages:
                content = msg.content or ""
                if any(kw in content.lower() for kw in ["error", "exception", "failed", "bug"]):
                    solutions.append({
                        "title": e.title or "Problem-Solution",
                        "id": e.id[:8],
                        "preview": content[:200] + "..." if len(content) > 200 else content,
                    })
        return solutions[:10]

    def _analyze_tool_usage(self, engrams: List[Engram]) -> Dict[str, int]:
        tool_counts = Counter()
        for e in engrams:
            for msg in e.messages:
                for tool in msg.tool_use:
                    tool_counts[tool.get("name", "unknown")] += 1
        return dict(tool_counts.most_common(15))

    def _analyze_ide_distribution(self, engrams: List[Engram]) -> Dict[str, int]:
        ide_counts = Counter()
        for e in engrams:
            ide_name = e.ide_info.name if e.ide_info else e.source
            ide_counts[ide_name] += 1
        return dict(ide_counts)

    def _generate_recommendations(self, engrams: List[Engram]) -> List[str]:
        recommendations = []
        tool_usage = self._analyze_tool_usage(engrams)
        if tool_usage.get("read_file", 0) > 10:
            recommendations.append("Consider creating documentation from frequently accessed files")
        if tool_usage.get("grep", 0) > 15:
            recommendations.append("High grep usage suggests complex codebase - consider architectural diagrams")
        if len(engrams) > 20:
            recommendations.append("Rich interaction history available - would benefit from periodic summarization")
        return recommendations

    def generate_summary_yaml(self, project_name: str, limit: int = 50) -> str:
        insights = self.generate_project_insights(project_name=project_name, limit=limit)
        if "error" in insights:
            return f"error: {insights['error']}"
        date_str = datetime.now().strftime("%Y-%m-%d")
        lines = [
            "---",
            f"name: {project_name}-insights",
            f"version: 1.0.0",
            f"date: {date_str}",
            f"status: active",
            "---",
            "",
            f"# Project Insights: {project_name}",
            "",
            "## Summary",
            f"- **Total Interactions**: {insights['total_interactions']}",
            f"- **Code Languages**: {list(insights['code_patterns']['languages'].keys())}",
            f"- **Frameworks**: {list(insights['code_patterns']['frameworks'].keys())}",
            "",
            "## Done List",
            "- [x] Analyzed project interactions",
            "- [x] Extracted code patterns",
            "- [x] Identified problem/solution pairs",
            "- [x] Analyzed tool usage",
            "- [x] Generated recommendations",
            "",
            "## Timeline (Recent 10)",
        ]
        for t in insights['timeline'][:10]:
            lines.append(f"- [{t['date']}] {t['title']} ({t['source']})")
        lines.extend([
            "",
            "## Top Tools",
        ])
        for tool, count in list(insights['tool_usage'].items())[:10]:
            lines.append(f"- **{tool}**: {count} calls")
        lines.extend([
            "",
            "## Recommendations",
        ])
        for rec in insights['recommendations']:
            lines.append(f"- {rec}")
        lines.extend([
            "",
            "## Problem/Solution Highlights",
        ])
        for ps in insights['problem_solutions'][:5]:
            lines.append(f"- **{ps['title']}**: {ps['preview'][:100]}...")
        return "\n".join(lines)

    def save_insights(self, project_name: str, limit: int = 50) -> Path:
        states_dir = AGENTS_HOME / "states" / datetime.now().strftime("%Y-%m-%d")
        states_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%H%M%S")
        file_path = states_dir / f"{timestamp}-insights-{project_name[:20]}.yaml"
        content = self.generate_summary_yaml(project_name=project_name, limit=limit)
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Insights saved to {file_path}")
        return file_path
