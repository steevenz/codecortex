"""
Per-tool AI insight generators. Each function analyzes tool output and produces
structured guidance: summary, recommendations, next_actions, critical_issues.

Registered via @register_insight decorator from src.core.insight.

:project: CodeCortex
:package: Core.InsightGenerators
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.core.insight import AIInsight, register_insight, insight, _count, _found, _suggest_tool, _critical

logger = logging.getLogger(__name__)


def _neo_call(fn_name: str, *args, **kwargs) -> Any:
    """
    Safely invoke a NeoEnricher function.

    Catches all exceptions so a failing LLM call never breaks the
    rule-based insight fallback. Validates that the return value is a
    non-empty dict before returning it.
    """
    try:
        import importlib
        mod = importlib.import_module("src.core.cognitive.neo_enricher")
        fn = getattr(mod, fn_name, None)
        if fn is None:
            return None
        result = fn(*args, **kwargs)
        if result is not None and not isinstance(result, dict):
            logger.warning(
                "NeoEnricher returned unexpected type",
                extra={"event": "NEO_INVALID_RETURN", "fn": fn_name, "type": type(result).__name__},
            )
            return None
        return result or None
    except Exception as e:
        logger.debug(
            "NeoEnricher call skipped",
            extra={"event": "NEO_CALL_SKIPPED", "fn": fn_name, "error_code": type(e).__name__},
        )
        return None


# ══════════════════════════════════════════════════════════════
# CODEANALYSIS — 4 tools
# ══════════════════════════════════════════════════════════════

@register_insight("code_analyze")
def _code_analyze_insight(data: Dict, ctx: Dict) -> AIInsight:
    symbols = data.get("symbols", []) if isinstance(data, dict) else []
    edges = data.get("edges", []) if isinstance(data, dict) else []
    n_sym = len(symbols)
    n_edges = len(edges)
    n_calls = sum(1 for e in edges if isinstance(e, dict) and e.get("relation") == "CALLS")
    n_inherits = sum(1 for e in edges if isinstance(e, dict) and e.get("relation") == "INHERITS")

    recs = []
    next_acts = []
    critical = []

    if n_sym == 0:
        return AIInsight(summary="No symbols found. The target may be empty or non-code.", confidence="low")

    kinds = {}
    for s in symbols:
        k = s.get("kind", "unknown") if isinstance(s, dict) else "unknown"
        kinds[k] = kinds.get(k, 0) + 1

    summary = f"Found {n_sym} symbols ({', '.join(f'{v} {k}s' for k, v in sorted(kinds.items()))}), {n_edges} relationships"

    if n_calls > n_inherits * 5 and n_calls > 20:
        recs.append("High call coupling detected — consider dependency inversion")
    if n_inherits > 10:
        recs.append("Deep inheritance hierarchy — prefer composition over inheritance")
    if kinds.get("class", 0) > 50:
        recs.append(f"{kinds.get('class', 0)} classes may indicate SRP violations")

    if n_edges > 0:
        next_acts.append(_suggest_tool("code_audit", {"target": data.get("target", ""), "scan_categories": ["secrets", "misconfig"]}))

    return AIInsight(summary=summary, recommendations=recs, next_actions=next_acts,
                     critical_issues=critical, confidence="high" if n_sym > 0 else "low")


@register_insight("code_search")
def _code_search_insight(data: Dict, ctx: Dict) -> AIInsight:
    text = _found(data, "total_matches")
    sem = _found(data, "total_semantic")
    rel = _found(data, "total_relationships")
    parts = [f"{text} text matches"]
    if sem:
        parts.append(f"{sem} semantic hits")
    if rel:
        parts.append(f"{rel} relationships")
    summary = f"Search returned {', '.join(parts)}"
    recs = []
    if text == 0 and sem == 0:
        recs.append("Try semantic=True for concept-based search")
    if rel > 0:
        recs.append("Use graph_query with query_type=callers to explore relationships deeper")

    # [NEOCORTEX] Rank and explain results via LLM round-robin
    query = ctx.get("query", "")
    results = (data.get("results") or data.get("symbols") or []) if isinstance(data, dict) else []
    if query and isinstance(results, list) and results:
        neo = _neo_call("search_explainer", results, query, project_id=ctx.get("repo_id", "default"))
        if neo:
            intent = neo.get("intent_interpreted", "")
            if intent:
                summary = f"{summary} — {intent}"
            best_idx = neo.get("best_match_idx", 0)
            if isinstance(results, list) and isinstance(best_idx, int) and best_idx < len(results):
                best = results[best_idx]
                best_name = best.get("name", best.get("symbol", "?")) if isinstance(best, dict) else "?"
                recs.insert(0, f"Best match: '{best_name}' — {neo.get('suggested_next', '')}")

    return AIInsight(summary=summary, recommendations=recs, confidence="high" if text > 0 else "low")


@register_insight("code_audit")
def _code_audit_insight(data: Dict, ctx: Dict) -> AIInsight:
    score = data.get("compliance_score", 100) if isinstance(data, dict) else 100
    findings = data.get("findings", []) if isinstance(data, dict) else []
    scanned = data.get("scanned_files", 0) if isinstance(data, dict) else 0
    n_findings = len(findings)
    criticals = [f for f in findings if isinstance(f, dict) and f.get("severity") == "critical"]
    highs = [f for f in findings if isinstance(f, dict) and f.get("severity") == "high"]

    summary = f"Score {score}/100 — {n_findings} findings in {scanned} files ({len(criticals)} critical, {len(highs)} high)"
    recs = data.get("recommendations", []) if isinstance(data, dict) else []
    crit_issues = []
    for c in criticals[:5]:
        crit_issues.append(_critical(c.get("message", "Unknown"), file=c.get("file"), line=c.get("line"),
                                      remediation=c.get("remediation", "")))

    next_acts = []
    if score < 70:
        next_acts.append(_suggest_tool("code_refactor", {"action": "impact", "target_symbol": "::"}))

    return AIInsight(summary=summary, recommendations=list(recs), next_actions=next_acts,
                     critical_issues=crit_issues,
                     risk_level="high" if criticals else ("medium" if highs else "low"),
                     confidence="high" if scanned > 0 else "low")


@register_insight("code_status")
def _code_status_insight(data: Dict, ctx: Dict) -> AIInsight:
    summary = data.get("summary") if isinstance(data, dict) else None
    syms = data.get("symbols") if isinstance(data, dict) else None
    vcs = data.get("vcs") if isinstance(data, dict) else None
    files = (summary or {}).get("files", 0) if summary else 0
    loc = (summary or {}).get("code_lines", 0) if summary else 0
    ratio = (summary or {}).get("comment_ratio", 0) if summary else 0
    sym_total = sum(syms.values()) if isinstance(syms, dict) else 0
    vcs_type = (vcs or {}).get("type", "none") if vcs else "none"
    dirty = (vcs or {}).get("uncommitted_changes", 0) if vcs else 0

    summary_str = f"{files} files, {loc} LOC, {sym_total} symbols, comment ratio {ratio:.0%}, VCS: {vcs_type}"
    recs = []
    if ratio < 0.05 and loc > 1000:
        recs.append("Low documentation — consider adding docstrings")
    if dirty > 10:
        recs.append(f"{dirty} uncommitted changes — commit before refactoring")
    return AIInsight(summary=summary_str, recommendations=recs, confidence="high")


# ══════════════════════════════════════════════════════════════
# CODEGRAPH — 6 tools
# ══════════════════════════════════════════════════════════════

@register_insight("graph_search")
def _graph_search_insight(data: Dict, ctx: Dict) -> AIInsight:
    if isinstance(data, dict):
        for key in ("functions", "classes", "variables"):
            items = data.get(key, [])
            if isinstance(items, list) and items:
                total = sum(len(data.get(k, [])) for k in ("functions", "classes", "variables") if isinstance(data.get(k), list))
                return AIInsight(summary=f"Found {total} symbol(s) matching query", confidence="high")
    total = _count(data, "nodes", "results")
    return AIInsight(summary=f"Graph search returned {total} results", confidence="medium" if total else "low")


@register_insight("graph_query")
def _graph_query_insight(data: Dict, ctx: Dict) -> AIInsight:
    qt = ctx.get("query_type", "query")
    if isinstance(data, dict):
        for key in ("callers", "callees", "unused_functions", "path", "nodes"):
            val = data.get(key)
            if isinstance(val, list):
                n = len(val)
                return AIInsight(summary=f"Found {n} {key} via '{qt}'", confidence="high" if n > 0 else "medium")
            if key == "path" and isinstance(val, list):
                return AIInsight(summary=f"Trace path length: {len(val)}", confidence="high")
    return AIInsight(summary=f"Graph query '{qt}' completed", confidence="medium")


@register_insight("graph_audit")
def _graph_audit_insight(data: Dict, ctx: Dict) -> AIInsight:
    gods = data.get("god_nodes", []) if isinstance(data, dict) else []
    dd = data.get("dead_code", []) if isinstance(data, dict) else []
    circ = data.get("circular_deps", {}).get("count", 0) if isinstance(data, dict) else 0
    coupling = data.get("coupling", []) if isinstance(data, dict) else []

    summary_parts = []
    if isinstance(gods, list) and gods:
        summary_parts.append(f"{len(gods)} god nodes")
    if isinstance(dd, list) and dd:
        summary_parts.append(f"{len(dd)} dead code")
    if circ:
        summary_parts.append(f"{circ} circular deps")
    if isinstance(coupling, list) and coupling:
        high = sum(1 for c in coupling if isinstance(c, dict) and c.get("score", 0) > 0.7)
        if high:
            summary_parts.append(f"{high} strong couplings")

    summary = "Architecture audit: " + (", ".join(summary_parts) if summary_parts else "no issues found")
    recs = []
    crit = []

    if isinstance(gods, list):
        for g in gods[:3]:
            if isinstance(g, dict):
                recs.append(f"God node '{g.get('name', '?')}' — consider splitting (in-degree: {g.get('in_degree', 0)})")
    if circ:
        recs.append(f"{circ} circular dependencies — refactor to break cycles")
    if isinstance(coupling, list):
        for c in coupling[:3]:
            if isinstance(c, dict) and c.get("score", 0) > 0.8:
                crit.append(_critical(f"Unexpected coupling: {c.get('source', '?')} → {c.get('target', '?')} (score: {c.get('score', 0):.2f})"))

    next_acts = []
    if gods or circ:
        next_acts.append(_suggest_tool("code_refactor", {"action": "impact", "target_symbol": "::"}))

    # [NEOCORTEX] Generate structured audit narrative via LLM round-robin
    neo = None
    if isinstance(data, dict) and (gods or circ or coupling):
        neo = _neo_call("audit_narrative", data, project_id=ctx.get("repo_id", "default"))
    if neo:
        summary = neo.get("executive_summary", summary)
        for action in neo.get("priority_actions", [])[:3]:
            recs.append(f"[P{action.get('rank','')}] {action.get('action','')} — {action.get('why','')}")
        for risk in neo.get("key_risks", [])[:2]:
            crit.append(_critical(risk))

    return AIInsight(summary=summary, recommendations=recs, next_actions=next_acts,
                     critical_issues=crit, risk_level="high" if crit else ("medium" if recs else "low"))


@register_insight("graph_build")
def _graph_build_insight(data: Dict, ctx: Dict) -> AIInsight:
    stats = data.get("graph_stats", {}) if isinstance(data, dict) else {}
    nodes = stats.get("functions", 0) + stats.get("classes", 0) if isinstance(stats, dict) else 0
    edges = stats.get("calls", 0) + stats.get("inherits", 0) if isinstance(stats, dict) else 0
    summary = f"Graph built: ~{nodes} nodes, ~{edges} edges"
    return AIInsight(summary=summary, confidence="high",
                     next_actions=[_suggest_tool("graph_audit", {"repo_id": data.get("repo_id", "")})])


@register_insight("graph_relationship")
def _graph_relationship_insight(data: Dict, ctx: Dict) -> AIInsight:
    total = _found(data, "total")
    target = ctx.get("target_node", "")
    summary = f"Found {total} relationships for '{target}'" if total else f"No relationships for '{target}'"
    return AIInsight(summary=summary, confidence="high" if total else "low",
                     next_actions=[_suggest_tool("graph_query", {"query_type": "trace_flow", "target": target})] if total else [])


@register_insight("graph_refactor")
def _graph_refactor_insight(data: Dict, ctx: Dict) -> AIInsight:
    risk = (data or {}).get("impact", {}).get("risk", "unknown") if isinstance(data, dict) else "unknown"
    summary = f"Refactor impact analysis: risk={risk}"
    recs = []
    if risk == "high":
        recs.append("High risk — review blast radius before applying")
    return AIInsight(summary=summary, recommendations=recs, risk_level=risk if risk in ("low", "medium", "high") else "medium")


# ══════════════════════════════════════════════════════════════
# FILESYSTEM — 5 tools
# ══════════════════════════════════════════════════════════════

@register_insight("fs_manage")
def _fs_manage_insight(data: Dict, ctx: Dict) -> AIInsight:
    op = ctx.get("operation", "unknown")
    if isinstance(data, dict):
        written = data.get("written")
        if written is not None:
            path = data.get("path", "")
            size = data.get("size", 0)
            return AIInsight(summary=f"File {'' if written else 'not '}written: {path} ({size} bytes)", confidence="high")
        if data.get("content") is not None:
            return AIInsight(summary=f"Read file: {data.get('path', '?')} ({data.get('size', 0)} bytes)", confidence="high")
    return AIInsight(summary=f"Filesystem operation '{op}' completed", confidence="high")


@register_insight("fs_search")
def _fs_search_insight(data: Dict, ctx: Dict) -> AIInsight:
    results = data.get("results", []) if isinstance(data, dict) else []
    total = len(results) if isinstance(results, list) else 0
    content = ctx.get("content_regex", "")
    pattern = ctx.get("file_pattern", "*")
    summary = f"Found {total} files matching pattern='{pattern}'" + (f" + content='{content}'" if content else "")
    return AIInsight(summary=summary, confidence="high" if total else "low")


@register_insight("fs_watch")
def _fs_watch_insight(data: Dict, ctx: Dict) -> AIInsight:
    changes = data.get("changes", []) if isinstance(data, dict) else []
    n = len(changes) if isinstance(changes, list) else 0
    summary = f"Detected {n} filesystem change(s)"
    return AIInsight(summary=summary, confidence="high")


@register_insight("fs_df")
def _fs_df_insight(data: Dict, ctx: Dict) -> AIInsight:
    total = (data or {}).get("total_size", "0 B") if isinstance(data, dict) else "0 B"
    files = (data or {}).get("total_files", 0) if isinstance(data, dict) else 0
    summary = f"Disk usage: {total}, {files} files"
    recs = []
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        large = [i for i in data["items"] if isinstance(i, dict) and isinstance(i.get("size"), str) and "MB" in i.get("size", "")]
        if large:
            recs.append(f"Largest: {large[0].get('path', '?')} ({large[0].get('size', '?')})")
    return AIInsight(summary=summary, recommendations=recs, confidence="high")


@register_insight("fs_audit")
def _fs_audit_insight(data: Dict, ctx: Dict) -> AIInsight:
    total = _found(data, "total_findings")
    crit = []
    if isinstance(data, dict) and isinstance(data.get("findings"), list):
        crit = [f for f in data["findings"] if isinstance(f, dict) and f.get("severity") == "critical"]
    summary = f"Filesystem audit: {total} findings ({len(crit)} critical)"
    critical_issues = []
    for c in crit[:5]:
        critical_issues.append(_critical(c.get("message", "Sensitive file"), path=c.get("path", ""),
                                          recommendation=c.get("recommendation", "")))
    return AIInsight(summary=summary, critical_issues=critical_issues,
                     risk_level="high" if crit else "low", confidence="high")


# ══════════════════════════════════════════════════════════════
# CODEREPOSITORY
# ══════════════════════════════════════════════════════════════

@register_insight("repo_init")
def _repo_init_insight(data: Dict, ctx: Dict) -> AIInsight:
    rid = (data or {}).get("repo_id", "?") if isinstance(data, dict) else "?"
    summary = f"Repository initialized: {rid}"
    return AIInsight(summary=summary, confidence="high",
                     next_actions=[_suggest_tool("repo_analyze", {"repo_id": rid, "dry_run": True})])


@register_insight("repo_inspect")
def _repo_inspect_insight(data: Dict, ctx: Dict) -> AIInsight:  # noqa: C901
    score = (data or {}).get("insights", {}).get("ai_readiness_score", 0) if isinstance(data, dict) else 0
    idx = (data or {}).get("index_metadata", {}).get("indexed", False) if isinstance(data, dict) else False
    churn = (data or {}).get("git_diagnostics", {}).get("churn_hotspots", []) if isinstance(data, dict) else []
    bus = (data or {}).get("git_diagnostics", {}).get("bus_factor", {}) if isinstance(data, dict) else {}
    vcs = (data or {}).get("vcs_type", "none") if isinstance(data, dict) else "none"
    temporal = (data or {}).get("temporal_coupling", {}) if isinstance(data, dict) else {}

    recs = []
    next_acts = []
    crit = []

    if not idx:
        recs.append("Not indexed — run repo_init to enable AI features")
        next_acts.append(_suggest_tool("repo_init", {"repo_path": data.get("repo_path", "")}))
    if isinstance(churn, list) and churn:
        top = churn[0]
        if isinstance(top, dict) and top.get("risk") == "high":
            recs.append(f"Churn hotspot: {top.get('file', '?')} ({top.get('change_count', 0)} changes)")
    if isinstance(bus, dict) and bus.get("bus_factor_risk") == "high":
        recs.append("High bus factor risk — top contributor >60% of commits")
    if vcs == "none":
        recs.append("Not under version control — run git init")
    if isinstance(temporal, dict) and temporal.get("built"):
        hotspots = temporal.get("hotspots", [])
        if isinstance(hotspots, list):
            for h in hotspots[:2]:
                if isinstance(h, dict) and h.get("risk") == "high":
                    recs.append(f"Temporal hotspot: {h.get('file', '?')} couples with {h.get('co_change_partners', 0)} files")
    high_pairs = temporal.get("high_risk_pairs", 0) if isinstance(temporal, dict) else 0
    if high_pairs:
        crit.append(_critical(f"{high_pairs} high-risk temporal coupling pairs detected — refactor recommended"))

    # Documentation intelligence
    docs = (data or {}).get("documentation", {}) if isinstance(data, dict) else {}
    if isinstance(docs, dict) and not docs.get("error"):
        n_docs = docs.get("total_documents", 0)
        n_reqs = docs.get("total_requirements", 0)
        n_decisions = docs.get("total_decisions", 0)
        if n_docs:
            recs.append(f"Found {n_docs} documents, {n_reqs} requirements, {n_decisions} ADRs")
            if n_decisions == 0:
                recs.append("No ADRs found — start documenting architectural decisions")
            next_acts.append(_suggest_tool("docs", {"action": "summarize"}))

    summary = f"AI Readiness: {score}/100, indexed={idx}"
    risk_level = "high" if crit else ("medium" if high_pairs else "low")
    if score < 30:
        risk_level = "high"
    elif score < 60 and risk_level != "high":
        risk_level = "medium"

    # [NEOCORTEX] Generate developer onboarding summary via LLM round-robin
    if isinstance(data, dict) and score > 0:
        neo = _neo_call("onboarding_summary", data, project_id=ctx.get("repo_id", "default"))
        if neo:
            summary = neo.get("overview", summary)
            for step in neo.get("setup_steps", [])[:2]:
                recs.append(f"Setup: {step}")
            if neo.get("architecture_notes"):
                recs.append(f"Architecture: {neo['architecture_notes']}")
            for gotcha in neo.get("gotchas", [])[:2]:
                recs.append(f"Note: {gotcha}")

    return AIInsight(summary=summary, recommendations=recs, next_actions=next_acts,
                     critical_issues=crit, risk_level=risk_level)


@register_insight("repo_analyze")
def _repo_analyze_insight(data: Dict, ctx: Dict) -> AIInsight:
    idx = (data or {}).get("indexing_summary", {}) if isinstance(data, dict) else {}
    graph = (data or {}).get("graph_summary", {}) if isinstance(data, dict) else {}
    embed = (data or {}).get("embedding_status", "disabled") if isinstance(data, dict) else "disabled"
    graph_ready = (data or {}).get("graph_ready", False) if isinstance(data, dict) else False
    search_ready = (data or {}).get("search_ready", False) if isinstance(data, dict) else False
    recs = data.get("recommendations", []) if isinstance(data, dict) else []

    n_files = idx.get("total_files_scanned", 0) if isinstance(idx, dict) else 0
    n_sym = idx.get("symbols_extracted", 0) if isinstance(idx, dict) else 0
    n_edges = idx.get("edges_built", 0) if isinstance(idx, dict) else 0
    n_nodes = graph.get("total_nodes", 0) if isinstance(graph, dict) else 0
    elapsed = (data or {}).get("duration_seconds", 0)

    summary = f"Analysis: {n_files} files, {n_sym} symbols, {n_edges} edges in {elapsed}s"
    next_acts = []

    if graph_ready:
        next_acts.append(_suggest_tool("graph_audit", {"repo_id": data.get("repo_id", "")}))
    if search_ready:
        next_acts.append(_suggest_tool("code_search", {"query": "entry point", "repo_id": data.get("repo_id", "")}))
    if embed == "disabled":
        next_acts.append(_suggest_tool("repo_analyze", {"repo_path": data.get("repo_path", ""), "store_embeddings": True, "dry_run": True}))

    return AIInsight(summary=summary, recommendations=list(recs), next_actions=next_acts,
                     confidence="high" if n_files > 0 else "low")


@register_insight("repo_sync")
def _repo_sync_insight(data: Dict, ctx: Dict) -> AIInsight:
    summary_data = (data or {}).get("changes_summary", {}) if isinstance(data, dict) else {}
    added = summary_data.get("added", 0) if isinstance(summary_data, dict) else 0
    modified = summary_data.get("modified", 0) if isinstance(summary_data, dict) else 0
    deleted = summary_data.get("deleted", 0) if isinstance(summary_data, dict) else 0
    total = added + modified + deleted
    summary = f"Sync: +{added} -{deleted} ~{modified} ({total} total changes)"
    return AIInsight(summary=summary, confidence="high")


@register_insight("repo_list")
def _repo_list_insight(data: Dict, ctx: Dict) -> AIInsight:
    repos = data.get("repositories", []) if isinstance(data, dict) else []
    n = len(repos) if isinstance(repos, list) else 0
    summary = f"{n} registered repositories"
    next_acts = []
    if n == 0:
        next_acts.append(_suggest_tool("repo_init", {"repo_path": "/path/to/project"}))
    return AIInsight(summary=summary, next_actions=next_acts, confidence="high")


@register_insight("repo_audit")
def _repo_audit_insight(data: Dict, ctx: Dict) -> AIInsight:
    findings = data.get("findings", []) if isinstance(data, dict) else []
    n = len(findings) if isinstance(findings, list) else 0
    summary = f"Security audit: {n} findings"
    recs, crit = [], []

    # [NEOCORTEX] Generate security remediation narrative via LLM round-robin
    if n > 0 and isinstance(data, dict):
        neo = _neo_call("security_narrative", data, project_id=ctx.get("repo_id", "default"))
        if neo:
            sev = neo.get("severity_summary", {})
            summary = (f"Security audit: {n} findings "
                       f"({sev.get('critical',0)} critical, {sev.get('high',0)} high)")
            for step in neo.get("remediation_steps", [])[:3]:
                recs.append(step)
            for finding in neo.get("critical_findings", [])[:3]:
                crit.append(_critical(
                    f"{finding.get('type','?')} at {finding.get('location','?')}",
                    fix=finding.get("fix", "")
                ))
            if neo.get("compliance_notes"):
                recs.append(f"Compliance: {neo['compliance_notes']}")

    return AIInsight(summary=summary, recommendations=recs, critical_issues=crit,
                     risk_level="high" if n > 0 else "low", confidence="high")


@register_insight("repo_compact")
def _repo_compact_insight(data: Dict, ctx: Dict) -> AIInsight:
    freed = (data or {}).get("freed_bytes", 0) if isinstance(data, dict) else 0
    summary = f"Database compacted: freed {freed} bytes" if freed else "Database compacted"
    return AIInsight(summary=summary, confidence="high")


@register_insight("repo_cleanup")
def _repo_cleanup_insight(data: Dict, ctx: Dict) -> AIInsight:
    rid = (data or {}).get("repo_id", "?") if isinstance(data, dict) else "?"
    return AIInsight(summary=f"Repository {rid} deleted", risk_level="high", confidence="high")


# ══════════════════════════════════════════════════════════════
# CODEREFACTOR
# ══════════════════════════════════════════════════════════════

@register_insight("code_refactor")
def _code_refactor_insight(data: Dict, ctx: Dict) -> AIInsight:
    status = (data or {}).get("status", "") if isinstance(data, dict) else ""
    action = (data or {}).get("action", "") if isinstance(data, dict) else ""
    blast = (data or {}).get("blast_radius", {}) if isinstance(data, dict) else {}
    changes = data.get("changes", []) if isinstance(data, dict) else []
    commit = (data or {}).get("commit_hash") if isinstance(data, dict) else None

    n_changes = len(changes) if isinstance(changes, list) else 0
    n_files = (blast or {}).get("files_affected", 0) if isinstance(blast, dict) else 0
    risk = (blast or {}).get("risk", "low") if isinstance(blast, dict) else "low"

    summary = f"Refactor '{action}': {n_changes} changes across {n_files} files, risk={risk}"
    if commit:
        summary += f", committed: {commit[:8]}"

    recs = []
    if status == "error":
        return AIInsight(summary=f"Refactoring failed: {data.get('message', '')}", risk_level="high", confidence="high")
    if risk == "high" and not commit:
        recs.append("High blast radius — review changes before applying")
        recs.append("Call with action=preview to see diff")

    # [NEOCORTEX] Generate safe refactoring sequence via LLM round-robin
    if isinstance(blast, dict) and blast and not commit:
        neo = _neo_call("refactor_sequence", blast,
                        target=ctx.get("target_symbol", action),
                        project_id=ctx.get("repo_id", "default"))
        if neo:
            for i, step in enumerate(neo.get("safe_order", [])[:4], 1):
                recs.append(f"Step {i}: {step}")
            if neo.get("testing_strategy"):
                recs.append(f"Testing: {neo['testing_strategy']}")
            neo_risk = neo.get("estimated_total_risk", "")
            if neo_risk in ("low", "medium", "high"):
                risk = neo_risk

    return AIInsight(summary=summary, recommendations=recs,
                     risk_level=risk if risk in ("low", "medium", "high") else "medium",
                     next_actions=[] if commit else [_suggest_tool("code_refactor",
                     {"action": "apply" if action != "apply" else "impact", "target_symbol": "::"})],
                     confidence="high")


# ══════════════════════════════════════════════════════════════
# CODETESTER
# ══════════════════════════════════════════════════════════════

@register_insight("code_tester")
def _code_tester_insight(data: Dict, ctx: Dict) -> AIInsight:
    act = ctx.get("action", "")
    if act == "discover":
        frameworks = data.get("frameworks", []) if isinstance(data, dict) else []
        n_files = _found(data, "total")
        summary = f"Discovered {n_files} test files, frameworks: {', '.join(frameworks)}" if isinstance(frameworks, list) else f"Discovered {n_files} test files"
        next_acts = []
        if n_files:
            next_acts.append(_suggest_tool("code_tester", {"action": "run", "files": data.get("test_files", [])}))
        return AIInsight(summary=summary, next_actions=next_acts, confidence="high" if n_files else "low")
    elif act == "run":
        summary_data = data.get("summary", {}) if isinstance(data, dict) else {}
        passed = (summary_data or {}).get("passed", 0)
        failed = (summary_data or {}).get("failed", 0)
        skipped = (summary_data or {}).get("skipped", 0)
        summary = f"Tests: {passed} passed, {failed} failed, {skipped} skipped"
        recs = []
        if failed:
            recs.append(f"{failed} test(s) failing — investigate before proceeding")
        return AIInsight(summary=summary, recommendations=recs, risk_level="high" if failed else "low")
    elif act == "coverage":
        cov = _found(data, "coverage_percent")
        summary = f"Code coverage: {cov}%"
        recs = []
        if cov < 60:
            recs.append("Low coverage (<60%) — prioritize adding tests")
        return AIInsight(summary=summary, recommendations=recs, risk_level="high" if cov < 40 else "medium" if cov < 60 else "low")
    return AIInsight(summary=f"Test action '{act}' completed", confidence="medium")


# ══════════════════════════════════════════════════════════════
# CODEINDEX
# ══════════════════════════════════════════════════════════════

@register_insight("code_index")
def _code_index_insight(data: Dict, ctx: Dict) -> AIInsight:
    act = ctx.get("action", "")
    if act == "status":
        indexed = (data or {}).get("indexed", False) if isinstance(data, dict) else False
        pending = (data or {}).get("pending_files", 0) if isinstance(data, dict) else 0
        summary = f"Index status: {'indexed' if indexed else 'not indexed'}"
        if pending:
            summary += f", {pending} pending files"
        return AIInsight(summary=summary, confidence="high")
    elif act == "build":
        n = _found(data, "files_indexed")
        summary = f"Indexed {n} files"
        return AIInsight(summary=summary, confidence="high")
    return AIInsight(summary=f"Index action '{act}' completed", confidence="high")


# ══════════════════════════════════════════════════════════════
# SCAFFOLDER — 7 tools
# ══════════════════════════════════════════════════════════════

@register_insight("scaffold_list_stacks")
def _sc_list_stacks_insight(data: Dict, ctx: Dict) -> AIInsight:
    stacks = data.get("stacks", []) if isinstance(data, dict) else []
    n = len(stacks) if isinstance(stacks, list) else 0
    names = [s.get("display_name", s.get("name", "?")) for s in stacks[:5]] if isinstance(stacks, list) else []
    summary = f"{n} stacks available: {', '.join(names)}"
    return AIInsight(summary=summary, confidence="high",
                     next_actions=[_suggest_tool("scaffold_get_stack", {"stack_name": names[0]})] if names else [])


@register_insight("scaffold_get_stack")
def _sc_get_stack_insight(data: Dict, ctx: Dict) -> AIInsight:
    stack = data.get("stack", {}) if isinstance(data, dict) else {}
    name = (stack or {}).get("display_name", "?") if isinstance(stack, dict) else "?"
    pts = (stack or {}).get("project_types", []) if isinstance(stack, dict) else []
    n_pts = len(pts) if isinstance(pts, list) else 0
    summary = f"Stack '{name}' — {n_pts} project types"
    return AIInsight(summary=summary, confidence="high")


@register_insight("scaffold_validate_name")
def _sc_validate_name_insight(data: Dict, ctx: Dict) -> AIInsight:
    display = (data or {}).get("display", "?") if isinstance(data, dict) else "?"
    slug = (data or {}).get("slug", "?") if isinstance(data, dict) else "?"
    summary = f"Name '{display}' is valid → slug: '{slug}'"
    recs = []

    # [NEOCORTEX] Semantic naming validation via LLM round-robin
    neo = _neo_call("naming_advisor", display,
                    context={
                        "kind": ctx.get("kind", "project"),
                        "stack": ctx.get("stack", ""),
                        "repo_path": ctx.get("repo_path", ""),
                        "existing_names": ctx.get("existing_names", []),
                    },
                    project_id=ctx.get("repo_id", "default"))
    if neo:
        verdict = neo.get("verdict", "approved")
        score = neo.get("score", 100)
        alts = neo.get("alternatives", [])
        rec = neo.get("recommendation", "")
        summary = f"Name '{display}' — {verdict} (score: {score}/100)"
        if rec:
            recs.append(rec)
        if alts:
            recs.append(f"Alternatives: {', '.join(alts[:3])}")
        for issue in neo.get("convention_issues", [])[:2]:
            recs.append(f"Convention: {issue}")

    return AIInsight(summary=summary, recommendations=recs, confidence="high",
                     next_actions=[_suggest_tool("scaffold_create", {"name": slug, "dry_run": True})])


@register_insight("scaffold_list_licenses")
def _sc_list_licenses_insight(data: Dict, ctx: Dict) -> AIInsight:
    licenses = data.get("licenses", []) if isinstance(data, dict) else []
    n = len(licenses) if isinstance(licenses, list) else 0
    names = [l.get("id", "?") for l in licenses[:5]] if isinstance(licenses, list) else []
    summary = f"{n} license types: {', '.join(names)}"
    return AIInsight(summary=summary, confidence="high")


@register_insight("scaffold_generate")
def _sc_generate_insight(data: Dict, ctx: Dict) -> AIInsight:
    fn = (data or {}).get("filename", "?") if isinstance(data, dict) else "?"
    length = (data or {}).get("content_length", 0) if isinstance(data, dict) else 0
    summary = f"Generated '{fn}' ({length} chars)"
    return AIInsight(summary=summary, confidence="high")


@register_insight("scaffold_make")
def _sc_make_insight(data: Dict, ctx: Dict) -> AIInsight:
    cn = (data or {}).get("class_name", "?") if isinstance(data, dict) else "?"
    tp = (data or {}).get("type_display", "?") if isinstance(data, dict) else "?"
    rp = (data or {}).get("relative_path", "?") if isinstance(data, dict) else "?"
    written = (data or {}).get("written", False) if isinstance(data, dict) else False
    summary = f"Generated {tp} '{cn}' at {rp}" + (" (written)" if written else " (preview)")
    recs = []

    # [NEOCORTEX] Validate generated name + suggest better location via LLM round-robin
    if cn and cn != "?":
        neo = _neo_call("naming_advisor", cn,
                        context={"kind": tp or "class", "stack": ctx.get("stack", ""), "repo_path": ctx.get("repo_path", "")},
                        project_id=ctx.get("repo_id", "default"))
        if neo:
            verdict = neo.get("verdict", "approved")
            alts = neo.get("alternatives", [])
            rec = neo.get("recommendation", "")
            if verdict != "approved" and alts:
                recs.append(f"Name suggestion: consider '{alts[0]}' instead of '{cn}'")
            if rec:
                recs.append(rec)
            if neo.get("domain_fit") == "poor":
                recs.append("Domain fit is poor — name may not reflect the class responsibility")

    return AIInsight(summary=summary, recommendations=recs, confidence="high")


@register_insight("scaffold_create")
def _sc_create_insight(data: Dict, ctx: Dict) -> AIInsight:
    if isinstance(data, dict):
        if data.get("dry_run"):
            n_templates = data.get("template_count", 0)
            n_dirs = data.get("directory_count", 0)
            stack = data.get("stack", "?")
            summary = f"Dry-run: {stack} project ready — {n_templates} templates, {n_dirs} directories"
            recs = []

            # [NEOCORTEX] Recommend structure improvements via LLM round-robin
            tree = data.get("directory_tree", data.get("structure", {}))
            if isinstance(tree, dict) and tree:
                neo = _neo_call("structure_advisor",
                                stack=stack, current_tree=tree,
                                project_type=ctx.get("project_type", ""),
                                project_id=ctx.get("repo_id", "default"))
                if neo:
                    if neo.get("rationale"):
                        recs.append(neo["rationale"])
                    for ap in neo.get("anti_patterns_detected", [])[:2]:
                        recs.append(f"Anti-pattern: {ap}")
                    conv = neo.get("naming_conventions", {})
                    if conv:
                        recs.append(f"Conventions: files={conv.get('files','?')}, classes={conv.get('classes','?')}")

            return AIInsight(summary=summary, recommendations=recs, confidence="high",
                             next_actions=[_suggest_tool("scaffold_create", {
                                 "name": data.get("name", {}).get("slug", ""),
                                 "stack": stack, "dry_run": False})])
        progress = data.get("progress", [])
        n_steps = len(progress) if isinstance(progress, list) else 0
        summary = f"Project scaffolded in {n_steps} steps"
        return AIInsight(summary=summary, confidence="high")
    return AIInsight(summary="Project scaffolding completed", confidence="high")


# ══════════════════════════════════════════════════════════════
# UNIFIED API tools (action-based)
# ══════════════════════════════════════════════════════════════

@register_insight("codecortex_repository")
def _unified_repo_insight(data: Dict, ctx: Dict) -> AIInsight:
    action = ctx.get("action", "unknown")
    rid = (data or {}).get("repo_id") if isinstance(data, dict) else None
    summary = f"Repository action '{action}' completed"
    next_acts = []
    if action == "init" and rid:
        next_acts.append(_suggest_tool("codecortex:repository", {"action": "analyze", "repo_path": data.get("repo_path", "")}))
    return AIInsight(summary=summary, next_actions=next_acts, confidence="high")


@register_insight("codecortex_filesystem")
def _unified_fs_insight(data: Dict, ctx: Dict) -> AIInsight:
    action = ctx.get("action", "unknown")
    return AIInsight(summary=f"Filesystem action '{action}' completed", confidence="high")


@register_insight("codecortex_codebase")
def _unified_cb_insight(data: Dict, ctx: Dict) -> AIInsight:
    action = ctx.get("action", "unknown")
    return AIInsight(summary=f"Codebase action '{action}' completed", confidence="high")


@register_insight("codecortex_scaffolder")
def _unified_sc_insight(data: Dict, ctx: Dict) -> AIInsight:
    action = ctx.get("action", "unknown")
    return AIInsight(summary=f"Scaffolder action '{action}' completed", confidence="high",
                     next_actions=[_suggest_tool("codecortex:scaffolder", {"action": "list_stacks"})] if action == "list_stacks" else [])


@register_insight("codecortex_idegraph")
def _unified_ig_insight(data: Dict, ctx: Dict) -> AIInsight:
    action = ctx.get("action", "unknown")
    return AIInsight(summary=f"IDE Graph action '{action}' completed", confidence="high")


# ══════════════════════════════════════════════════════════════
# GOLDEN KNOWLEDGE
# ══════════════════════════════════════════════════════════════

@register_insight("golden_knowledge")
def _golden_knowledge_insight(data: Dict, ctx: Dict) -> AIInsight:
    total = (data or {}).get("total_entries", 0) if isinstance(data, dict) else 0
    by_type = (data or {}).get("by_type", {}) if isinstance(data, dict) else {}
    summary = f"Golden knowledge: {total} entries ({', '.join(f'{v} {k}s' for k, v in by_type.items())})" if total else "No golden knowledge stored"
    recs = []
    if total == 0:
        recs.append("Extract golden knowledge from ADRs and standards")
    next_acts = []
    if total:
        next_acts.append(_suggest_tool("code_analyze", {"target": "", "mode": "overview"}))
    return AIInsight(summary=summary, recommendations=recs, next_actions=next_acts,
                     confidence="high" if total else "low")


# ══════════════════════════════════════════════════════════════
# DATA FLOW TRACING
# ══════════════════════════════════════════════════════════════

@register_insight("trace_variable")
@register_insight("trace_function_param")
def _trace_insight(data: Dict, ctx: Dict) -> AIInsight:
    var = (data or {}).get("variable", "?") if isinstance(data, dict) else "?"
    n_sources = len(data.get("sources", [])) if isinstance(data, dict) else 0
    n_sinks = len(data.get("sinks", [])) if isinstance(data, dict) else 0
    n_transforms = len(data.get("transformations", [])) if isinstance(data, dict) else 0
    flow = data.get("flow_path", []) if isinstance(data, dict) else []
    summary = f"Variable '{var}': {n_sources} sources → {n_transforms} transforms → {n_sinks} sinks"
    recs = []
    if n_sources == 0:
        recs.append("Variable source not found — may be external input")
    if n_sinks == 0:
        recs.append("Variable not used further — possible dead code")
    return AIInsight(summary=summary, recommendations=recs, confidence="high")


# ══════════════════════════════════════════════════════════════
# EXECUTION TRACING / OPERATIONAL LAYER
# ══════════════════════════════════════════════════════════════

@register_insight("trace_execution")
@register_insight("get_call_chain")
def _execution_trace_insight(data: Dict, ctx: Dict) -> AIInsight:
    func = (data or {}).get("function") or (data or {}).get("root", "?") if isinstance(data, dict) else "?"
    paths = (data or {}).get("estimated_paths", 0) if isinstance(data, dict) else 0
    branches = len(data.get("branches", [])) if isinstance(data, dict) else 0
    calls = len(data.get("internal_calls", [])) if isinstance(data, dict) else 0
    chain_depth = (data or {}).get("depth", 0) if isinstance(data, dict) else 0
    summary = f"Function '{func}': ~{paths} paths, {branches} branches, {calls} calls"
    if chain_depth:
        summary += f", chain depth={chain_depth}"
    recs = []
    if paths > 10:
        recs.append(f"High cyclomatic complexity (~{paths} paths) — consider splitting")
    return AIInsight(summary=summary, recommendations=recs,
                     risk_level="high" if paths > 20 else "medium" if paths > 10 else "low")


# ══════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH (4 actions)
# ══════════════════════════════════════════════════════════════

@register_insight("knowledge_extract")
def _knowledge_extract_insight(data: Dict, ctx: Dict) -> AIInsight:
    n = (data or {}).get("chunks_extracted", 0) if isinstance(data, dict) else 0
    docs = (data or {}).get("documents_scanned", 0) if isinstance(data, dict) else 0
    by_type = (data or {}).get("by_type", {}) if isinstance(data, dict) else {}
    summary = f"Extracted {n} knowledge items from {docs} docs"
    if by_type:
        summary += f" ({', '.join(f'{v} {k}s' for k, v in by_type.items())})"
    recs = []
    if n == 0:
        recs.append("No knowledge extracted — check docs/ directory")
    next_acts = []
    if n:
        next_acts.append({"action": "query", "params": {"task": "architecture overview"}})
    return AIInsight(summary=summary, recommendations=recs, next_actions=next_acts, confidence="high" if n else "low")


@register_insight("knowledge_query")
def _knowledge_query_insight(data: Dict, ctx: Dict) -> AIInsight:
    total = (data or {}).get("total", 0) if isinstance(data, dict) else 0
    task = ""
    if isinstance(data, dict):
        q = data.get("query", {})
        if isinstance(q, dict):
            task = q.get("task", "")
    summary = f"Found {total} knowledge items" + (f" for '{task}'" if task else "")
    recs = []
    if total == 0:
        recs.append("No relevant knowledge — try extract action first")
    return AIInsight(summary=summary, recommendations=recs, confidence="high" if total else "low")


@register_insight("knowledge_status")
def _knowledge_status_insight(data: Dict, ctx: Dict) -> AIInsight:
    total = (data or {}).get("total_chunks", 0) if isinstance(data, dict) else 0
    summary = f"Knowledge store: {total} chunks" if total else "No knowledge stored yet"
    recs = []
    if total == 0:
        recs.append("Run knowledge_graph extract to build knowledge base")
    return AIInsight(summary=summary, recommendations=recs, confidence="high")


@register_insight("knowledge_relationships")
def _knowledge_relationships_insight(data: Dict, ctx: Dict) -> AIInsight:
    edges = (data or {}).get("edges", []) if isinstance(data, dict) else []
    n = len(edges) if isinstance(edges, list) else 0
    focus = (data or {}).get("focus", "all") if isinstance(data, dict) else "all"
    summary = f"Knowledge graph: {n} relationships (focus: {focus})"
    return AIInsight(summary=summary, confidence="high")


# ---------------------------------------------------------------------------
# IDE Graph insight generators
# ---------------------------------------------------------------------------

@register_insight("idegraph_search")
def _idegraph_search_insight(data: Dict, ctx: Dict) -> AIInsight:
    count = (data or {}).get("count", 0) if isinstance(data, dict) else 0
    summary = f"Found {count} IDE memories" if count else "No IDE memories found"
    recs = []
    if count == 0:
        recs.append("Run idegraph ingest to harvest IDE conversations")
    return AIInsight(summary=summary, recommendations=recs, confidence="high")


@register_insight("idegraph_get")
def _idegraph_get_insight(data: Dict, ctx: Dict) -> AIInsight:
    source = ""
    if isinstance(data, dict) and "attributes" in data:
        source = data["attributes"].get("source", "")
    summary = f"Retrieved IDE memory from {source}" if source else "IDE memory retrieved"
    return AIInsight(summary=summary, confidence="high")


@register_insight("idegraph_list")
def _idegraph_list_insight(data: Dict, ctx: Dict) -> AIInsight:
    items = (data or {}).get("items", []) if isinstance(data, dict) else []
    summary = f"Listed {len(items)} IDE memories"
    return AIInsight(summary=summary, confidence="high")


@register_insight("idegraph_ingest")
def _idegraph_ingest_insight(data: Dict, ctx: Dict) -> AIInsight:
    summary_data = (data or {}).get("summary", {}) if isinstance(data, dict) else {}
    total = summary_data.get("total_engrams", 0) if isinstance(summary_data, dict) else 0
    summary = f"Ingested {total} cross-IDE memories"
    recs = []
    if total > 0:
        recs.append("Use idegraph search to query harvested memories")
    return AIInsight(summary=summary, recommendations=recs, confidence="high")


@register_insight("idegraph_refresh")
def _idegraph_refresh_insight(data: Dict, ctx: Dict) -> AIInsight:
    matched = (data or {}).get("result", {}).get("matched_engrams", 0) if isinstance(data, dict) else 0
    summary = f"Refreshed {matched} engrams for project"
    return AIInsight(summary=summary, confidence="high")


@register_insight("idegraph_health")
def _idegraph_health_insight(data: Dict, ctx: Dict) -> AIInsight:
    status = (data or {}).get("status", "unknown") if isinstance(data, dict) else "unknown"
    convs = (data or {}).get("conversations", 0) if isinstance(data, dict) else 0
    summary = f"IDE Graph health: {status} ({convs} conversations)"
    c = "medium" if status == "degraded" else "high"
    return AIInsight(summary=summary, confidence=c)


@register_insight("idegraph_stats")
def _idegraph_stats_insight(data: Dict, ctx: Dict) -> AIInsight:
    by_ide = (data or {}).get("by_ide", []) if isinstance(data, dict) else []
    total = sum(r.get("engrams", 0) for r in by_ide)
    summary = f"Ingestion stats: {total} engrams across {len(by_ide)} IDEs"
    return AIInsight(summary=summary, confidence="high")


@register_insight("idegraph_compact")
def _idegraph_compact_insight(data: Dict, ctx: Dict) -> AIInsight:
    total = (data or {}).get("total", 0) if isinstance(data, dict) else 0
    summary = f"Compacted {total} conversations via local LLM"
    return AIInsight(summary=summary, confidence="medium")


@register_insight("idegraph_workspace")
def _idegraph_workspace_insight(data: Dict, ctx: Dict) -> AIInsight:
    ws_key = (data or {}).get("workspace_key", "unknown") if isinstance(data, dict) else "unknown"
    summary = f"Workspace: {ws_key}"
    return AIInsight(summary=summary, confidence="high")


@register_insight("idegraph_harvest")
def _idegraph_harvest_insight(data: Dict, ctx: Dict) -> AIInsight:
    if not isinstance(data, dict):
        data = {}
    ides = data.get("ides", 0)
    configs = data.get("configs", 0)
    summary = f"Harvested {ides} IDEs, {configs} configurations"
    return AIInsight(summary=summary, confidence="high")
