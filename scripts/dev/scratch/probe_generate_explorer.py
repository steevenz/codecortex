"""Probe the exact generate/explorer call that crashed earlier."""
import os, sys, json, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

URL_SSE = "http://127.0.0.1:8010/cognitive-api/v1/sync"
URL_REST = "http://127.0.0.1:8010/api/v1/llm/analyze"
KEY = "nct_auth_KcZrU8eF4QWMCoPoVtWr6V8iUpXIVsPQYezrE-cZnvQ"

# Test 1: via direct REST analyze (the bridge path)
print("=== TEST 1: REST /api/v1/llm/analyze (bridge path) ===")
t0 = time.monotonic()
try:
    resp = httpx.post(
        URL_REST,
        json={
            "prompt": "GitBook-style sidebar redesign: organization switcher header, collapsible Projects/Workspaces sections, bottom actions bar with theme/settings/help.",
            "format": "insight",
            "project_id": "CODDYbots-sidebar-refactor",
            "max_tokens": 400,
        },
        headers={"X-API-KEY": KEY, "Content-Type": "application/json"},
        timeout=60.0,
    )
    print(f"STATUS: {resp.status_code} ({(time.monotonic()-t0)*1000:.0f}ms)")
    print(f"BODY: {resp.text[:600]}")
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")

# Test 2: via MCP tools/call (the original failing path)
print("\n=== TEST 2: MCP tools/call generate(mode=explorer) ===")
t0 = time.monotonic()
payload = {
    "jsonrpc": "2.0",
    "id": "test-explorer-1",
    "method": "tools/call",
    "params": {
        "name": "brainstorm",
        "arguments": {
            "action": "generate",
            "mode": "explorer",
            "project_id": "CODDYbots-sidebar-refactor",
            "session_id": "",
            "topic": "GitBook-style sidebar redesign: organization switcher header, collapsible Projects/Workspaces sections, bottom actions bar with theme/settings/help. Need to map current Coddy sidebar structure to new layout while preserving nav items, workspaces, chats, clusters, and user profile data.",
        },
    },
}
try:
    resp = httpx.post(URL_SSE, json=payload, headers={"X-API-KEY": KEY}, timeout=120.0)
    print(f"STATUS: {resp.status_code} ({(time.monotonic()-t0)*1000:.0f}ms)")
    print(f"BODY: {resp.text[:800]}")
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
