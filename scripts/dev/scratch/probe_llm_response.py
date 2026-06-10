"""Probe raw LLM response from Neocortex /api/v1/llm/analyze."""
import os, sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

URL = "http://127.0.0.1:8010/api/v1/llm/analyze"
KEY = "nct_auth_KcZrU8eF4QWMCoPoVtWr6V8iUpXIVsPQYezrE-cZnvQ"

prompt = (
    'Return ONLY valid JSON with no other text:\n'
    '{"verdict": "approved", "score": 95, "note": "test"}'
)

resp = httpx.post(
    URL,
    json={"prompt": prompt, "format": "insight", "project_id": "probe", "max_tokens": 200},
    headers={"X-API-KEY": KEY, "Content-Type": "application/json"},
    timeout=120.0,
)
print(f"STATUS: {resp.status_code}")
print(f"RAW BODY:\n{resp.text[:2000]}")
print()
try:
    data = resp.json()
    print(f"PARSED success: {data.get('success')}")
    content = data.get("data", {}).get("content", "")
    print(f"CONTENT TYPE: {type(content).__name__}")
    print(f"CONTENT (first 1000 chars):")
    print(repr(content[:1000]) if isinstance(content, str) else content)
except Exception as e:
    print(f"JSON parse failed: {e}")
