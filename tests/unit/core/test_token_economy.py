"""
Tests for Token Economy — LLM token optimization.
"""
import sys, json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[3]))


def test_estimate_tokens():
    from src.core.token import estimate_tokens
    assert estimate_tokens("hello world") > 0
    assert estimate_tokens("") == 0


def test_truncate():
    from src.core.token import truncate_to_budget
    t = truncate_to_budget("A" * 1000, 100)
    assert len(t) < 1000
    assert "truncated" in t


def test_summarize():
    from src.core.token import smart_summarize
    code = "import os\nimport sys\n\ndef hello():\n    print('hi')\n    x = 1\n"
    s = smart_summarize(code, 50)
    assert "def hello" in s or "import" in s


def test_cache():
    from src.core.token import TokenCache
    c = TokenCache(10, 60)
    assert c.get("k") is None
    c.set("v", 500, "k")
    assert c.get("k") == "v"


def test_optimize_dict():
    from src.core.token import optimize_response
    o = optimize_response({"a": "b", "c": "d"}, 1000)
    assert o.summary is not None


def test_optimize_list():
    from src.core.token import optimize_response
    data = [{"id": i, "content": "x" * 100} for i in range(50)]
    o = optimize_response(data, 500)
    assert o.truncated or o.token_count <= 500


def test_budget():
    from src.core.token import get_token_budget
    b = get_token_budget()
    assert 100 <= b <= 32000


def test_mcp_summary():
    from src.core.token import mcp_response
    big = {"results": [{"id": i, "data": "x" * 1000} for i in range(100)]}
    r = mcp_response(True, "test", big, summary_mode=True)
    assert r["success"]
    assert "token_economy" in r


def test_cache_clear():
    from src.core.token import TokenCache
    c = TokenCache(10)
    c.set("v", 100, "k")
    c.clear()
    assert c.get("k") is None


if __name__ == "__main__":
    test_estimate_tokens()
    test_truncate()
    test_summarize()
    test_cache()
    test_optimize_dict()
    test_optimize_list()
    test_budget()
    test_mcp_summary()
    test_cache_clear()
    print("ALL TOKEN ECONOMY TESTS PASSED!")
