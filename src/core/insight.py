"""
AI Insight Engine — generates structured guidance for AI coders from tool outputs.

Each module registers an insight generator that examines tool results and produces
actionable recommendations, risk assessments, and suggested next steps.

Usage:
    from src.core.insight import generate_insight, insight, AIInsight

    # In any tool:
    return api_response(..., insight="tool_name")

    # Or directly:
    ins = generate_insight("code_analyze", data)

:project: CodeCortex
:package: Core.Insight
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# Lazy load generators on first use to avoid circular imports.
_GENERATORS_LOADED: bool = False
_BRIDGE_AVAILABLE: Optional[bool] = None


def _ensure_generators() -> None:
    global _GENERATORS_LOADED
    if not _GENERATORS_LOADED:
        from src.core import insight_generators as _g
        _g  # noqa: trigger @register_insight decorators
        _GENERATORS_LOADED = True


def _ensure_bridge() -> bool:
    """Auto-discover neocortex Server. Returns True if bridge is available."""
    global _BRIDGE_AVAILABLE
    if _BRIDGE_AVAILABLE is not None:
        return _BRIDGE_AVAILABLE
    if os.environ.get("CODECORTEX_NO_AI", "").lower() in ("1", "true", "yes"):
        _BRIDGE_AVAILABLE = False
        return False
    try:
        from src.core.cognitive.bridge import CortexBridge
        bridge = CortexBridge.instance()
        _BRIDGE_AVAILABLE = bridge.discover()
        return _BRIDGE_AVAILABLE
    except Exception:
        _BRIDGE_AVAILABLE = False
        return False


# ── Schema ────────────────────────────────────────────────

class AIInsight:
    """Structured insight for AI coders embedded in every tool response.

    Fields:
        summary: One-line AI-readable summary of what was found.
        recommendations: Actionable suggestions based on results.
        next_actions: Suggested next tool calls with parameters.
        critical_issues: Urgent findings needing immediate attention.
        confidence: "high" | "medium" | "low".
        risk_level: "low" | "medium" | "high".
    """
    __slots__ = ("summary", "recommendations", "next_actions", "critical_issues", "confidence", "risk_level")

    def __init__(
        self,
        summary: str = "",
        recommendations: Optional[List[str]] = None,
        next_actions: Optional[List[Dict[str, Any]]] = None,
        critical_issues: Optional[List[Dict[str, Any]]] = None,
        confidence: str = "medium",
        risk_level: str = "low",
    ):
        self.summary = summary
        self.recommendations = recommendations or []
        self.next_actions = next_actions or []
        self.critical_issues = critical_issues or []
        self.confidence = confidence
        self.risk_level = risk_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "recommendations": self.recommendations,
            "next_actions": self.next_actions,
            "critical_issues": self.critical_issues,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
        }

    @classmethod
    def ok(cls, summary: str, **kwargs) -> "AIInsight":
        return cls(summary=summary, confidence="high", risk_level="low", **kwargs)

    @classmethod
    def warn(cls, summary: str, **kwargs) -> "AIInsight":
        return cls(summary=summary, confidence="medium", risk_level="medium", **kwargs)

    @classmethod
    def alert(cls, summary: str, **kwargs) -> "AIInsight":
        return cls(summary=summary, confidence="high", risk_level="high", **kwargs)


# ── Registry ──────────────────────────────────────────────

_INSIGHT_GENERATORS: Dict[str, callable] = {}


def register_insight(tool_name: str):
    """Decorator to register an insight generator for a tool."""
    def wrapper(fn):
        _INSIGHT_GENERATORS[tool_name] = fn
        return fn
    return wrapper


def generate_insight(tool_name: str, data: Any, context: Optional[Dict] = None) -> AIInsight:
    """Generate insight for a tool output. Auto-calls LLM when neocortex available, falls back to rule-based."""
    _ensure_generators()
    ctx = context or {}

    # Phase 1: Try LLM enrichment via neocortex Bridge (auto-discovery)
    llm_enriched = None
    try:
        if _ensure_bridge():
            from src.core.cognitive.bridge import CortexBridge
            bridge = CortexBridge.instance()
            project_id = ctx.get("repo_id") or ctx.get("project_id") or "default"
            enriched_text = bridge.enrich(
                tool_name=tool_name,
                data=data,
                context=ctx,
                project_id=project_id,
            )
            if enriched_text:
                llm_enriched = AIInsight(
                    summary=enriched_text[:200],
                    recommendations=[enriched_text] if enriched_text else [],
                    confidence="high",
                )
    except Exception:
        pass

    if llm_enriched:
        return llm_enriched

    # Phase 2: Fall back to registered rule-based generator
    generator = _INSIGHT_GENERATORS.get(tool_name)
    if generator:
        try:
            return generator(data, ctx)
        except Exception:
            return AIInsight(summary="Insight generation failed", confidence="low")
    return _generic_insight(tool_name, data)


def insight(
    summary: str = "",
    recommendations: Optional[List[str]] = None,
    next_actions: Optional[List[Dict[str, Any]]] = None,
    critical_issues: Optional[List[Dict[str, Any]]] = None,
    confidence: str = "medium",
    risk_level: str = "low",
) -> AIInsight:
    """Shorthand to create an AIInsight inline."""
    return AIInsight(
        summary=summary, recommendations=recommendations,
        next_actions=next_actions, critical_issues=critical_issues,
        confidence=confidence, risk_level=risk_level,
    )


def _generic_insight(tool_name: str, data: Any) -> AIInsight:
    """Fallback insight for tools without registered generators."""
    if data is None:
        return AIInsight(summary="No data returned", confidence="low")
    if isinstance(data, dict):
        count = len(data)
        keys = list(data.keys())[:5]
        return AIInsight(
            summary=f"Tool '{tool_name}' returned {count} fields: {', '.join(keys)}",
            confidence="medium",
        )
    if isinstance(data, list):
        return AIInsight(
            summary=f"Tool '{tool_name}' returned {len(data)} items",
            confidence="medium",
        )
    return AIInsight(summary=f"Tool '{tool_name}' completed", confidence="medium")


# ── Helpers ───────────────────────────────────────────────

def _count(data: Any, *keys: str) -> int:
    """Safely count items from nested dict."""
    if not isinstance(data, dict):
        return 0
    for key in keys:
        val = data.get(key)
        if isinstance(val, list):
            return len(val)
        if isinstance(val, dict):
            return len(val)
    return 0


def _found(data: Any, *keys: str) -> int:
    """Count occurrences of truthy nested keys."""
    if not isinstance(data, dict):
        return 0
    for key in keys:
        val = data.get(key)
        if isinstance(val, (int, float)):
            return int(val)
    return 0


def _suggest_tool(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a next_action suggestion dict."""
    return {"tool": action, "params": params}


def _critical(message: str, **meta: Any) -> Dict[str, Any]:
    """Create a critical issue entry."""
    return {"message": message, **meta}
