"""
TreeSitterManager – Thread-safe language cache and parser lifecycle.

:project: CodeCortex
:package: Core.Parser.Tree_sitter_manager
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import importlib
import sys
import threading
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from tree_sitter import Language, Parser

Language = Any
Parser = Any
_tree_sitter_import_error: Optional[ImportError] = None
_Language = None
_Parser = None
_get_language_pack = None
_lock = threading.Lock()

def _missing_tree_sitter_error(import_error: ImportError) -> ImportError:
    if sys.version_info[:2] == (3, 13):
        return ImportError(
            "Tree-sitter parsing is not available on Python 3.13 because "
            "tree-sitter-language-pack does not publish cp313 wheels. "
            "Use Python 3.12 or 3.14 for indexing/parsing."
        )
    return ImportError(
        "tree-sitter and tree-sitter-language-pack are required for code parsing. "
        "Install them with: pip install tree-sitter tree-sitter-language-pack"
    )

def _load_tree_sitter_dependencies():
    global _tree_sitter_import_error, _Language, _Parser, _get_language_pack

    with _lock:
        if _Language is not None and _Parser is not None:
            return _Language, _Parser

        try:
            from tree_sitter import Language as ImportedLanguage, Parser as ImportedParser

            _Language = ImportedLanguage
            _Parser = ImportedParser
        except ImportError as e:
            _tree_sitter_import_error = e
            raise _missing_tree_sitter_error(e) from e

        if _get_language_pack is None:
            try:
                from tree_sitter_language_pack import get_language as imported_get_language

                _get_language_pack = imported_get_language
            except ImportError:
                _get_language_pack = None
        return _Language, _Parser

def _load_language_from_wheels(canonical_name: str) -> Any:
    LanguageCls, _ = _load_tree_sitter_dependencies()

    if canonical_name == "typescript":
        mod = importlib.import_module("tree_sitter_typescript")
        return LanguageCls(mod.language_typescript())

    if canonical_name == "tsx":
        mod = importlib.import_module("tree_sitter_typescript")
        return LanguageCls(mod.language_tsx())

    try:
        mod_name = f"tree_sitter_{canonical_name}"
        mod = importlib.import_module(mod_name)
        return LanguageCls(mod.language())
    except ImportError:
        if canonical_name == "css":
            raise ImportError(
                f"Tree-sitter grammar not installed for language '{canonical_name}'. "
                "CSS/SCSS parsing will use regex fallback."
            )
        raise ImportError(
            f"Tree-sitter grammar wheel not installed for language '{canonical_name}'. "
            "Install the matching 'tree-sitter-<language>' package or enable tree-sitter-language-pack."
        )

class TreeSitterManager:
    _instance: Optional["TreeSitterManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "TreeSitterManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._languages: Dict[str, Any] = {}
                    cls._instance._parsers: Dict[str, Any] = {}
        return cls._instance

    def get_parser(self, language: str) -> Optional[Parser]:
        if language not in self._parsers:
            lang = self.get_language(language)
            if lang is not None:
                LanguageCls, ParserCls = _load_tree_sitter_dependencies()
                self._parsers[language] = ParserCls(lang)
            else:
                self._parsers[language] = None
        return self._parsers.get(language)

    def get_language(self, canonical_name: str) -> Optional[Language]:
        if canonical_name not in self._languages:
            try:
                self._languages[canonical_name] = _load_language_from_wheels(canonical_name)
            except ImportError:
                self._languages[canonical_name] = None
        return self._languages.get(canonical_name)

    def get_language_safe(self, canonical_name: str) -> Language:
        if canonical_name not in self._languages:
            self._languages[canonical_name] = _load_language_from_wheels(canonical_name)
        return self._languages[canonical_name]

    def create_parser(self, language: str) -> Optional[Parser]:
        return self.get_parser(language)

    def clear(self):
        with _lock:
            self._languages.clear()
            self._parsers.clear()

    @staticmethod
    def reset():
        with TreeSitterManager._lock:
            if TreeSitterManager._instance is not None:
                TreeSitterManager._instance.clear()
                TreeSitterManager._instance = None

def get_tree_sitter_manager() -> TreeSitterManager:
    return TreeSitterManager()

def get_language_safe(language: str) -> Language:
    return TreeSitterManager().get_language_safe(language)


def create_parser(language: str) -> Optional[Parser]:
    return TreeSitterManager().get_parser(language)


def execute_query(language, query, node):
    """Execute a Tree-Sitter query on a node, normalising across API versions.

    Returns a list of (node, capture_name) tuples.

    API history:
      < 0.22  : Query.execute(node)  → list[(node, name)]
      0.22-0.23: Query.captures(node) → dict{name: [nodes]} or list[(node,name)]
      >=0.24  : QueryCursor(query).captures(node) → list[(pattern_idx, {name: [nodes]})]
    """
    import tree_sitter as _ts
    lang_obj = language
    if hasattr(language, "language"):
        lang_obj = language.language
    q = _ts.Query(lang_obj, query)

    # ── tree-sitter >=0.24: QueryCursor ────────────────────────────────
    if hasattr(_ts, "QueryCursor"):
        cursor = _ts.QueryCursor(q)
        raw = cursor.captures(node)
        # raw is list of (Node, str) or dict{str: [Node]}
        if isinstance(raw, dict):
            result = []
            for capture_name, nodes in raw.items():
                for n in nodes:
                    result.append((n, capture_name))
            return result
        return raw  # already list[(node, name)]

    # ── tree-sitter 0.22-0.23: Query.captures ──────────────────────────
    if hasattr(q, "captures"):
        raw = q.captures(node)
        if isinstance(raw, dict):
            result = []
            for capture_name, nodes in raw.items():
                for n in nodes:
                    result.append((n, capture_name))
            return result
        return raw

    # ── Legacy <0.22: Query.execute ────────────────────────────────────
    if hasattr(q, "execute"):
        return q.execute(node)

    return []  # unknown version — return empty, callers handle gracefully
