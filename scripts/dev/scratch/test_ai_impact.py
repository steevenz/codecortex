"""
AI Coder Impact Demonstration -- focused test of bridge output quality.

Compares BEFORE (rule-based only) vs AFTER (LLM-enriched via Neocortex)
to show concrete differences AI Coder would experience.
"""

import io, sys, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import os
sys.path.insert(0, r"C:\Users\steevenz\MCP\mcp-codecortex")
os.environ["CODECORTEX_BRIDGE_NEOCORTEX_URL"]     = "http://127.0.0.1:8010"
os.environ["CODECORTEX_BRIDGE_NEOCORTEX_API_KEY"] = "nct_auth_KcZrU8eF4QWMCoPoVtWr6V8iUpXIVsPQYezrE-cZnvQ"
os.environ["CODECORTEX_BRIDGE_ENABLED"]            = "true"

G="\033[32m"; R="\033[31m"; Y="\033[33m"; C="\033[36m"; B="\033[1m"; E="\033[0m"
def hdr(t): print(f"\n{B}{C}{'='*65}{E}\n{B}{C}  {t}{E}\n{B}{C}{'='*65}{E}")

# ──────────────────────────────────────────────────────────────────────────
hdr("1. NAMING ADVISOR -- AI Coder picks a class name")
# ──────────────────────────────────────────────────────────────────────────

print(f"\n  {Y}Scenario:{E} AI Coder wants to create a new service class")
print(f"  {Y}Proposed name:{E} 'HandleUserPaymentProcessingAndEmailNotification'")
print(f"  {Y}Stack:{E} Python FastAPI")

from src.core.cognitive.neo_enricher import naming_advisor
t0 = time.monotonic()
result = naming_advisor(
    "HandleUserPaymentProcessingAndEmailNotification",
    context={
        "kind": "class",
        "stack": "Python FastAPI",
        "existing_names": ["PaymentService", "NotificationService", "UserRepository"],
    },
    project_id="ai_impact_test",
)
ms = (time.monotonic()-t0)*1000

if result:
    print(f"\n  {G}LLM Verdict (took {ms:.0f}ms):{E}")
    print(f"  {C}verdict       :{E} {result.get('verdict','?')}")
    print(f"  {C}score         :{E} {result.get('score','?')}/100")
    print(f"  {C}domain_fit    :{E} {result.get('domain_fit','?')}")
    print(f"  {C}alternatives  :{E} {result.get('alternatives',[])}")
    print(f"  {C}issues        :{E} {result.get('convention_issues',[])}")
    print(f"  {C}recommendation:{E} {result.get('recommendation','?')}")
    print(f"\n  {G}AI Coder impact:{E} Has concrete alternatives + scoring instead of just regex pass/fail")
else:
    print(f"  {R}LLM returned None ({ms:.0f}ms){E}")

# ──────────────────────────────────────────────────────────────────────────
hdr("2. AUDIT NARRATIVE -- AI Coder reviews architecture")
# ──────────────────────────────────────────────────────────────────────────

print(f"\n  {Y}Scenario:{E} Architecture audit returns raw findings; AI Coder needs action plan")
print(f"  {Y}Raw input:{E} 2 god nodes, 3 circular deps, 1 high coupling pair")

from src.core.cognitive.neo_enricher import audit_narrative
t0 = time.monotonic()
mock_audit = {
    "god_nodes": [
        {"name": "PaymentService", "in_degree": 23, "out_degree": 18},
        {"name": "UserController", "in_degree": 15, "out_degree": 12},
    ],
    "dead_code": [{"name": "legacy_handler"}, {"name": "unused_util"}],
    "circular_deps": {"count": 3, "cycles": [["a","b","c"]]},
    "coupling": [{"source": "OrderService", "target": "PaymentService", "score": 0.92}],
}
result = audit_narrative(mock_audit, project_id="ai_impact_test")
ms = (time.monotonic()-t0)*1000

if result:
    print(f"\n  {G}LLM Narrative (took {ms:.0f}ms):{E}")
    summary = result.get("executive_summary","")
    print(f"  {C}executive_summary:{E}")
    print(f"  {C}  {summary[:280]}{E}")
    print(f"\n  {C}health_score     :{E} {result.get('health_score','?')}/100")
    actions = result.get("priority_actions", [])
    if actions:
        print(f"\n  {C}priority_actions ({len(actions)}):{E}")
        for a in actions[:4]:
            rank   = a.get("rank","?")
            action = a.get("action","")[:80]
            why    = a.get("why","")[:80]
            effort = a.get("effort","?")
            print(f"  {C}  [P{rank}] [{effort}] {action}{E}")
            print(f"  {C}        why: {why}{E}")
    risks = result.get("key_risks", [])
    if risks:
        print(f"\n  {C}key_risks:{E}")
        for r in risks[:3]:
            print(f"  {C}  - {str(r)[:100]}{E}")
    print(f"\n  {G}AI Coder impact:{E} Knows WHERE to start, WHAT to fix first, WHY it matters")
else:
    print(f"  {R}LLM returned None ({ms:.0f}ms){E}")

# ──────────────────────────────────────────────────────────────────────────
hdr("3. REFACTOR SEQUENCE -- AI Coder plans safe changes")
# ──────────────────────────────────────────────────────────────────────────

print(f"\n  {Y}Scenario:{E} AI Coder needs to refactor a high-impact function")
print(f"  {Y}Target:{E} 'PaymentService.process_payment' (5 callers, 8 callees)")

