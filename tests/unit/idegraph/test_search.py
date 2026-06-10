import os
import sys
sys.path.insert(0, os.path.abspath('.'))

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.services.search_engine import (
    SearchEngine, SearchQuery, SearchMode, SearchField
)

@pytest.fixture
def sample_engrams():
    return [
        Engram(
            id="e1",
            source="vscode",
            source_file="auth.py",
            project_name="Backend",
            title="Authentication issue",
            created_at=datetime.now(timezone.utc),
            messages=[
                Message(role="user", content="Fix the JWT token validation"),
                Message(role="assistant", content="Here is the fix for auth logic.", code_context=[{"type": "function", "name": "validate_token"}])
            ],
            ide_info=IDEInfo(name="vscode", type="editor")
        ),
        Engram(
            id="e2",
            source="cursor",
            source_file="database.py",
            project_name="Backend",
            title="Database connection pool",
            created_at=datetime.now(timezone.utc),
            messages=[
                Message(role="user", content="Increase pool size to 20"),
                Message(role="assistant", content="Updated sqlalchemy pool_size=20.")
            ],
            ide_info=IDEInfo(name="cursor", type="editor")
        ),
    ]

def test_explain_query():
    engine = SearchEngine()
    
    # Keyword
    q1 = engine.explain_query("token")
    assert q1.mode == SearchMode.KEYWORD
    assert q1.raw == "token"
    
    # Regex
    q2 = engine.explain_query("/auth.*/i")
    assert q2.mode == SearchMode.REGEX
    assert q2.raw == "/auth.*/i"
    
    # Glob
    q3 = engine.explain_query("*.py")
    assert q3.mode == SearchMode.GLOB
    
    # Boolean
    q4 = engine.explain_query("token AND logic")
    assert q4.mode == SearchMode.BOOLEAN
    
    # Fuzzy
    q5 = engine.explain_query("~tokin~")
    assert q5.mode == SearchMode.FUZZY
    assert q5.raw == "tokin"

def test_search_keyword(sample_engrams):
    engine = SearchEngine()
    engine._fetch_candidates = MagicMock(return_value=sample_engrams)
    
    q = SearchQuery(raw="JWT", mode=SearchMode.KEYWORD)
    results = engine.search(q)
    
    assert len(results) == 1
    assert results[0].engram.id == "e1"
    assert "content" in results[0].matched_fields

def test_search_boolean(sample_engrams):
    engine = SearchEngine()
    engine._fetch_candidates = MagicMock(return_value=sample_engrams)
    
    q = SearchQuery(raw="token AND fix", mode=SearchMode.BOOLEAN)
    results = engine.search(q)
    
    assert len(results) == 1
    assert results[0].engram.id == "e1"

def test_search_regex(sample_engrams):
    engine = SearchEngine()
    engine._fetch_candidates = MagicMock(return_value=sample_engrams)
    
    q = SearchQuery(raw="pool_size=[0-9]+", mode=SearchMode.REGEX)
    results = engine.search(q)
    
    assert len(results) == 1
    assert results[0].engram.id == "e2"

if __name__ == "__main__":
    test_explain_query()
    
    # Fixture mocking for manual execution
    engrams = [
        Engram(
            id="e1",
            source="vscode",
            source_file="auth.py",
            project_name="Backend",
            title="Authentication issue",
            created_at=datetime.now(timezone.utc),
            messages=[
                Message(role="user", content="Fix the JWT token validation"),
                Message(role="assistant", content="Here is the fix for auth logic.")
            ],
            ide_info=IDEInfo(name="vscode", type="editor")
        )
    ]
    test_search_keyword(engrams)
    test_search_boolean(engrams)
    print("All test_search tests PASSED")
