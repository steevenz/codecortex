"""E2E test bridge + insight"""
import sys
sys.path.insert(0, ".")
from src.core.cognitive.bridge import CortexBridge
from src.core.insight import generate_insight, AIInsight

b = CortexBridge.instance()
ok = b.discover(force=True)
print(f"1. Bridge discover: {ok}")
print(f"   CCT URL: {b.cct_url}")

result = b.enrich("repo_inspect", {"files": 100, "symbols": 50, "language": "python"}, project_id="test")
print(f"2. Bridge enrich: {'OK' if result else 'LLM not available (no API key)'}")
if result:
    print(f"   Insight: {result[:100]}")

insight = generate_insight("repo_inspect", {"files": 100, "symbols": 50})
print(f"3. generate_insight fallback: {insight.summary[:80]}...")
