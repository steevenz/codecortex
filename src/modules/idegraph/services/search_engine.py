"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:standard: Aegis-IdeGraph-v1.0

Search Engine — Advanced search capabilities for AI coders.
Supports keyword, glob, regex, fuzzy, boolean operators,
multi-field search, and date range queries.
"""

import fnmatch
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple, Callable

from src.modules.idegraph.domain.engram import Engram, Message
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)


class SearchMode(str, Enum):
    """Search mode types."""
    KEYWORD = "keyword"      # Default: substring match
    GLOB = "glob"            # fnmatch patterns: *.py, src/**
    REGEX = "regex"          # Regular expressions: /auth.*/i
    FUZZY = "fuzzy"          # Approximate match (difflib)
    BOOLEAN = "boolean"      # AND, OR, NOT operators


class SearchField(str, Enum):
    """Fields that can be searched."""
    ALL = "all"
    TITLE = "title"
    CONTENT = "content"
    CODE = "code"            # code_context
    DIFFS = "diffs"          # code diffs
    TOOLS = "tools"          # tool_use
    SOURCE = "source"        # source_file path
    PROJECT = "project"      # project_name


@dataclass
class SearchQuery:
    """Structured search query for AI coders."""
    raw: str
    mode: SearchMode = SearchMode.KEYWORD
    fields: List[SearchField] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_messages: Optional[int] = None
    max_messages: Optional[int] = None
    has_artifacts: Optional[bool] = None
    workspace_key: Optional[str] = None
    project_name: Optional[str] = None
    ide_name: Optional[str] = None

    def __post_init__(self):
        if self.fields is None:
            self.fields = [SearchField.ALL]


@dataclass
class SearchResult:
    """Search result with scoring and match details."""
    engram: Engram
    score: float  # 0.0-1.0
    matched_fields: List[str]
    match_snippets: List[str]  # Context snippets for AI
    rank: int = 0


class SearchEngine:
    """
    Advanced search engine for idegraph.
    
    Supports:
    - Keyword: simple substring matching
    - Glob: fnmatch patterns (e.g. "*.py", "src/**")
    - Regex: Python regular expressions (e.g. "r'auth.*'")
    - Fuzzy: approximate matching with similarity threshold
    - Boolean: AND, OR, NOT operators
    - Multi-field: search specific fields (title, content, code, diffs, tools, source)
    - Date range: filter by creation date
    """

    FUZZY_THRESHOLD = 0.6
    SNIPPET_LENGTH = 120

    def __init__(self, db=None):
        self._db = db

    # ── Public API ────────────────────────────────────────────────

    def search(self, query: SearchQuery, limit: int = 20) -> List[SearchResult]:
        """Execute search with advanced query parameters."""
        # Build candidate list from DB or cache
        candidates = self._fetch_candidates(query)

        # Apply search strategy based on mode
        if query.mode == SearchMode.GLOB:
            results = self._search_glob(candidates, query)
        elif query.mode == SearchMode.REGEX:
            results = self._search_regex(candidates, query)
        elif query.mode == SearchMode.FUZZY:
            results = self._search_fuzzy(candidates, query)
        elif query.mode == SearchMode.BOOLEAN:
            results = self._search_boolean(candidates, query)
        else:
            results = self._search_keyword(candidates, query)

        # Apply date/message/artifact filters
        results = self._apply_filters(results, query)

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        logger.info(
            "Search completed",
            extra={"extra_data": {
                "mode": query.mode.value,
                "query": query.raw,
                "total_results": len(results),
                "limit": limit,
            }},
        )
        return results[:limit]

    def explain_query(self, query_str: str) -> SearchQuery:
        """
        Auto-detect search mode from query string.
        
        Detection rules:
        - "*.py" or "src/**" → GLOB
        - "/pattern/flags" → REGEX
        - "word1 AND word2" → BOOLEAN
        - "~fuzzy~" → FUZZY (tilde prefix)
        - Default → KEYWORD
        """
        raw = query_str.strip()
        mode = SearchMode.KEYWORD
        fields = [SearchField.ALL]

        # Detect regex first (before glob since regex can contain *)
        if raw.startswith("/") and (raw.endswith("/") or raw.rfind("/") > 1):
            mode = SearchMode.REGEX
        # Detect glob
        elif any(c in raw for c in "*?[]!"):
            mode = SearchMode.GLOB
        # Detect boolean
        elif any(op in raw.upper() for op in [" AND ", " OR ", " NOT "]):
            mode = SearchMode.BOOLEAN
        # Detect fuzzy
        elif raw.startswith("~") and raw.endswith("~"):
            mode = SearchMode.FUZZY
            raw = raw[1:-1]
        # Detect field prefix: "title:auth" or "code:def validate"
        elif ":" in raw.split()[0] if raw else False:
            prefix = raw.split(":", 1)[0].lower()
            field_map = {
                "title": SearchField.TITLE,
                "content": SearchField.CONTENT,
                "code": SearchField.CODE,
                "diffs": SearchField.DIFFS,
                "tools": SearchField.TOOLS,
                "source": SearchField.SOURCE,
                "project": SearchField.PROJECT,
            }
            if prefix in field_map:
                mode = SearchMode.KEYWORD
                fields = [field_map[prefix]]
                raw = raw.split(":", 1)[1]

        return SearchQuery(raw=raw, mode=mode, fields=fields)

    def get_snippet(self, text: str, query: str, radius: int = 60) -> str:
        """Extract context snippet around query match."""
        idx = text.lower().find(query.lower())
        if idx < 0:
            return text[:self.SNIPPET_LENGTH] + "..." if len(text) > self.SNIPPET_LENGTH else text
        start = max(0, idx - radius)
        end = min(len(text), idx + len(query) + radius)
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet

    # ── Search Strategies ─────────────────────────────────────────

    def _search_keyword(self, candidates: List[Engram], query: SearchQuery) -> List[SearchResult]:
        """Default keyword search with multi-field support."""
        results = []
        query_lower = query.raw.lower()
        for engram in candidates:
            score, matched_fields, snippets = self._score_engram(
                engram, query, self._match_keyword, query_lower
            )
            if score > 0:
                results.append(SearchResult(
                    engram=engram, score=score,
                    matched_fields=matched_fields, match_snippets=snippets,
                ))
        return results

    def _search_glob(self, candidates: List[Engram], query: SearchQuery) -> List[SearchResult]:
        """Glob pattern matching (fnmatch)."""
        results = []
        pattern = query.raw
        for engram in candidates:
            score, matched_fields, snippets = self._score_engram(
                engram, query, self._match_glob, pattern
            )
            if score > 0:
                results.append(SearchResult(
                    engram=engram, score=score,
                    matched_fields=matched_fields, match_snippets=snippets,
                ))
        return results

    def _search_regex(self, candidates: List[Engram], query: SearchQuery) -> List[SearchResult]:
        """Regex pattern matching."""
        results = []
        # Parse /pattern/flags
        pattern_str = query.raw
        flags = 0
        if pattern_str.startswith("/"):
            # Extract flags
            last_slash = pattern_str.rfind("/", 1)
            if last_slash > 0:
                flag_str = pattern_str[last_slash + 1:]
                pattern_str = pattern_str[1:last_slash]
                if "i" in flag_str:
                    flags |= re.IGNORECASE
        try:
            regex = re.compile(pattern_str, flags)
        except re.error as e:
            logger.warning(f"Invalid regex pattern: {e}")
            return []

        for engram in candidates:
            score, matched_fields, snippets = self._score_engram(
                engram, query, self._match_regex, regex
            )
            if score > 0:
                results.append(SearchResult(
                    engram=engram, score=score,
                    matched_fields=matched_fields, match_snippets=snippets,
                ))
        return results

    def _search_fuzzy(self, candidates: List[Engram], query: SearchQuery) -> List[SearchResult]:
        """Fuzzy matching with similarity threshold."""
        results = []
        target = query.raw.lower()
        for engram in candidates:
            score, matched_fields, snippets = self._score_engram(
                engram, query, self._match_fuzzy, target
            )
            if score >= self.FUZZY_THRESHOLD:
                results.append(SearchResult(
                    engram=engram, score=score,
                    matched_fields=matched_fields, match_snippets=snippets,
                ))
        return results

    def _search_boolean(self, candidates: List[Engram], query: SearchQuery) -> List[SearchResult]:
        """Boolean expression parsing: word1 AND word2 OR NOT word3."""
        results = []
        expr = self._parse_boolean(query.raw)
        for engram in candidates:
            score, matched_fields, snippets = self._score_engram(
                engram, query, self._match_boolean, expr
            )
            if score > 0:
                results.append(SearchResult(
                    engram=engram, score=score,
                    matched_fields=matched_fields, match_snippets=snippets,
                ))
        return results

    # ── Match Functions ───────────────────────────────────────────

    def _match_keyword(self, text: str, query_lower: str) -> Tuple[bool, float]:
        """Check if query is a substring (case-insensitive)."""
        if query_lower in text.lower():
            count = text.lower().count(query_lower)
            return True, min(1.0, 0.3 + count * 0.1)
        return False, 0.0

    def _match_glob(self, text: str, pattern: str) -> Tuple[bool, float]:
        """Check if text matches glob pattern."""
        if fnmatch.fnmatch(text.lower(), pattern.lower()):
            return True, 1.0
        return False, 0.0

    def _match_regex(self, text: str, regex: re.Pattern) -> Tuple[bool, float]:
        """Check if text matches regex pattern."""
        if regex.search(text):
            count = len(regex.findall(text))
            return True, min(1.0, 0.3 + count * 0.15)
        return False, 0.0

    def _match_fuzzy(self, text: str, target: str) -> Tuple[bool, float]:
        """Check fuzzy similarity between text and target."""
        ratio = SequenceMatcher(None, text.lower(), target.lower()).ratio()
        return ratio >= self.FUZZY_THRESHOLD, ratio

    def _match_boolean(self, text: str, expr: Dict[str, Any]) -> Tuple[bool, float]:
        """Evaluate boolean expression against text."""
        result, score = self._eval_boolean(text.lower(), expr)
        return result, score

    # ── Scoring & Field Extraction ────────────────────────────────

    def _get_searchable_texts(self, engram: Engram, fields: List[SearchField]) -> Dict[str, str]:
        """Extract searchable text per field from engram."""
        texts = {}
        use_all = SearchField.ALL in fields

        if use_all or SearchField.TITLE in fields:
            texts["title"] = engram.title or ""
        if use_all or SearchField.CONTENT in fields:
            texts["content"] = " ".join(
                (m.content or "") for m in engram.messages
            )
        if use_all or SearchField.CODE in fields:
            texts["code"] = " ".join(
                str(ctx) for m in engram.messages
                for ctx in (m.code_context or [])
            )
        if use_all or SearchField.DIFFS in fields:
            texts["diffs"] = " ".join(
                str(d) for m in engram.messages
                for d in (m.diffs or [])
            )
        if use_all or SearchField.TOOLS in fields:
            texts["tools"] = " ".join(
                str(t) for m in engram.messages
                for t in (m.tool_use or [])
            )
        if use_all or SearchField.SOURCE in fields:
            texts["source"] = engram.source_file or ""
        if use_all or SearchField.PROJECT in fields:
            texts["project"] = f"{engram.project_name or ''} {engram.project_path or ''}"

        return texts

    def _score_engram(
        self, engram: Engram, query: SearchQuery,
        matcher: Callable, matcher_arg: Any
    ) -> Tuple[float, List[str], List[str]]:
        """Score an engram against query using given matcher."""
        texts = self._get_searchable_texts(engram, query.fields)
        total_score = 0.0
        matched_fields = []
        snippets = []

        for field_name, text in texts.items():
            matched, score = matcher(text, matcher_arg)
            if matched:
                matched_fields.append(field_name)
                total_score += score
                # Extract snippet
                if query.mode == SearchMode.KEYWORD:
                    snippet = self.get_snippet(text, query.raw)
                else:
                    snippet = text[:self.SNIPPET_LENGTH] + "..." if len(text) > self.SNIPPET_LENGTH else text
                if snippet not in snippets:
                    snippets.append(snippet)

        # Normalize score
        final_score = min(1.0, total_score / max(len(texts), 1))
        return final_score, matched_fields, snippets

    # ── Filters ───────────────────────────────────────────────────

    def _apply_filters(self, results: List[SearchResult], query: SearchQuery) -> List[SearchResult]:
        """Apply date, message count, artifact filters."""
        filtered = []
        for r in results:
            eg = r.engram
            # Date range
            if query.date_from and eg.created_at < query.date_from:
                continue
            if query.date_to and eg.created_at > query.date_to:
                continue
            # Message count
            msg_count = len(eg.messages)
            if query.min_messages is not None and msg_count < query.min_messages:
                continue
            if query.max_messages is not None and msg_count > query.max_messages:
                continue
            # Project/IDE filters
            if query.project_name and query.project_name.lower() not in (eg.project_name or "").lower():
                continue
            if query.ide_name:
                actual_ide = (eg.ide_info.name if eg.ide_info else eg.source or "").lower()
                if query.ide_name.lower() not in actual_ide:
                    continue
            filtered.append(r)
        return filtered

    # ── Boolean Parser ──────────────────────────────────────────────

    def _parse_boolean(self, raw: str) -> Dict[str, Any]:
        """
        Parse simple boolean expression.
        Supports: word1 AND word2, word1 OR word2, NOT word
        """
        upper = raw.upper()

        # Check for NOT
        if " NOT " in upper:
            parts = upper.split(" NOT ", 1)
            return {
                "op": "NOT",
                "left": self._parse_boolean(parts[0].strip()),
                "right": parts[1].strip().lower(),
            }

        # Check for AND
        if " AND " in upper:
            parts = upper.split(" AND ", 1)
            return {
                "op": "AND",
                "left": parts[0].strip().lower(),
                "right": parts[1].strip().lower(),
            }

        # Check for OR
        if " OR " in upper:
            parts = upper.split(" OR ", 1)
            return {
                "op": "OR",
                "left": parts[0].strip().lower(),
                "right": parts[1].strip().lower(),
            }

        # Simple word
        return {"op": "TERM", "value": raw.lower().strip()}

    def _eval_boolean(self, text: str, expr: Dict[str, Any]) -> Tuple[bool, float]:
        """Evaluate boolean expression against text."""
        op = expr.get("op")

        if op == "TERM":
            val = expr["value"]
            if val in text:
                count = text.count(val)
                return True, min(1.0, 0.3 + count * 0.1)
            return False, 0.0

        if op == "AND":
            left_val = expr["left"]
            right_val = expr["right"]
            left_ok = left_val in text if isinstance(left_val, str) else self._eval_boolean(text, left_val)[0]
            right_ok = right_val in text if isinstance(right_val, str) else self._eval_boolean(text, right_val)[0]
            if left_ok and right_ok:
                return True, 1.0
            return False, 0.0

        if op == "OR":
            left_val = expr["left"]
            right_val = expr["right"]
            left_ok = left_val in text if isinstance(left_val, str) else self._eval_boolean(text, left_val)[0]
            right_ok = right_val in text if isinstance(right_val, str) else self._eval_boolean(text, right_val)[0]
            if left_ok or right_ok:
                return True, 0.7
            return False, 0.0

        if op == "NOT":
            left_ok = self._eval_boolean(text, expr["left"])[0]
            right_val = expr["right"]
            right_ok = right_val in text if isinstance(right_val, str) else self._eval_boolean(text, right_val)[0]
            if left_ok and not right_ok:
                return True, 0.9
            return False, 0.0

        return False, 0.0

    # ── Data Fetching ───────────────────────────────────────────────

    def _fetch_candidates(self, query: SearchQuery) -> List[Engram]:
        """Fetch candidate engrams from DB or cache."""
        if not self._db:
            return []
        conn = self._db.conn if hasattr(self._db, "conn") else self._db
        cursor = conn.cursor()

        # Build SQL with filters
        sql = (
            "SELECT c.id FROM conversations c "
            "JOIN workspaces w ON w.id = c.workspace_id "
            "LEFT JOIN ides i ON i.id = c.ide_id WHERE 1=1"
        )
        params = []

        if query.project_name:
            sql += " AND LOWER(w.project_name) LIKE ?"
            params.append(f"%{query.project_name.lower()}%")
        if query.ide_name:
            sql += " AND LOWER(COALESCE(i.name, c.source)) LIKE ?"
            params.append(f"%{query.ide_name.lower()}%")
        if query.workspace_key:
            sql += " AND w.workspace_key = ?"
            params.append(query.workspace_key)
        if query.date_from:
            sql += " AND c.created_at >= ?"
            params.append(query.date_from.isoformat())
        if query.date_to:
            sql += " AND c.created_at <= ?"
            params.append(query.date_to.isoformat())

        sql += " LIMIT 200"
        cursor.execute(sql, params)
        ids = [r[0] for r in cursor.fetchall()]

        # Hydrate engrams
        candidates = []
        from src.modules.idegraph.services.search import Search as LegacySearch
        legacy = LegacySearch(db=self._db)
        for cid in ids:
            e = legacy.get_by_id(cid)
            if e:
                candidates.append(e)

        return candidates