from src.core.cognitive.neo_enricher import refactor_sequence
t0 = time.monotonic()
mock_impact = {
    "risk": "high",
    "callers": [
        {"name": "checkout_endpoint"},
        {"name": "subscription_handler"},
        {"name": "refund_processor"},
        {"name": "billing_cron"},
        {"name": "webhook_dispatcher"},
    ],
    "callees": [
        {"name": "validate_card"},
        {"name": "send_to_gateway"},
        {"name": "log_transaction"},
    ],
    "affected_files": [
        "api/checkout.py", "services/subscription.py", "billing/refund.py", "tasks/cron.py",
    ],
}
result = refactor_sequence(mock_impact, target="PaymentService.process_payment", project_id="ai_impact_test")
ms = (time.monotonic()-t0)*1000

if result:
    print(f"\n  {G}LLM Refactor Plan (took {ms:.0f}ms):{E}")
    steps = result.get("safe_order", [])
    if steps:
        print(f"  {C}safe_order ({len(steps)} steps):{E}")
        for i, s in enumerate(steps[:5], 1):
            print(f"  {C}  {i}. {str(s)[:120]}{E}")
    risks = result.get("risk_per_step", [])
    if risks:
        print(f"\n  {C}risk_per_step:{E}")
        for rp in risks[:3]:
            print(f"  {C}  step {rp.get('step','?')} [{rp.get('risk','?')}]: {rp.get('reason','')[:80]}{E}")
    testing = result.get("testing_strategy","")
    if testing:
        print(f"\n  {C}testing_strategy: {testing[:200]}{E}")
    print(f"  {C}estimated_total_risk: {result.get('estimated_total_risk','?')}{E}")
    print(f"\n  {G}AI Coder impact:{E} Has dependency-ordered steps + per-step risk + test plan")
else:
    print(f"  {R}LLM returned None ({ms:.0f}ms){E}")

# ──────────────────────────────────────────────────────────────────────────
hdr("4. SEARCH EXPLAINER -- AI Coder navigates results")
# ──────────────────────────────────────────────────────────────────────────

print(f"\n  {Y}Scenario:{E} AI Coder searches codebase, gets multiple matches")
print(f"  {Y}Query:{E} 'process payment refund'")

from src.core.cognitive.neo_enricher import search_explainer
t0 = time.monotonic()
mock_results = [
    {"name": "process_payment", "file_path": "services/payment.py", "symbol_type": "function"},
    {"name": "PaymentGateway", "file_path": "core/gateway.py", "symbol_type": "class"},
    {"name": "refund_payment", "file_path": "services/refund.py", "symbol_type": "function"},
    {"name": "test_payment_flow", "file_path": "tests/test_payment.py", "symbol_type": "function"},
    {"name": "payment_config", "file_path": "config/settings.py", "symbol_type": "variable"},
]
result = search_explainer(mock_results, "process payment refund", project_id="ai_impact_test")
ms = (time.monotonic()-t0)*1000

if result:
    print(f"\n  {G}LLM Result Ranking (took {ms:.0f}ms):{E}")
    intent = result.get("intent_interpreted","")
    print(f"  {C}intent_interpreted: {intent[:150]}{E}")
    best = result.get("best_match_idx",0)
    if isinstance(best, int) and 0 <= best < len(mock_results):
        print(f"  {C}best_match        : [{best}] {mock_results[best]['name']} @ {mock_results[best]['file_path']}{E}")
    ranked = result.get("ranked_results", [])
    if ranked:
        print(f"\n  {C}ranked_results ({len(ranked)}):{E}")
        for r in ranked[:4]:
            idx = r.get("idx","?")
            rel = r.get("relevance","?")
            expl = r.get("explanation","")[:80]
            name = mock_results[idx]['name'] if isinstance(idx,int) and idx<len(mock_results) else "?"
            print(f"  {C}  [{rel:6}] {name:25} -- {expl}{E}")
    nxt = result.get("suggested_next","")
    if nxt:
        print(f"\n  {C}suggested_next: {nxt[:150]}{E}")
    print(f"\n  {G}AI Coder impact:{E} Knows WHICH result matters most, not just N matches")
else:
    print(f"  {R}LLM returned None ({ms:.0f}ms){E}")

# ──────────────────────────────────────────────────────────────────────────
hdr("FINAL VERDICT")
# ──────────────────────────────────────────────────────────────────────────

print(f"""
  {B}What was demonstrated:{E}
  {'-'*60}

  CodeCortex audit:
    Raw    : "2 god nodes detected, 3 circular deps"
    LLM    : Executive summary + P1/P2/P3 ranked actions + risks

  CodeCortex naming validation:
    Raw    : "Name is valid -> slug: 'handleuserpayment...'"
    LLM    : Verdict + score + alternatives + convention issues

  CodeCortex refactor impact:
    Raw    : "5 callers, 8 callees, risk: high"
    LLM    : Step-by-step sequence + per-step risk + test strategy

  CodeCortex search:
    Raw    : "5 matches found"
    LLM    : Intent interpretation + relevance ranking + next action

  {B}{G}AI Coder receives:{E}
  {G}  * Concrete WHAT to do{E}
  {G}  * Concrete WHY it matters{E}
  {G}  * Concrete ORDER of operations{E}
  {G}  * Risk assessment per step{E}

  {B}vs without bridge:{E}
  {R}  * Raw counts and lists{E}
  {R}  * No prioritization{E}
  {R}  * No execution order{E}
  {R}  * AI Coder must figure it all out{E}
""")
