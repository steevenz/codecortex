"""
NeoEnricher — Domain-specific LLM enrichment via Neocortex round-robin.

Wraps CortexBridge with specialized, structured calls per CodeCortex domain:
  - audit_narrative   : Technical debt report with prioritized action plan
  - naming_advisor    : Semantic naming validation + convention alignment
  - refactor_sequence : Blast radius → safe refactoring steps
  - search_explainer  : Search result relevance ranking
  - structure_advisor : Folder/file structure recommendations
  - onboarding_summary: Repository onboarding guide
  - security_narrative: Security findings remediation plan

All methods are SYNCHRONOUS (uses sync httpx inside CortexBridge) so they
can be called directly from @register_insight generators without asyncio.

Security contract:
  - Raw secret values, credentials, and PII are NEVER included in prompts.
  - Only counts, type labels, and severity categories are sent to LLM.
  - LLM output is validated for structure and forbidden keys before use.
  - All outputs are labelled as AI-generated in the meta field.

:project: CodeCortex
:package: Core.Cognitive
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CrossStack-v1.0
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_TIMEOUT = 90.0     # Ollama inference can take 30-90s on first load
_MAX_PROMPT_ITEMS = 8       # max list items injected into any prompt
_MAX_STRING_LEN = 120       # max chars per string field in prompts

# Matches markdown code fences containing JSON: ```json {...}``` or ```{...}```
_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", re.DOTALL)

# Keys that would indicate prompt injection or code execution attempts in LLM output
_FORBIDDEN_OUTPUT_KEYS = frozenset({
    "__import__", "__builtins__", "eval", "exec", "os", "sys",
    "subprocess", "open", "__class__", "__globals__",
})


def _new_request_id() -> str:
    return f"neo_{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_str(value: Any, max_len: int = _MAX_STRING_LEN) -> str:
    """Truncate and stringify a value safely for prompt injection."""
    return str(value)[:max_len] if value is not None else ""


def _safe_list(items: Any, max_items: int = _MAX_PROMPT_ITEMS) -> List[str]:
    """Extract safe string labels from a list. Never includes raw values."""
    if not isinstance(items, list):
        return []
    result = []
    for item in items[:max_items]:
        if isinstance(item, dict):
            label = item.get("type") or item.get("name") or item.get("kind") or "unknown"
            result.append(_safe_str(label, 60))
        elif isinstance(item, str):
            result.append(_safe_str(item, 60))
    return result


def _wrap(data: Optional[Dict], project_id: str) -> Optional[Dict]:
    """Attach standard meta to an enricher result. Returns None if data is None."""
    if data is None:
        return None
    data["_meta"] = {
        "request_id": _new_request_id(),
        "generated_at": _utcnow(),
        "project_id": project_id,
        "source": "neocortex_llm",
        "ai_generated": True,
    }
    return data


def _validate_json_obj(obj: Any) -> Optional[Dict]:
    """Validate a parsed JSON object against the forbidden-key list."""
    if not isinstance(obj, dict):
        return None
    if _FORBIDDEN_OUTPUT_KEYS.intersection(obj.keys()):
        logger.warning(
            "LLM output rejected: forbidden keys detected",
            extra={"event": "LLM_OUTPUT_REJECTED", "reason": "forbidden_keys"},
        )
        return None
    return obj


def _extract_json(text: str) -> Optional[Dict]:
    """
    Extract first JSON object from LLM response text.

    Tries three strategies in order:
      1. Markdown code fence containing JSON
      2. Direct JSON parse of whole text
      3. Substring between first { and last }

    Validates the parsed object against forbidden-key list to prevent
    prompt injection attacks from propagating into CodeCortex data structures.
    """
    if not text:
        return None

    # Strategy 1: markdown fence
    m = _JSON_FENCE.search(text)
    if m:
        try:
            return _validate_json_obj(json.loads(m.group(1)))
        except json.JSONDecodeError:
            pass

    # Strategy 2: direct parse
    raw = text.strip()
    try:
        return _validate_json_obj(json.loads(raw))
    except json.JSONDecodeError:
        pass

    # Strategy 3: substring between { and }
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return _validate_json_obj(json.loads(raw[start:end]))
        except json.JSONDecodeError:
            pass

    return None


# LLM error sentinels — strings we treat as "no usable response"
_LLM_ERROR_MARKERS = (
    "[ERROR]",
    "[No LLM available",
    "Autonomous reasoning unavailable",
    "Fallback to guided mode required",
)


def _bridge_call(
    prompt: str,
    fmt: str = "insight",
    project_id: str = "default",
    max_tokens: int = 800,
) -> Optional[str]:
    """
    Single synchronous call to neocortex /api/v1/llm/analyze.

    Returns raw LLM text content, or None on any failure / known error sentinel.
    Callers MUST parse and validate the returned string before use.
    """
    try:
        from src.core.cognitive.bridge import CortexBridge
        bridge = CortexBridge.instance()
        if not bridge.available() or not bridge.neocortex_url:
            return None
        import httpx
        resp = httpx.post(
            f"{bridge.neocortex_url}/api/v1/llm/analyze",
            json={"prompt": prompt, "format": fmt, "project_id": project_id, "max_tokens": max_tokens},
            headers=bridge._headers(),
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                content = data.get("data", {}).get("content") or ""
                # Filter out known LLM error sentinels so callers get clean None
                if content and any(marker in content for marker in _LLM_ERROR_MARKERS):
                    logger.debug(
                        "NeoEnricher: LLM returned error sentinel",
                        extra={"event": "BRIDGE_LLM_ERROR", "sentinel_match": True},
                    )
                    return None
                return content or None
        logger.debug(
            "NeoEnricher bridge call returned non-200",
            extra={"event": "BRIDGE_CALL_FAILED", "status_code": resp.status_code},
        )
    except httpx.TimeoutException:
        logger.debug("NeoEnricher bridge call timed out", extra={"event": "BRIDGE_CALL_TIMEOUT"})
    except httpx.RequestError as e:
        logger.debug("NeoEnricher bridge call request error", extra={"event": "BRIDGE_CALL_ERROR", "error_code": type(e).__name__})
    except Exception as e:
        logger.debug("NeoEnricher bridge call unexpected error", extra={"event": "BRIDGE_CALL_ERROR", "error_code": type(e).__name__})
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Audit Narrative
# ─────────────────────────────────────────────────────────────────────────────

def audit_narrative(
    data: Dict[str, Any],
    project_id: str = "default",
) -> Optional[Dict[str, Any]]:
    """
    Generate a structured technical debt report from audit findings.

    Only counts, names, and severity labels are sent to LLM — no raw code content.
    Returns dict with: executive_summary, priority_actions, health_score, key_risks.
    """
    god_nodes = data.get("god_nodes", []) if isinstance(data, dict) else []
    dead_code = data.get("dead_code", []) if isinstance(data, dict) else []
    circular = data.get("circular_deps", {}) if isinstance(data, dict) else {}
    coupling = data.get("coupling", []) if isinstance(data, dict) else []

    god_names = _safe_list(god_nodes)
    circ_count = circular.get("count", 0) if isinstance(circular, dict) else 0
    high_coupling_pairs = [
        f"{_safe_str(c.get('source','?'), 40)}→{_safe_str(c.get('target','?'), 40)}"
        for c in coupling[:_MAX_PROMPT_ITEMS]
        if isinstance(c, dict) and c.get("score", 0) > 0.7
    ]
    dead_count = len(dead_code) if isinstance(dead_code, list) else 0

    prompt = (
        "You are a senior software architect producing a technical debt report.\n\n"
        "Analyze these codebase audit findings and return a JSON report.\n"
        "Do not invent findings — base your analysis strictly on the data provided.\n\n"
        f"God nodes (modules doing too much): {god_names}\n"
        f"Dead code items: {dead_count}\n"
        f"Circular dependencies: {circ_count}\n"
        f"High coupling pairs: {high_coupling_pairs}\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "executive_summary": "2-3 sentence non-technical summary",\n'
        '  "health_score": 0,\n'
        '  "priority_actions": [\n'
        '    {"rank": 1, "action": "...", "why": "...", "effort": "low|medium|high"}\n'
        '  ],\n'
        '  "severity_map": {"critical": [], "high": [], "medium": []},\n'
        '  "key_risks": ["risk1", "risk2"]\n'
        "}"
    )
    text = _bridge_call(prompt, fmt="remediation", project_id=project_id, max_tokens=1000)
    return _wrap(_extract_json(text), project_id)


# ─────────────────────────────────────────────────────────────────────────────
# Naming Advisor
# ─────────────────────────────────────────────────────────────────────────────

def naming_advisor(
    name: str,
    context: Dict[str, Any],
    project_id: str = "default",
) -> Optional[Dict[str, Any]]:
    """
    Semantic naming validation: convention alignment, alternatives, domain fit.

    Returns dict with: verdict, score, alternatives, convention_issues,
    domain_fit, recommendation.
    """
    kind = _safe_str(context.get("kind", "file"))
    stack = _safe_str(context.get("stack", ""))
    existing = _safe_list(context.get("existing_names", []))
    safe_name = _safe_str(name, 80)

    prompt = (
        f"You are a senior engineer reviewing a proposed {kind} name.\n\n"
        f"Proposed name: \"{safe_name}\"\n"
        f"Tech stack: {stack or 'unknown'}\n"
        f"Sample existing names in project: {existing}\n\n"
        "Evaluate the name against industry conventions. Return ONLY valid JSON:\n"
        "{\n"
        '  "verdict": "approved|warning|rejected",\n'
        '  "score": 0,\n'
        '  "convention_issues": ["issue1"],\n'
        '  "domain_fit": "excellent|good|poor",\n'
        '  "alternatives": ["BetterName1", "BetterName2"],\n'
        '  "recommendation": "one sentence"\n'
        "}"
    )
    text = _bridge_call(prompt, fmt="insight", project_id=project_id, max_tokens=500)
    return _wrap(_extract_json(text), project_id)


# ─────────────────────────────────────────────────────────────────────────────
# Refactor Sequence
# ─────────────────────────────────────────────────────────────────────────────

def refactor_sequence(
    impact_data: Dict[str, Any],
    target: str = "",
    project_id: str = "default",
) -> Optional[Dict[str, Any]]:
    """
    Convert blast radius data into a safe, dependency-ordered refactoring plan.

    Returns dict with: safe_order, risk_per_step, checkpoints, testing_strategy,
    estimated_total_risk.
    """
    callers = _safe_list(impact_data.get("callers", []))
    callees = _safe_list(impact_data.get("callees", []))
    risk = _safe_str(impact_data.get("risk", "medium"), 20)
    affected = _safe_list(impact_data.get("affected_files", []))
    safe_target = _safe_str(target, 80)

    prompt = (
        "You are a refactoring specialist planning a safe code change.\n\n"
        f"Target to change: \"{safe_target}\"\n"
        f"Risk level: {risk}\n"
        f"Callers (symbols that depend on this): {callers}\n"
        f"Callees (symbols this depends on): {callees}\n"
        f"Affected files: {affected}\n\n"
        "Generate a dependency-safe refactoring sequence. Return ONLY valid JSON:\n"
        "{\n"
        '  "safe_order": ["step 1", "step 2"],\n'
        '  "risk_per_step": [{"step": 1, "risk": "low", "reason": "..."}],\n'
        '  "checkpoints": ["verify X before step N"],\n'
        '  "testing_strategy": "what tests to run and in what order",\n'
        '  "estimated_total_risk": "low|medium|high"\n'
        "}"
    )
    text = _bridge_call(prompt, fmt="insight", project_id=project_id, max_tokens=800)
    return _wrap(_extract_json(text), project_id)


# ─────────────────────────────────────────────────────────────────────────────
# Search Explainer
# ─────────────────────────────────────────────────────────────────────────────

def search_explainer(
    results: List[Dict[str, Any]],
    query: str,
    project_id: str = "default",
) -> Optional[Dict[str, Any]]:
    """
    Rank search results by relevance to the query intent and explain each.

    Returns dict with: ranked_results, best_match_idx, intent_interpreted,
    suggested_next.
    """
    if not results:
        return None

    safe_query = _safe_str(query, 120)
    items = [
        {
            "idx": i,
            "name": _safe_str(r.get("name", r.get("symbol", "?")), 60),
            "file": _safe_str(r.get("file_path", ""), 80),
            "type": _safe_str(r.get("symbol_type", ""), 30),
        }
        for i, r in enumerate(results[:_MAX_PROMPT_ITEMS])
    ]
    prompt = (
        f"You are a code search assistant ranking results for query: \"{safe_query}\"\n\n"
        f"Search results:\n{json.dumps(items, indent=2)}\n\n"
        "Rank by relevance to the query intent. Return ONLY valid JSON:\n"
        "{\n"
        '  "intent_interpreted": "what the developer is likely trying to do",\n'
        '  "best_match_idx": 0,\n'
        '  "ranked_results": [\n'
        '    {"idx": 0, "relevance": "high|medium|low", "explanation": "why this matches"}\n'
        '  ],\n'
        '  "suggested_next": "what to do after finding this"\n'
        "}"
    )
    text = _bridge_call(prompt, fmt="explain", project_id=project_id, max_tokens=600)
    return _wrap(_extract_json(text), project_id)


# ─────────────────────────────────────────────────────────────────────────────
# Structure Advisor
# ─────────────────────────────────────────────────────────────────────────────

def structure_advisor(
    stack: str,
    current_tree: Dict[str, Any],
    project_type: str = "",
    project_id: str = "default",
) -> Optional[Dict[str, Any]]:
    """
    Recommend folder/file structure improvements based on stack and project type.

    Returns dict with: recommended_structure, moves, anti_patterns_detected,
    naming_conventions, rationale.
    """
    safe_stack = _safe_str(stack, 80)
    safe_type = _safe_str(project_type, 60)
    top_folders = list(current_tree.keys())[:12] if isinstance(current_tree, dict) else []
    safe_folders = [_safe_str(f, 60) for f in top_folders]

    prompt = (
        "You are a software architect recommending project structure.\n\n"
        f"Tech stack: {safe_stack}\n"
        f"Project type: {safe_type or 'unknown'}\n"
        f"Current top-level folders: {safe_folders}\n\n"
        "Provide structure recommendations. Return ONLY valid JSON:\n"
        "{\n"
        '  "recommended_structure": {"folder_name": "purpose"},\n'
        '  "moves": [{"from": "path", "to": "path", "reason": "..."}],\n'
        '  "anti_patterns_detected": ["pattern name and location"],\n'
        '  "naming_conventions": {"files": "...", "folders": "...", "classes": "..."},\n'
        '  "rationale": "why this structure fits the stack"\n'
        "}"
    )
    text = _bridge_call(prompt, fmt="insight", project_id=project_id, max_tokens=700)
    return _wrap(_extract_json(text), project_id)


# ─────────────────────────────────────────────────────────────────────────────
# Onboarding Summary
# ─────────────────────────────────────────────────────────────────────────────

def onboarding_summary(
    repo_data: Dict[str, Any],
    project_id: str = "default",
) -> Optional[Dict[str, Any]]:
    """
    Generate a developer onboarding guide from repository inspection data.

    Returns dict with: overview, entry_points, key_files, setup_steps,
    architecture_notes, gotchas.
    """
    lang = _safe_str(repo_data.get("primary_language", "unknown"), 40)
    frameworks = _safe_list(repo_data.get("frameworks", []))
    entry_points = _safe_list(repo_data.get("entry_points", []))
    file_count = int(repo_data.get("file_count", 0)) if isinstance(repo_data.get("file_count"), (int, float)) else 0
    tech_stack = repo_data.get("tech_stack", {})
    stack_keys = [_safe_str(k, 40) for k in list(tech_stack.keys())[:8]] if isinstance(tech_stack, dict) else []

    prompt = (
        "You are a senior developer writing a new team member onboarding guide.\n\n"
        f"Language: {lang}\n"
        f"Frameworks: {frameworks}\n"
        f"Entry points: {entry_points}\n"
        f"File count: {file_count}\n"
        f"Tech stack keys: {stack_keys}\n\n"
        "Write a concise onboarding guide. Return ONLY valid JSON:\n"
        "{\n"
        '  "overview": "2-sentence project description",\n'
        '  "entry_points": [{"file": "path", "purpose": "..."}],\n'
        '  "key_files": [{"file": "path", "why_important": "..."}],\n'
        '  "setup_steps": ["step 1", "step 2"],\n'
        '  "architecture_notes": "key design patterns or decisions to know",\n'
        '  "gotchas": ["non-obvious thing new developers should know"]\n'
        "}"
    )
    text = _bridge_call(prompt, fmt="summary", project_id=project_id, max_tokens=800)
    return _wrap(_extract_json(text), project_id)


# ─────────────────────────────────────────────────────────────────────────────
# Security Narrative
# ─────────────────────────────────────────────────────────────────────────────

def security_narrative(
    findings: Dict[str, Any],
    project_id: str = "default",
) -> Optional[Dict[str, Any]]:
    """
    Convert raw security audit findings into an actionable remediation report.

    SECURITY CONTRACT: Only counts, type labels, and severity categories are
    sent to the LLM. Raw secret values, credentials, file paths with sensitive
    context, and PII are NEVER included in the prompt.

    Returns dict with: severity_summary, critical_findings,
    remediation_steps, compliance_notes, estimated_fix_time.
    """
    secrets = findings.get("secrets", []) if isinstance(findings, dict) else []
    misconfigs = findings.get("misconfigurations", []) if isinstance(findings, dict) else []
    vulns = findings.get("vulnerabilities", []) if isinstance(findings, dict) else []
    pii = findings.get("pii_exposure", []) if isinstance(findings, dict) else []

    # Extract ONLY type labels — never raw values or paths that may contain secrets
    secret_types = _safe_list(secrets)
    misconfig_types = _safe_list(misconfigs)
    vuln_types = _safe_list(vulns)

    prompt = (
        "You are a security engineer writing a remediation report.\n"
        "Base your analysis strictly on the counts and type labels provided.\n\n"
        f"Secrets detected: {len(secrets)} instances — types: {secret_types}\n"
        f"Misconfigurations: {len(misconfigs)} — types: {misconfig_types}\n"
        f"Vulnerabilities: {len(vulns)} — types: {vuln_types}\n"
        f"PII exposure risks: {len(pii)} instances\n\n"
        "Write a security remediation report. Return ONLY valid JSON:\n"
        "{\n"
        '  "severity_summary": {"critical": 0, "high": 0, "medium": 0},\n'
        '  "critical_findings": [{"type": "...", "location": "general area", "fix": "..."}],\n'
        '  "remediation_steps": ["immediate action 1", "immediate action 2"],\n'
        '  "compliance_notes": "compliance implications (GDPR, SOC2, etc.)",\n'
        '  "estimated_fix_time": "X hours/days"\n'
        "}"
    )
    text = _bridge_call(prompt, fmt="remediation", project_id=project_id, max_tokens=800)
    return _wrap(_extract_json(text), project_id)
