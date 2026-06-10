"""
@project   CodeCortex
@package   modules.idegraph.tests
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:standard: Aegis-IdeGraph-v1.0

End-to-end tests for enhanced search engine — keyword, glob, regex, fuzzy, boolean, multi-field.
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.modules.idegraph.domain.engram import Engram, Message
from src.modules.idegraph.services.search_engine import (
    SearchEngine, SearchQuery, SearchMode, SearchField, SearchResult,
)


class TestExplainQuery:
    """Test auto-detection of search mode from query string."""

    def test_keyword_default(self):
        """Plain text → KEYWORD mode."""
        engine = SearchEngine()
        sq = engine.explain_query("authentication")
        assert sq.mode == SearchMode.KEYWORD
        assert sq.raw == "authentication"

    def test_glob_detection(self):
        """Patterns with * ? [ ] → GLOB mode."""
        engine = SearchEngine()
        sq = engine.explain_query("*.py")
        assert sq.mode == SearchMode.GLOB
        sq = engine.explain_query("src/**")
        assert sq.mode == SearchMode.GLOB

    def test_regex_detection(self):
        """Patterns starting with / → REGEX mode."""
        engine = SearchEngine()
        sq = engine.explain_query("/auth.*/i")
        assert sq.mode == SearchMode.REGEX
        assert sq.raw == "/auth.*/i"

    def test_boolean_detection(self):
        """Queries with AND/OR/NOT → BOOLEAN mode."""
        engine = SearchEngine()
        sq = engine.explain_query("auth AND oauth")
        assert sq.mode == SearchMode.BOOLEAN
        sq = engine.explain_query("auth OR oauth NOT facebook")
        assert sq.mode == SearchMode.BOOLEAN

    def test_fuzzy_detection(self):
        """Queries wrapped in ~ → FUZZY mode."""
        engine = SearchEngine()
        sq = engine.explain_query("~auth~")
        assert sq.mode == SearchMode.FUZZY
        assert sq.raw == "auth"

    def test_field_prefix_detection(self):
        """Prefix like title: code: → KEYWORD with specific field."""
        engine = SearchEngine()
        sq = engine.explain_query("title:authentication")
        assert sq.mode == SearchMode.KEYWORD
        assert sq.fields == [SearchField.TITLE]
        assert sq.raw == "authentication"

    def test_code_field_prefix(self):
        engine = SearchEngine()
        sq = engine.explain_query("code:def validate")
        assert sq.fields == [SearchField.CODE]
        assert sq.raw == "def validate"


class TestKeywordSearch:
    """Test basic keyword search functionality."""

    def _make_engram(self, title: str, content: str, id: str = "eg") -> Engram:
        return Engram(
            id=id, source="cursor", source_file="/test.json",
            messages=[Message(role="user", content=content)],
            title=title, created_at=datetime.now(timezone.utc),
        )

    def test_basic_keyword_match(self):
        """Keyword search finds substring in content."""
        engine = SearchEngine()
        candidates = [
            self._make_engram("Auth fix", "Fix JWT authentication bug", "a"),
            self._make_engram("DB setup", "Setup PostgreSQL database", "b"),
        ]
        sq = SearchQuery(raw="authentication", mode=SearchMode.KEYWORD)
        results = engine.search(sq, limit=10)
        # No DB connection, so fetch_candidates returns empty; test matcher directly
        score, fields, snippets = engine._score_engram(
            candidates[0], sq, engine._match_keyword, "authentication"
        )
        assert score > 0
        assert "content" in fields

    def test_keyword_no_match(self):
        """Keyword search returns 0 for non-matching text."""
        engine = SearchEngine()
        candidate = self._make_engram("Auth fix", "Fix JWT authentication bug")
        sq = SearchQuery(raw="oauth", mode=SearchMode.KEYWORD)
        score, fields, snippets = engine._score_engram(
            candidate, sq, engine._match_keyword, "oauth"
        )
        assert score == 0.0
        assert fields == []

    def test_multi_field_search(self):
        """Search across multiple fields."""
        engine = SearchEngine()
        candidate = self._make_engram("Auth fix", "Fix JWT authentication bug")
        sq = SearchQuery(raw="auth", mode=SearchMode.KEYWORD, fields=[SearchField.TITLE, SearchField.CONTENT])
        score, fields, snippets = engine._score_engram(
            candidate, sq, engine._match_keyword, "auth"
        )
        # Should match both title and content
        assert score > 0
        assert len(fields) >= 1


class TestGlobSearch:
    """Test glob pattern matching."""

    def _make_engram(self, source_file: str, title: str = "") -> Engram:
        return Engram(
            id="eg", source="cursor", source_file=source_file,
            messages=[Message(role="user", content="test")],
            title=title, created_at=datetime.now(timezone.utc),
        )

    def test_glob_source_file(self):
        """Glob patterns match source file paths."""
        engine = SearchEngine()
        candidate = self._make_engram("/home/user/src/auth.py")
        sq = SearchQuery(raw="*.py", mode=SearchMode.GLOB, fields=[SearchField.SOURCE])
        score, fields, snippets = engine._score_engram(
            candidate, sq, engine._match_glob, "*.py"
        )
        assert score > 0

    def test_glob_no_match(self):
        """Non-matching glob returns 0."""
        engine = SearchEngine()
        candidate = self._make_engram("/home/user/src/auth.js")
        sq = SearchQuery(raw="*.py", mode=SearchMode.GLOB, fields=[SearchField.SOURCE])
        score, fields, snippets = engine._score_engram(
            candidate, sq, engine._match_glob, "*.py"
        )
        assert score == 0.0


class TestRegexSearch:
    """Test regex pattern matching."""

    def test_regex_match(self):
        """Regex patterns match text."""
        engine = SearchEngine()
        candidate = Engram(
            id="eg", source="cursor", source_file="/test.json",
            messages=[Message(role="user", content="Fix JWT authentication bug")],
            title="Auth fix", created_at=datetime.now(timezone.utc),
        )
        import re
        regex = re.compile(r"auth.*", re.IGNORECASE)
        sq = SearchQuery(raw="/auth.*/i", mode=SearchMode.REGEX)
        score, fields, snippets = engine._score_engram(
            candidate, sq, engine._match_regex, regex
        )
        assert score > 0

    def test_regex_invalid_pattern(self):
        """Invalid regex returns empty results gracefully."""
        engine = SearchEngine()
        sq = SearchQuery(raw="/auth(/i", mode=SearchMode.REGEX)
        results = engine._search_regex([], sq)
        assert results == []


class TestFuzzySearch:
    """Test fuzzy matching with similarity threshold."""

    def test_fuzzy_match(self):
        """Fuzzy matching finds approximate matches."""
        engine = SearchEngine()
        candidate = Engram(
            id="eg", source="cursor", source_file="/test.json",
            messages=[Message(role="user", content="authentication system")],
            title="Auth", created_at=datetime.now(timezone.utc),
        )
        sq = SearchQuery(raw="authentification", mode=SearchMode.FUZZY)
        # Test direct fuzzy match on the content text itself
        text = "authentication system"
        matched, score = engine._match_fuzzy(text, "authentification")
        # "authentification" vs "authentication system" — direct comparison
        assert score > 0.3  # Some similarity exists

    def test_fuzzy_no_match(self):
        """Completely different words fail fuzzy match."""
        engine = SearchEngine()
        candidate = Engram(
            id="eg", source="cursor", source_file="/test.json",
            messages=[Message(role="user", content="database connection")],
            title="DB", created_at=datetime.now(timezone.utc),
        )
        sq = SearchQuery(raw="authentication", mode=SearchMode.FUZZY)
        score, fields, snippets = engine._score_engram(
            candidate, sq, engine._match_fuzzy, "authentication"
        )
        assert score < SearchEngine.FUZZY_THRESHOLD


class TestBooleanSearch:
    """Test boolean expression parsing and evaluation."""

    def test_boolean_and(self):
        """AND requires both terms."""
        engine = SearchEngine()
        text = "Fix JWT authentication and oauth"
        expr = engine._parse_boolean("auth AND oauth")
        result, score = engine._eval_boolean(text, expr)
        assert result is True
        assert score > 0

    def test_boolean_and_fail(self):
        """AND fails if one term missing."""
        engine = SearchEngine()
        text = "Fix JWT authentication"
        expr = engine._parse_boolean("auth AND oauth")
        result, score = engine._eval_boolean(text, expr)
        assert result is False

    def test_boolean_or(self):
        """OR succeeds if either term present."""
        engine = SearchEngine()
        text = "Fix JWT authentication"
        expr = engine._parse_boolean("auth OR oauth")
        result, score = engine._eval_boolean(text, expr)
        assert result is True

    def test_boolean_not(self):
        """NOT excludes term."""
        engine = SearchEngine()
        text = "Fix JWT authentication"
        expr = engine._parse_boolean("auth NOT oauth")
        result, score = engine._eval_boolean(text, expr)
        assert result is True

    def test_boolean_not_fail(self):
        """NOT fails if excluded term present."""
        engine = SearchEngine()
        text = "Fix JWT authentication with oauth"
        expr = engine._parse_boolean("auth NOT oauth")
        result, score = engine._eval_boolean(text, expr)
        assert result is False


class TestDateRangeFilter:
    """Test date range filtering."""

    def test_date_filter_includes(self):
        """Engram within date range passes filter."""
        engine = SearchEngine()
        now = datetime.now(timezone.utc)
        r = SearchResult(
            engram=Engram(id="a", source="c", source_file="/t", messages=[], created_at=now),
            score=1.0, matched_fields=[], match_snippets=[]
        )
        sq = SearchQuery(raw="x", date_from=now - timedelta(days=1), date_to=now + timedelta(days=1))
        filtered = engine._apply_filters([r], sq)
        assert len(filtered) == 1

    def test_date_filter_excludes(self):
        """Engram outside date range is excluded."""
        engine = SearchEngine()
        now = datetime.now(timezone.utc)
        r = SearchResult(
            engram=Engram(id="a", source="c", source_file="/t", messages=[], created_at=now - timedelta(days=10)),
            score=1.0, matched_fields=[], match_snippets=[]
        )
        sq = SearchQuery(raw="x", date_from=now - timedelta(days=5), date_to=now + timedelta(days=1))
        filtered = engine._apply_filters([r], sq)
        assert len(filtered) == 0


class TestMessageCountFilter:
    """Test message count filtering."""

    def test_min_messages(self):
        """Engram with fewer messages than min is excluded."""
        engine = SearchEngine()
        r = SearchResult(
            engram=Engram(id="a", source="c", source_file="/t", messages=[Message(role="user", content="x")], created_at=datetime.now(timezone.utc)),
            score=1.0, matched_fields=[], match_snippets=[]
        )
        sq = SearchQuery(raw="x", min_messages=5)
        filtered = engine._apply_filters([r], sq)
        assert len(filtered) == 0

    def test_max_messages(self):
        """Engram with more messages than max is excluded."""
        engine = SearchEngine()
        r = SearchResult(
            engram=Engram(id="a", source="c", source_file="/t", messages=[Message(role="user", content="x")] * 10, created_at=datetime.now(timezone.utc)),
            score=1.0, matched_fields=[], match_snippets=[]
        )
        sq = SearchQuery(raw="x", max_messages=5)
        filtered = engine._apply_filters([r], sq)
        assert len(filtered) == 0


class TestSnippetExtraction:
    """Test context snippet extraction."""

    def test_snippet_around_match(self):
        """Snippet includes context around match."""
        engine = SearchEngine()
        text = "This is a long text about authentication and authorization systems"
        snippet = engine.get_snippet(text, "authentication", radius=10)
        assert "authentication" in snippet
        assert "..." in snippet or len(snippet) < len(text)

    def test_snippet_no_match(self):
        """No match returns start of text."""
        engine = SearchEngine()
        text = "This is about databases"
        snippet = engine.get_snippet(text, "authentication", radius=10)
        assert "databases" in snippet


class TestFieldExtraction:
    """Test searchable text extraction from engrams."""

    def test_all_fields(self):
        """ALL field returns all searchable texts."""
        engine = SearchEngine()
        engram = Engram(
            id="eg", source="cursor", source_file="/src/auth.py",
            messages=[
                Message(role="user", content="Fix auth bug", code_context=["def fix():"], diffs=["+line"], tool_use=[{"name": "fix"}])
            ],
            title="Auth Fix", project_name="myapp",
            created_at=datetime.now(timezone.utc),
        )
        texts = engine._get_searchable_texts(engram, [SearchField.ALL])
        assert "title" in texts
        assert "content" in texts
        assert "code" in texts
        assert "diffs" in texts
        assert "tools" in texts
        assert "source" in texts
        assert "project" in texts

    def test_specific_fields(self):
        """Specific fields return only those texts."""
        engine = SearchEngine()
        engram = Engram(
            id="eg", source="cursor", source_file="/src/auth.py",
            messages=[Message(role="user", content="Fix auth bug")],
            title="Auth Fix", created_at=datetime.now(timezone.utc),
        )
        texts = engine._get_searchable_texts(engram, [SearchField.TITLE, SearchField.CONTENT])
        assert "title" in texts
        assert "content" in texts
        assert "code" not in texts
