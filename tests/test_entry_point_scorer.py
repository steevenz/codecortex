"""
Tests for entry point scoring.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.domain.codegraph.application.entry_point_scorer import EntryPointScorer, bulk_score_symbols


def test_entry_point_high_score():
    scorer = EntryPointScorer()
    result = scorer.score(
        name="handleLogin",
        callers_count=0,
        callees_count=5,
        is_exported=True,
        file_path="/app/routes/auth.py",
        language="python",
    )
    assert result["is_entry_point"] is True
    assert result["score"] >= 50


def test_entry_point_utility_penalty():
    scorer = EntryPointScorer()
    result = scorer.score(
        name="getUserName",
        callers_count=3,
        callees_count=0,
        is_exported=False,
    )
    assert result["score"] < 50


def test_entry_point_main():
    scorer = EntryPointScorer()
    result = scorer.score(name="main", callers_count=0, callees_count=10, is_exported=True)
    assert result["is_entry_point"] is True
    assert "name" in " ".join(result["reasons"])


def test_entry_point_low_score():
    scorer = EntryPointScorer()
    result = scorer.score(
        name="format_date",
        callers_count=5,
        callees_count=0,
        is_exported=False,
    )
    assert result["is_entry_point"] is False


def test_bulk_score():
    symbols = [
        {"name": "handleLogin", "callers_count": 0, "callees_count": 5, "is_exported": True},
        {"name": "formatDate", "callers_count": 5, "callees_count": 0, "is_exported": False},
    ]
    results = bulk_score_symbols(symbols)
    assert len(results) == 2
    assert results[0]["entry_score"] > results[1]["entry_score"]


def test_controller_pattern():
    scorer = EntryPointScorer()
    result = scorer.score(name="UserController", callers_count=1, callees_count=8, is_exported=True)
    assert result["is_entry_point"] is True


if __name__ == "__main__":
    test_entry_point_high_score()
    test_entry_point_utility_penalty()
    test_entry_point_main()
    test_entry_point_low_score()
    test_bulk_score()
    test_controller_pattern()
    print("All entry point scorer tests passed.")
