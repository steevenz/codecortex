"""
Intent-Aware Retrieval Router — classifies natural language queries into
code intelligence intents and routes to the optimal tool configuration.

No LLM dependency. Uses keyword + pattern matching for deterministic routing.
Enables task-aware retrieval (8.1) and intent-based search (11.5).

:project: CodeCortex
:package: Modules.Codeanalysis.Services.Intent
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeAnalysis-v1.0
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CodeCortex.CodeAnalysis.Intent")

# ── Intent definitions ───────────────────────────────────

INTENT_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "trace_bug": {
        "description": "Trace execution flow to find bug causes",
        "triggers": ["trace", "flow", "execution path", "call chain", "how does.*work",
                     "where.*crash", "why.*fail", "debug", "stack trace", "error path"],
        "tool": "codebase",
        "action": "graph",
        "sub_action": "trace_flow",
        "search_action": "relation",
        "search_params": {"relation_type": "callers", "max_depth": 5},
        "priority": "high",
    },
    "understand_feature": {
        "description": "Understand how a feature or module works",
        "triggers": ["how does", "explain", "overview of", "understand", "what does.*do",
                     "architecture of", "design of", "structure of"],
        "tool": "codebase",
        "action": "graph",
        "sub_action": "build",
        "search_action": "semantic",
        "search_params": {"limit": 20},
        "priority": "medium",
    },
    "find_usage": {
        "description": "Find where a symbol is used or called",
        "triggers": ["called by", "used in", "used by", "referenced by", "imported by",
                     "where is", "where are", "find usages", "find callers", "find callees",
                     "who calls", "who uses", "who imports"],
        "tool": "codebase",
        "action": "graph",
        "sub_action": "query",
        "query_type": "all_callers",
        "search_action": "symbol",
        "search_params": {"fuzzy": True},
        "priority": "high",
    },
    "check_impact": {
        "description": "Assess impact of changing a symbol or file",
        "triggers": ["impact", "what breaks", "change.*affect", "modify.*effect",
                     "rename.*impact", "refactor.*risk", "blast radius",
                     "before.*change", "safe to.*(change|delete|remove|rename)"],
        "tool": "codebase",
        "action": "refactor",
        "sub_action": "impact",
        "search_action": "relation",
        "search_params": {"relation_type": "all_callers", "max_depth": 3},
        "priority": "high",
    },
    "architecture_overview": {
        "description": "Get high-level architecture understanding",
        "triggers": ["architecture", "module", "dependency", "overview", "component",
                     "layer", "boundary", "service.*map", "system.*design",
                     "how.*organize", "project structure"],
        "tool": "codebase",
        "action": "graph",
        "sub_action": "audit",
        "search_action": "modular",
        "search_params": {"limit": 50},
        "priority": "low",
    },
    "find_code": {
        "description": "Find specific code by name or pattern",
        "triggers": ["find", "search", "locate", "where is", "show me",
                     "look for", "get the.*(file|class|function|method)"],
        "tool": "codebase",
        "action": "search",
        "search_action": "symbol",
        "search_params": {"fuzzy": True, "limit": 20},
        "priority": "medium",
    },
    "explain_error": {
        "description": "Debug an error from a message or stack trace",
        "triggers": ["error", "exception", "traceback", "crash log", "stack trace",
                     "failed", "broken", "not working", "bug report"],
        "tool": "codebase",
        "action": "search",
        "search_action": "semantic",
        "search_params": {"limit": 10},
        "priority": "high",
    },
}

# Negative triggers — queries about these topics should NOT use code search
NON_CODE_TRIGGERS = [
    "weather", "news", "sports", "movie", "recipe", "cooking",
    "hello", "hi there", "how are you", "who are you",
    "joke", "poem", "story", "song",
]

# Fallback intent for unclear queries
FALLBACK_INTENT = "find_code"


class IntentRouter:
    """Routes natural language queries to the optimal code intelligence tool.

    Usage:
        router = IntentRouter()
        result = router.route("where is the login handler called?")
        # {
        #     "intent": "find_usage",
        #     "confidence": 0.85,
        #     "suggested_query": "login handler",
        #     "tool_config": {"tool": "codebase", "action": "graph", ...}
        # }
    """

    def __init__(self):
        self._compiled: Dict[str, List[re.Pattern]] = {}
        for intent_name, config in INTENT_DEFINITIONS.items():
            self._compiled[intent_name] = [
                re.compile(trigger, re.I) for trigger in config["triggers"]
            ]

    def classify(self, query: str) -> Dict[str, Any]:
        """Classify a query into an intent with confidence score.

        Returns:
            Dict with intent, confidence, suggested_query.
        """
        query_stripped = query.strip()
        if not query_stripped:
            return {"intent": FALLBACK_INTENT, "confidence": 0, "suggested_query": ""}

        # Check for non-code queries
        for trigger in NON_CODE_TRIGGERS:
            if re.search(trigger, query_stripped, re.I):
                return {
                    "intent": "non_code",
                    "confidence": 0.9,
                    "suggested_query": query_stripped,
                    "message": "This query doesn't appear to be about code.",
                }

        # Score each intent
        best_intent = FALLBACK_INTENT
        best_score = 0
        best_match = ""

        for intent_name, patterns in self._compiled.items():
            config = INTENT_DEFINITIONS[intent_name]
            score = 0
            matched_trigger = ""

            for pattern in patterns:
                m = pattern.search(query_stripped)
                if m:
                    match_len = len(m.group(0))
                    # Longer matches = more specific = higher score
                    match_score = min(1.0, match_len / max(len(query_stripped), 1) * 2)
                    score = max(score, match_score)
                    matched_trigger = m.group(0)

            if score > best_score:
                best_score = score
                best_intent = intent_name
                best_match = matched_trigger

        # If confidence is low, use fallback
        if best_score < 0.15:
            best_intent = FALLBACK_INTENT
            best_score = 0.3

        # Extract suggested query: take text after the matched trigger
        suggested = query_stripped
        if best_match:
            idx = query_stripped.lower().find(best_match.lower())
            if idx >= 0:
                after = query_stripped[idx + len(best_match):].strip()
                before = query_stripped[:idx].strip()
                # Prefer text after the trigger (e.g., "find login handler" → "login handler")
                # Fall back to text before (e.g., "login handler where called" → "login handler")
                suggested = after or before or best_match
            else:
                suggested = query_stripped
            # Clean up: remove leading/trailing punctuation, trim
            suggested = re.sub(r"^[\s,;:?.!-]+|[\s,;:?.!-]+$", "", suggested)
        if not suggested or len(suggested) < 2:
            suggested = query_stripped

        return {
            "intent": best_intent,
            "confidence": round(best_score, 2),
            "suggested_query": suggested,
            "matched_trigger": best_match,
        }

    def route(self, query: str, repo_id: Optional[str] = None) -> Dict[str, Any]:
        """Classify intent and return optimal tool configuration.

        Returns:
            Dict with intent, confidence, suggested_query, tool_config, next_actions.
        """
        classification = self.classify(query)
        intent = classification["intent"]
        suggested = classification["suggested_query"]

        if intent == "non_code":
            return {
                **classification,
                "tool_config": None,
                "next_actions": [],
            }

        config = INTENT_DEFINITIONS.get(intent, INTENT_DEFINITIONS[FALLBACK_INTENT])

        # Build tool configuration
        tool_config = {
            "tool": config["tool"],
            "action": config["action"],
            "params": {
                "query": suggested or query,
                "repo_id": repo_id,
            },
        }

        # Add action-specific parameters
        if config["action"] == "graph":
            tool_config["params"]["sub_action"] = config.get("sub_action", "build")
            if "query_type" in config:
                tool_config["params"]["query_type"] = config["query_type"]
        elif config["action"] == "search":
            tool_config["params"]["search_action"] = config.get("search_action", "symbol")

        # Add search params
        search_params = config.get("search_params", {})
        tool_config["params"].update(search_params)

        # Generate next action suggestions
        next_actions = self._suggest_next_actions(intent, suggested, repo_id)

        return {
            "intent": intent,
            "confidence": classification["confidence"],
            "suggested_query": suggested,
            "matched_trigger": classification.get("matched_trigger", ""),
            "tool_config": tool_config,
            "intent_description": config["description"],
            "next_actions": next_actions,
        }

    def _suggest_next_actions(
        self, intent: str, query: str, repo_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Suggest follow-up actions based on intent."""
        actions = []
        base = {"repo_id": repo_id} if repo_id else {}

        if intent == "trace_bug":
            actions.append({"action": "find_usage", "params": {"query": query, **base}})
            actions.append({"action": "check_impact", "params": {"query": query, **base}})
        elif intent == "understand_feature":
            actions.append({"action": "architecture_overview", "params": {"query": "", **base}})
        elif intent == "find_usage":
            actions.append({"action": "check_impact", "params": {"query": query, **base}})
        elif intent == "check_impact":
            actions.append({"action": "trace_bug", "params": {"query": query, **base}})
        elif intent == "architecture_overview":
            actions.append({"action": "find_code", "params": {"query": "", **base}})

        return actions

    def list_intents(self) -> List[Dict[str, Any]]:
        """List all supported intents with descriptions."""
        return [
            {
                "name": name,
                "description": config["description"],
                "priority": config.get("priority", "medium"),
                "example_triggers": config["triggers"][:3],
            }
            for name, config in INTENT_DEFINITIONS.items()
        ]
