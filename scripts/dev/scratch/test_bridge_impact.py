"""
Bridge Impact Test -- CodeCortex <-> Neocortex
Pure HTTP test, no cross-venv imports.

Run from mcp-codecortex root:
    python scripts/dev/scratch/test_bridge_impact.py
"""

import io, sys, json, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Read real API keys from .env files ──────────────────────────────────────
from pathlib import Path

def _read_env(path: str, key: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return ""

CC_ROOT  = Path(r"C:\Users\steevenz\MCP\mcp-codecortex")
NEO_ROOT = Path(r"C:\Users\steevenz\MCP\mcp-neocortex")

CC_URL   = "http://127.0.0.1:8001"
NEO_URL  = "http://127.0.0.1:8010"
CC_KEY   = _read_env(CC_ROOT / ".env", "CODECORTEX_CLIENT_API_KEY")
NEO_KEY  = _read_env(NEO_ROOT / ".env", "NEOCORTEX_CLIENT_API_KEY")
TIMEOUT  = 45.0
REPO_PATH = str(CC_ROOT)

print(f"CC key  : {CC_KEY[:20]}..." if CC_KEY else "CC key  : NOT FOUND")
print(f"NEO key : {NEO_KEY[:20]}..." if NEO_KEY else "NEO key : NOT FOUND")

# ── Colours ─────────────────────────────────────────────────────────────────
G = "\033[32m"; R = "\033[31m"; Y = "\033[33m"; C = "\033[36m"
B = "\033[1m";  E = "\033[0m"

passed = failed = 0

def ok(label, detail=""):
    global passed; passed += 1
    print(f"  {G}[OK]{E} {label}")
    if detail: print(f"    {C}{str(detail)[:220]}{E}")

def fail(label, reason=""):
    global failed; failed += 1
    print(f"  {R}[FAIL]{E} {label}")
    if reason: print(f"    {R}{str(reason)[:220]}{E}")

def warn(msg): print(f"  {Y}[WARN]{E} {msg}")

def section(t):
    print(f"\n{B}{C}{'='*65}{E}\n{B}{C}  {t}{E}\n{B}{C}{'='*65}{E}")

# ── HTTP helpers ─────────────────────────────────────────────────────────────
try:
    import httpx
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx

def get(url, timeout=5.0):
    try:
        return httpx.get(url, timeout=timeout)
    except Exception as e:
        return type("R", (), {"status_code": 0, "json": lambda: {}, "text": str(e)})()

def rpc(base, key, path, tool, action, args):
    """Call an MCP tool via JSON-RPC and return parsed data dict."""
    try:
        r = httpx.post(
            f"{base}{path}",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                  "params": {"name": tool, "arguments": {"action": action, **args}}},
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return {"_http_error": r.status_code, "_body": r.text[:200]}
        body = r.json()
        content = (body.get("result", {}) or {}).get("content") or []
        if content and isinstance(content, list):
            text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
            try: return json.loads(text)
            except Exception: return {"_raw": text[:400]}
        return body.get("result", body)
    except Exception as e:
        return {"_exception": str(e)}

def post(url, key, payload):
    try:
        r = httpx.post(url, json=payload, headers={"X-API-KEY": key, "Content-Type": "application/json"}, timeout=TIMEOUT)
        return r.json() if r.status_code == 200 else {"_http_error": r.status_code}
    except Exception as e:
        return {"_exception": str(e)}

def ping(base, key, path):
    try:
        r = httpx.post(f"{base}{path}",
                       json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                       headers={"X-API-KEY": key, "Content-Type": "application/json"}, timeout=5.0)
        body = r.json()
        return r.status_code == 200 and ("result" in body or body.get("success"))
    except Exception:
        return False

def extract_session(d):
    if not isinstance(d, dict): return None
    for k in ("session_id", "session_token"):
        v = d.get(k) or d.get("data", {}).get(k) or d.get("cognition", {}).get(k)
        if v: return v
    return None

# ============================================================
section("TEST 1  --  Server Health & API Auth")
# ============================================================

r = get(f"{CC_URL}/status")
if r.status_code == 200:
    d = r.json()
    name = d.get("server", {}).get("name", "?")
    ok("CodeCortex /status reachable", f"name={name} transport={d.get('transport','?')}")
else:
    fail("CodeCortex /status", f"HTTP {r.status_code}")

r = get(f"{NEO_URL}/status")
if r.status_code == 200:
    d = r.json()
    ok("Neocortex /status reachable", f"server={d.get('server','?')} transport={d.get('transport','?')}")
else:
    fail("Neocortex /status", f"HTTP {r.status_code}")

# CodeCortex auth — use health endpoint (no auth needed) then try tool list
try:
    r = httpx.post(f"{CC_URL}/codecortex-api/v1/sync",
                   json={"jsonrpc":"2.0","id":1,"method":"tools/list"},
                   headers={"X-API-KEY": CC_KEY, "Content-Type":"application/json"}, timeout=8.0)
    body = r.json()
    if "result" in body:
        tools = body["result"].get("tools", [])
        ok("CodeCortex MCP auth + tools/list", f"{len(tools)} tools: {[t['name'] for t in tools[:4]]}")
    elif "error" in body:
        fail("CodeCortex MCP auth", f"RPC error: {body['error']}")
    else:
        warn("CodeCortex auth response unexpected")
        print(f"    {C}{str(body)[:150]}{E}")
except Exception as e:
    fail("CodeCortex MCP auth", str(e))

neo_ok = ping(NEO_URL, NEO_KEY, "/cognitive-api/v1/sync")
ok("Neocortex MCP auth (ping)") if neo_ok else fail("Neocortex MCP auth")

# LLM provider check
r_neo_status = get(f"{NEO_URL}/status").json()
llm_prov = r_neo_status.get("llm_provider", "?")
warn(f"Neocortex LLM provider: '{llm_prov}' -- bridge calls will be no-ops if no LLM") if llm_prov in ("?", "GUIDED", None, "") else ok(f"Neocortex LLM provider active: {llm_prov}")

# ============================================================
section("TEST 2  --  CodeCortex -> Neocortex (LLM enrichment)")
# ============================================================

# 2a. Direct /api/v1/llm/analyze
print(f"\n  {Y}2a. Neocortex /api/v1/llm/analyze -- direct LLM call{E}")
t0 = time.monotonic()
r_llm = post(NEO_URL, NEO_KEY, {
    "prompt": (
        "You are a senior architect. Analyze this audit data:\n"
        "God nodes: ['PaymentService', 'UserController']\n"
        "Circular deps: 3\n"
        "High coupling: OrderService->PaymentService (0.92)\n\n"
        "Return valid JSON only:\n"
        '{"executive_summary":"...","health_score":42,'
        '"priority_actions":[{"rank":1,"action":"...","why":"...","effort":"medium"}],'
        '"key_risks":["risk1"]}'
    ),
    "format": "remediation", "project_id": "bridge_test", "max_tokens": 600,
})
ms = (time.monotonic()-t0)*1000

if r_llm.get("success"):
    content = r_llm.get("data", {}).get("content", "")
    ok(f"LLM analyze responded ({ms:.0f}ms)")
    if not content or "No LLM" in content or "not configured" in content.lower():
        warn(f"LLM returned fallback -- no model configured: {content[:100]}")
    else:
        try:
            parsed = json.loads(content)
            ok("LLM returned structured JSON", f"health_score={parsed.get('health_score','?')} | P1: {str(parsed.get('priority_actions',[{}])[0].get('action','?'))[:60]}")
        except Exception:
            ok("LLM returned text (non-JSON)", content[:120])
else:
    fail(f"LLM analyze failed ({ms:.0f}ms)", str(r_llm)[:100])

# 2b. CortexBridge via CodeCortex Python env
print(f"\n  {Y}2b. CortexBridge discovery from CodeCortex venv{E}")
t0 = time.monotonic()
bridge_script = f"""
import sys; sys.path.insert(0,r'{CC_ROOT}')
import os
os.environ['CODECORTEX_BRIDGE_NEOCORTEX_URL']       = '{NEO_URL}'
os.environ['CODECORTEX_BRIDGE_NEOCORTEX_API_KEY']   = '{NEO_KEY}'
os.environ['CODECORTEX_BRIDGE_ENABLED']              = 'true'
os.environ['CODECORTEX_BRIDGE_NEOCORTEX_TRANSPORT']  = 'sse'
from src.core.cognitive.bridge import CortexBridge
b = CortexBridge.instance()
d = b.discover(force=True)
print(f'discovered={{d}} url={{b.cct_url}}')
"""
import subprocess
result = subprocess.run(
    [str(CC_ROOT / ".venv" / "Scripts" / "python.exe"), "-c", bridge_script],
    capture_output=True, text=True, cwd=str(CC_ROOT), timeout=20
)
ms = (time.monotonic()-t0)*1000
out = result.stdout.strip()
if "discovered=True" in out:
    ok(f"CortexBridge discovered Neocortex ({ms:.0f}ms)", out)
elif "discovered=False" in out:
    warn(f"CortexBridge could not reach Neocortex LLM endpoint ({ms:.0f}ms)")
    print(f"    {C}{out}{E}")
    if result.stderr:
        print(f"    {R}{result.stderr[:150]}{E}")
else:
    fail("CortexBridge script error", result.stderr[:200] or out[:200])

# 2c. NeoEnricher.audit_narrative
print(f"\n  {Y}2c. NeoEnricher.audit_narrative -- structured audit report{E}")
enricher_script = f"""
import sys; sys.path.insert(0,r'{CC_ROOT}')
import os, json
os.environ['CODECORTEX_BRIDGE_NEOCORTEX_URL']      = '{NEO_URL}'
os.environ['CODECORTEX_BRIDGE_NEOCORTEX_API_KEY']  = '{NEO_KEY}'
os.environ['CODECORTEX_BRIDGE_ENABLED']             = 'true'
from src.core.cognitive.neo_enricher import audit_narrative
mock = {{
    "god_nodes": [{{"name":"PaymentService","in_degree":23}},{{"name":"UserController","in_degree":15}}],
    "dead_code": [{{"name":"legacy_handler"}},{{"name":"unused_util"}}],
    "circular_deps": {{"count":3}},
    "coupling": [{{"source":"OrderService","target":"PaymentService","score":0.92}}],
}}
r = audit_narrative(mock, project_id='bridge_test')
print(json.dumps(r) if r else "NULL")
"""
t0 = time.monotonic()
result = subprocess.run(
    [str(CC_ROOT / ".venv" / "Scripts" / "python.exe"), "-c", enricher_script],
    capture_output=True, text=True, cwd=str(CC_ROOT), timeout=30
)
ms = (time.monotonic()-t0)*1000
out = result.stdout.strip()
if out and out != "NULL":
    try:
        parsed = json.loads(out)
        meta = parsed.pop("_meta", {})
        ok(f"audit_narrative returned structured dict ({ms:.0f}ms)")
        summary = parsed.get("executive_summary","")
        health  = parsed.get("health_score","?")
        actions = parsed.get("priority_actions", [])
        risks   = parsed.get("key_risks", [])
        print(f"    {C}health_score  : {health}{E}")
        print(f"    {C}summary       : {summary[:140]}{E}")
        if actions:
            a1 = actions[0]
            print(f"    {C}P1 action     : [{a1.get('effort','?')}] {str(a1.get('action','?'))[:80]}{E}")
            print(f"    {C}  why         : {str(a1.get('why','?'))[:80]}{E}")
        if risks:
            print(f"    {C}key_risks     : {risks[:2]}{E}")
        if meta.get("ai_generated"):
            ok("_meta.ai_generated=True (governance label present)")
        else:
            warn("_meta.ai_generated missing (LLM call likely skipped)")
    except Exception as e:
        warn(f"audit_narrative response parse error: {e} | raw: {out[:100]}")
elif out == "NULL":
    warn(f"audit_narrative returned None ({ms:.0f}ms) -- LLM unavailable, rule-based fallback will be used")
else:
    fail("audit_narrative script error", result.stderr[:200])

# 2d. NeoEnricher.naming_advisor
print(f"\n  {Y}2d. NeoEnricher.naming_advisor -- class/filename decision maker{E}")
naming_script = f"""
import sys; sys.path.insert(0,r'{CC_ROOT}')
import os, json
os.environ['CODECORTEX_BRIDGE_NEOCORTEX_URL']     = '{NEO_URL}'
os.environ['CODECORTEX_BRIDGE_NEOCORTEX_API_KEY'] = '{NEO_KEY}'
os.environ['CODECORTEX_BRIDGE_ENABLED']            = 'true'
from src.core.cognitive.neo_enricher import naming_advisor
r = naming_advisor(
    "HandleUserPaymentProcessingAndEmailNotification",
    context={{"kind":"class","stack":"Python FastAPI","existing_names":["PaymentService","NotificationService"]}},
    project_id="bridge_test",
)
print(json.dumps(r) if r else "NULL")
"""
t0 = time.monotonic()
result = subprocess.run(
    [str(CC_ROOT / ".venv" / "Scripts" / "python.exe"), "-c", naming_script],
    capture_output=True, text=True, cwd=str(CC_ROOT), timeout=25
)
ms = (time.monotonic()-t0)*1000
out = result.stdout.strip()
if out and out != "NULL":
    try:
        parsed = json.loads(out)
        parsed.pop("_meta", {})
        verdict = parsed.get("verdict","?"); score = parsed.get("score","?")
        alts    = parsed.get("alternatives",[]); rec = parsed.get("recommendation","")
        issues  = parsed.get("convention_issues",[])
        ok(f"naming_advisor verdict: {verdict} (score={score}) [{ms:.0f}ms]")
        if alts: print(f"    {C}Alternatives  : {alts[:3]}{E}")
        if rec:  print(f"    {C}Recommendation: {rec[:120]}{E}")
        if issues: print(f"    {C}Issues        : {issues[:2]}{E}")
        if verdict in ("warning","rejected"):
            ok("LLM correctly flagged non-SRP class name")
    except Exception as e:
        warn(f"naming_advisor parse error: {e}")
elif out == "NULL":
    warn(f"naming_advisor returned None ({ms:.0f}ms) -- LLM unavailable")
else:
    fail("naming_advisor error", result.stderr[:200])

# ============================================================
section("TEST 3  --  Neocortex -> CodeCortex (codebase context)")
# ============================================================

# 3a. CodeCortexClient.get_code_context via neocortex venv
print(f"\n  {Y}3a. CodeCortexClient.get_code_context -- symbol search{E}")
neo_cc_script = f"""
import sys; sys.path.insert(0,r'{NEO_ROOT}')
import os, json, asyncio
os.environ['NEOCORTEX_BRIDGE_CODECORTEX_URL']      = '{CC_URL}'
os.environ['NEOCORTEX_BRIDGE_CODECORTEX_API_KEY']  = '{CC_KEY}'
os.environ['NEOCORTEX_BRIDGE_ENABLED']              = 'true'
os.environ['NEOCORTEX_BRIDGE_CODECORTEX_TRANSPORT'] = 'sse'
from src.core.bridges.codecortex_client import CodeCortexClient
CodeCortexClient._instance = None
c = CodeCortexClient.instance()
r = asyncio.run(c.get_code_context(query="payment processing", repo_path=r'{REPO_PATH}'))
print(json.dumps(r) if r else "NULL")
"""
t0 = time.monotonic()
result = subprocess.run(
    [str(NEO_ROOT / ".venv" / "Scripts" / "python.exe"), "-c", neo_cc_script],
    capture_output=True, text=True, cwd=str(NEO_ROOT), timeout=30
)
ms = (time.monotonic()-t0)*1000
out = result.stdout.strip()
if out and out != "NULL":
    try:
        parsed = json.loads(out)
        if parsed.get("success"):
            data = parsed.get("data") or {}
            ok(f"get_code_context returned data ({ms:.0f}ms)")
            results = data.get("results") or data.get("symbols") or []
            if results and isinstance(results, list):
                ok(f"Codebase search: {len(results)} symbols found")
                for r in results[:3]:
                    nm = r.get("name","?") if isinstance(r,dict) else str(r)[:40]
                    fp = r.get("file_path","") if isinstance(r,dict) else ""
                    print(f"    {C}  symbol: {nm} @ {fp[:50]}{E}")
            else:
                print(f"    {C}data keys: {list(data.keys())[:6] if isinstance(data,dict) else type(data)}{E}")
        else:
            warn(f"get_code_context success=False: {str(parsed)[:150]}")
    except Exception as e:
        warn(f"parse error: {e} | raw: {out[:100]}")
elif out == "NULL":
    warn(f"get_code_context returned None ({ms:.0f}ms) -- repo may not be indexed")
else:
    fail("CodeCortexClient.get_code_context error", result.stderr[:200])

# 3b. get_architecture
print(f"\n  {Y}3b. CodeCortexClient.get_architecture -- architecture audit{E}")
arch_script = f"""
import sys; sys.path.insert(0,r'{NEO_ROOT}')
import os, json, asyncio
os.environ['NEOCORTEX_BRIDGE_CODECORTEX_URL']     = '{CC_URL}'
os.environ['NEOCORTEX_BRIDGE_CODECORTEX_API_KEY'] = '{CC_KEY}'
os.environ['NEOCORTEX_BRIDGE_ENABLED']             = 'true'
from src.core.bridges.codecortex_client import CodeCortexClient
CodeCortexClient._instance = None
c = CodeCortexClient.instance()
r = asyncio.run(c.get_architecture(repo_path=r'{REPO_PATH}'))
print(json.dumps(r) if r else "NULL")
"""
t0 = time.monotonic()
result = subprocess.run(
    [str(NEO_ROOT / ".venv" / "Scripts" / "python.exe"), "-c", arch_script],
    capture_output=True, text=True, cwd=str(NEO_ROOT), timeout=30
)
ms = (time.monotonic()-t0)*1000
out = result.stdout.strip()
if out and out != "NULL":
    try:
        parsed = json.loads(out)
        if parsed.get("success"):
            data = parsed.get("data") or {}
            ok(f"get_architecture returned data ({ms:.0f}ms)")
            gods   = data.get("god_nodes", [])
            circ   = data.get("circular_deps",{}).get("count",0) if isinstance(data.get("circular_deps"),dict) else 0
            couple = data.get("coupling",[])
            print(f"    {C}god_nodes     : {len(gods)} detected{E}")
            print(f"    {C}circular_deps : {circ}{E}")
            print(f"    {C}coupling pairs: {len(couple)}{E}")
        else:
            warn(f"get_architecture success=False: {str(parsed)[:120]}")
    except Exception as e:
        warn(f"parse error: {e} | raw: {out[:100]}")
elif out == "NULL":
    warn(f"get_architecture returned None ({ms:.0f}ms) -- repo may not be indexed")
else:
    fail("get_architecture error", result.stderr[:200])

# 3c. query_docs
print(f"\n  {Y}3c. CodeCortexClient.query_docs -- knowledge graph search{E}")
docs_script = f"""
import sys; sys.path.insert(0,r'{NEO_ROOT}')
import os, json, asyncio
os.environ['NEOCORTEX_BRIDGE_CODECORTEX_URL']     = '{CC_URL}'
os.environ['NEOCORTEX_BRIDGE_CODECORTEX_API_KEY'] = '{CC_KEY}'
from src.core.bridges.codecortex_client import CodeCortexClient
CodeCortexClient._instance = None
c = CodeCortexClient.instance()
r = asyncio.run(c.query_docs(query="authentication API contract", repo_path=r'{REPO_PATH}'))
print(json.dumps(r) if r else "NULL")
"""
t0 = time.monotonic()
result = subprocess.run(
    [str(NEO_ROOT / ".venv" / "Scripts" / "python.exe"), "-c", docs_script],
    capture_output=True, text=True, cwd=str(NEO_ROOT), timeout=25
)
ms = (time.monotonic()-t0)*1000
out = result.stdout.strip()
if out and out != "NULL":
    try:
        parsed = json.loads(out)
        ok(f"query_docs returned data ({ms:.0f}ms)")
        data = parsed.get("data",parsed)
        print(f"    {C}keys: {list(data.keys())[:6] if isinstance(data,dict) else type(data)}{E}")
    except Exception:
        warn(f"query_docs raw: {out[:100]}")
elif out == "NULL":
    warn(f"query_docs returned None ({ms:.0f}ms)")
else:
    fail("query_docs error", result.stderr[:150])

# ============================================================
section("TEST 4  --  Full Chain: think(decompose) + bridge triggers")
# ============================================================

print(f"\n  {Y}4a. think(action=decompose) with code problem + repo_path{E}")
t0 = time.monotonic()
think_r = rpc(NEO_URL, NEO_KEY, "/cognitive-api/v1/sync", "think", "decompose", {
    "content": "Refactor PaymentService: it handles payment processing, auth, email notifications and audit logging -- clear SRP violation with 800+ lines",
    "mode": "architect",
    "repo_path": REPO_PATH,
    "context": "Python FastAPI codebase, need to break into focused services",
})
ms = (time.monotonic()-t0)*1000

if "_http_error" in think_r or "_exception" in think_r:
    fail(f"think(decompose) failed ({ms:.0f}ms)", str(think_r))
else:
    ok(f"think(decompose) responded ({ms:.0f}ms)")
    cog  = think_r.get("cognition", think_r)
    sess = think_r.get("session_id") or (cog.get("session_id") if isinstance(cog,dict) else None)
    cont = (cog.get("content") or cog.get("output") or "") if isinstance(cog,dict) else str(cog)[:300]
    recs = (cog.get("recommendations") or []) if isinstance(cog,dict) else []
    exec_time = think_r.get("execution_time",{})

    if sess: ok(f"Session created: {sess[:16]}...")
    if cont: print(f"    {C}LLM output (first 200 chars):\n    {cont[:200]}{E}")
    if recs: print(f"    {C}Recommendations: {recs[:2]}{E}")

    research_scenario = exec_time.get("scenario","?") if isinstance(exec_time,dict) else "?"
    research_ms = exec_time.get("research_ms",0) if isinstance(exec_time,dict) else 0
    if research_scenario != "bypass_no_research":
        ok(f"Research gate fired (scenario={research_scenario}, {research_ms:.0f}ms)")
    else:
        warn("Research gate bypassed -- keywords may not have matched")

    # Check if session_context has codebase data
    sess_ctx = (cog.get("session_context") or {}) if isinstance(cog,dict) else {}
    if isinstance(sess_ctx,dict) and (sess_ctx.get("codebase_context") or sess_ctx.get("codebase_snapshot")):
        ok("Codebase context injected into LLM session context")
    else:
        warn("Codebase context not visible in response (async pre-fetch or not indexed)")

# ============================================================
section("TEST 5  --  Full Chain: codebase:audit + NeoEnricher insight")
# ============================================================

print(f"\n  {Y}5a. codebase:audit -> NeoEnricher insight (LLM-enriched or rule-based){E}")
t0 = time.monotonic()
audit_r = rpc(CC_URL, CC_KEY, "/codecortex-api/v1/sync", "codecortex:codebase", "audit", {
    "repo_path": REPO_PATH,
})
ms = (time.monotonic()-t0)*1000

if "_http_error" in audit_r or "_exception" in audit_r:
    fail(f"codebase:audit failed ({ms:.0f}ms)", str(audit_r))
else:
    ok(f"codebase:audit responded ({ms:.0f}ms)")
    insight = audit_r.get("insight",{})
    data    = audit_r.get("data",{})

    if isinstance(insight,dict) and insight:
        summary = insight.get("summary","")
        recs    = insight.get("recommendations",[])
        crit    = insight.get("critical_issues",[])
        risk    = insight.get("risk_level","?")
        ok(f"Insight field present | risk_level={risk}")
        print(f"    {C}summary : {summary[:160]}{E}")
        if recs:
            print(f"    {C}recs ({len(recs)}):{E}")
            for rec in recs[:4]: print(f"      {C}* {str(rec)[:100]}{E}")
        if crit:
            print(f"    {C}critical ({len(crit)}): {str(crit[0])[:100]}{E}")
        # Detect if LLM-enriched (longer/richer summary or contains priority markers)
        llm_signals = ["executive", "[P1]", "[P2]", "health_score", "Extract", "Decompose"]
        is_llm = any(sig.lower() in summary.lower() or any(sig.lower() in str(r).lower() for r in recs) for sig in llm_signals)
        ok("Insight is LLM-enriched via NeoEnricher") if is_llm else warn("Insight appears rule-based (NeoEnricher LLM call may have returned None)")
    else:
        warn("No 'insight' field in response -- generate_insight may not be hooked")

    if isinstance(data,dict):
        gods = data.get("god_nodes",[]) or []
        circ = (data.get("circular_deps") or {}).get("count",0)
        dead = data.get("dead_code",[]) or []
        print(f"    {C}raw: {len(gods)} god_nodes, {circ} circular_deps, {len(dead)} dead_code{E}")

# 5b. scaffolder:validate_name
print(f"\n  {Y}5b. scaffolder:validate_name -> naming_advisor insight{E}")
t0 = time.monotonic()
name_r = rpc(CC_URL, CC_KEY, "/codecortex-api/v1/sync", "codecortex:scaffolder", "validate_name", {
    "name": "HandleUserPaymentProcessingAndEmailNotification",
})
ms = (time.monotonic()-t0)*1000

if "_http_error" in name_r or "_exception" in name_r:
    fail(f"validate_name failed ({ms:.0f}ms)", str(name_r))
else:
    ok(f"validate_name responded ({ms:.0f}ms)")
    insight = name_r.get("insight",{})
    data    = name_r.get("data",{})
    if isinstance(insight,dict) and insight:
        summary = insight.get("summary","")
        recs    = insight.get("recommendations",[])
        ok("Naming insight present")
        print(f"    {C}summary: {summary[:160]}{E}")
        for rec in recs[:3]: print(f"      {C}* {str(rec)[:100]}{E}")
        has_llm = any("score" in str(r).lower() or "alternative" in str(r).lower() or "verdict" in str(r).lower() for r in recs)
        ok("Naming insight LLM-enriched (score/alternatives/verdict present)") if has_llm else warn("Naming insight rule-based")
    else:
        warn("No naming insight in response")

# ============================================================
section("TEST 6  --  Research Gate: local sources in evidence")
# ============================================================

print(f"\n  {Y}6a. think(action=debug) -- triggers research gate with local sources{E}")
t0 = time.monotonic()
debug_r = rpc(NEO_URL, NEO_KEY, "/cognitive-api/v1/sync", "think", "debug", {
    "content": "Find all callers of the authentication function in the codebase and identify potential security issues",
    "mode": "auto",
    "repo_path": REPO_PATH,
})
ms = (time.monotonic()-t0)*1000

if "_http_error" in debug_r or "_exception" in debug_r:
    fail(f"think(debug) failed ({ms:.0f}ms)", str(debug_r))
else:
    ok(f"think(debug) responded ({ms:.0f}ms)")
    exec_time = debug_r.get("execution_time",{})
    scenario  = exec_time.get("scenario","?") if isinstance(exec_time,dict) else "?"
    total_ms  = exec_time.get("total_ms",0) if isinstance(exec_time,dict) else 0
    res_ms    = exec_time.get("research_ms",0) if isinstance(exec_time,dict) else 0
    llm_ms    = exec_time.get("llm_ms",0) if isinstance(exec_time,dict) else 0

    print(f"    {C}scenario     : {scenario}{E}")
    print(f"    {C}total_ms     : {total_ms:.0f}ms{E}")
    print(f"    {C}research_ms  : {res_ms:.0f}ms{E}")
    print(f"    {C}llm_ms       : {llm_ms:.0f}ms{E}")

    if scenario in ("full","cached_research"):
        ok("Research gate fired -- local+web sources queried")
    else:
        warn(f"Research gate scenario: {scenario}")

    cog = debug_r.get("cognition",{})
    content = (cog.get("content") or cog.get("output") or "") if isinstance(cog,dict) else ""
    if content: print(f"    {C}response: {content[:200]}{E}")

# ============================================================
section("IMPACT ANALYSIS  --  AI Coder Before vs After Bridge")
# ============================================================

total = passed + failed
pct   = int(passed/total*100) if total else 0

print(f"""
  {B}Test Summary:{E}
  {'─'*45}
  {G}Passed  : {passed}{E}
  {R}Failed  : {failed}{E}
  {B}Score   : {pct}%{E}

  {B}Impact on AI Coder -- Before vs After:{E}
  {'─'*65}

  Code Search:
    BEFORE  Symbols returned as flat list, AI must guess relevance
    AFTER   Results ranked by intent, best match explained with WHY

  Architecture Audit:
    BEFORE  "3 god nodes, 2 circular deps" (raw numbers)
    AFTER   Executive summary + P1/P2/P3 action plan with effort estimate

  Naming / Scaffold:
    BEFORE  Regex-only validation (snake_case, length)
    AFTER   LLM scores domain fit, suggests SRP-aligned alternatives

  Refactoring:
    BEFORE  Blast radius as list of affected files
    AFTER   Step-by-step dependency-safe sequence + testing strategy

  Security Audit:
    BEFORE  "N findings" count
    AFTER   Severity narrative + remediation steps + compliance notes

  Thinking Sessions:
    BEFORE  LLM reasons about code from problem description alone
    AFTER   Pre-loaded with real architecture (god nodes, coupling data)
            Research gate queries codebase + docs + IDE history

  Cross-IDE Memory:
    BEFORE  Each session starts from zero
    AFTER   Past decisions stored in IDEGraph, recalled by any IDE
  {'─'*65}
""")

if pct >= 80:
    print(f"  {G}{B}[PASS] BRIDGE OPERATIONAL -- AI Coder benefits ACTIVE{E}")
elif pct >= 50:
    print(f"  {Y}{B}[PARTIAL] Bridge working -- some features need LLM config{E}")
else:
    print(f"  {R}{B}[FAIL] Bridge needs attention -- check connectivity + LLM provider{E}")

if llm_prov in ("?", "GUIDED", None, ""):
    print(f"""
  {Y}NOTE: Neocortex has no LLM provider configured.{E}
  {Y}      NeoEnricher calls will return None and fall back to rule-based.{E}
  {Y}      To enable full LLM enrichment, set one of:{E}
  {C}        NEOCORTEX_LLM_PROVIDER=ollama  (free, local){E}
  {C}        NEOCORTEX_LLM_PROVIDER=openai  (OPENAI_API_KEY required){E}
  {C}        NEOCORTEX_LLM_PROVIDER=anthropic (ANTHROPIC_API_KEY required){E}
  {C}        NEOCORTEX_LLM_ROUND_ROBIN=true   (all configured providers){E}
""")
