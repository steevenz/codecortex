"""
/**
 * @project   CodeCortex
 * @package   Core/TreeSitter
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * TreeSitterManager — Thread-safe language cache and parser lifecycle.
 *   Ported from legacy codegraph utils/tree_sitter_manager.py.
 *   Handles tree-sitter-language-pack loading with graceful degradation.
 */
"""

from __future__ import annotations

import sys
import threading
import importlib
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from tree_sitter import Language, Parser

Language = Any
Parser = Any
_tree_sitter_import_error: Optional[ImportError] = None
_Language = None
_Parser = None
_get_language_pack = None


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

    if _Language is not None and _Parser is not None:
        return _Language, _Parser

    try:
        from tree_sitter import Language as ImportedLanguage, Parser as ImportedParser
    except ImportError as e:
        _tree_sitter_import_error = e
        raise _missing_tree_sitter_error(e) from e

    _Language = ImportedLanguage
    _Parser = ImportedParser
    if _get_language_pack is None:
        try:
            from tree_sitter_language_pack import get_language as imported_get_language
            _get_language_pack = imported_get_language
        except ImportError:
            _get_language_pack = None
    return _Language, _Parser


def _load_language_from_wheels(canonical_name: str) -> Any:
    """
    Load a tree-sitter Language using per-language wheels.

    Tree-sitter language wheels expose a function returning a capsule object,
    which must be wrapped by tree_sitter.Language(...).
    """
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
            # CSS parser not installed; will fall back to regex in language parser
            raise ImportError(
                f"Tree-sitter grammar not installed for language '{canonical_name}'. "
                "CSS/SCSS parsing will use regex fallback."
            )
        raise ImportError(
            f"Tree-sitter grammar wheel not installed for language '{canonical_name}'. "
            "Install the matching 'tree-sitter-<language>' package or enable tree-sitter-language-pack."
        )


# Language name aliases for compatibility
LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "tsx": "tsx",
    "c++": "cpp",
    "c#": "c_sharp",
    "csharp": "c_sharp",
    "cs": "c_sharp",
    "rb": "ruby",
    "rs": "rust",
    "go": "go",
    "php": "php",
    ".php": "php",
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "cpp": "cpp",
    "c_sharp": "c_sharp",
    "c": "c",
    "java": "java",
    "haskell": "haskell",
    "ruby": "ruby",
    "rust": "rust",
    "kt": "kotlin",
    "kotlin": "kotlin",
    "scala": "scala",
    ".scala": "scala",
    "swift": "swift",
    ".swift": "swift",
    "dart": "dart",
    "perl": "perl",
    "pl": "perl",
    "pm": "perl",
    "elixir": "elixir",
    "ex": "elixir",
    "exs": "elixir",
    "css": "css",
    "scss": "css",
    "sass": "css",
    "less": "css",
    # Additional languages
    "vue": "vue",
    "cob": "cobol",
    "cbl": "cobol",
    "cobol": "cobol",
    "jl": "julia",
    "julia": "julia",
    "lua": "lua",
    "m": "objc",
    "mm": "objc",
    "objectivec": "objc",
    "ps1": "powershell",
    "powershell": "powershell",
    "v": "verilog",
    "sv": "verilog",
    "verilog": "verilog",
    "zig": "zig",
    "zir": "zig",
}

# Canonical names that differ from tree-sitter-language-pack names
LANGUAGE_PACK_NAMES = {
    "c_sharp": "csharp",
}


class TreeSitterManager:
    """
    Manages tree-sitter language loading and parser creation.

    - Thread-safe language caching (languages are cached, parsers are NOT thread-safe)
    - Language name aliasing
    - Clear error handling
    """

    def __init__(self):
        self._language_cache: Dict[str, Language] = {}
        self._cache_lock = threading.Lock()

    def _normalize_language_name(self, lang: str) -> str:
        normalized = LANGUAGE_ALIASES.get(lang.lower())
        if normalized is None:
            supported = ", ".join(sorted(set(LANGUAGE_ALIASES.values())))
            raise ValueError(f"Unknown language: {lang}. Supported: {supported}")
        return normalized

    def get_language_safe(self, lang: str) -> Language:
        canonical_name = self._normalize_language_name(lang)
        _load_tree_sitter_dependencies()

        with self._cache_lock:
            if canonical_name in self._language_cache:
                return self._language_cache[canonical_name]

            try:
                pack_name = LANGUAGE_PACK_NAMES.get(canonical_name, canonical_name)
                if _get_language_pack is not None:
                    language = _get_language_pack(pack_name)
                else:
                    language = _load_language_from_wheels(canonical_name)
                self._language_cache[canonical_name] = language
                return language
            except Exception as e:
                raise Exception(f"Failed to load language '{canonical_name}': {e}")

    def create_parser(self, lang: str) -> Parser:
        _, parser_cls = _load_tree_sitter_dependencies()
        language = self.get_language_safe(lang)
        return parser_cls(language)

    def is_language_available(self, lang: str) -> bool:
        try:
            self.get_language_safe(lang)
            return True
        except (ValueError, Exception):
            return False

    def get_supported_languages(self) -> list[str]:
        return sorted(set(LANGUAGE_ALIASES.values()))


# Global singleton instance
_manager_instance: Optional[TreeSitterManager] = None
_instance_lock = threading.Lock()


def get_tree_sitter_manager() -> TreeSitterManager:
    global _manager_instance
    if _manager_instance is not None:
        return _manager_instance
    with _instance_lock:
        if _manager_instance is None:
            _manager_instance = TreeSitterManager()
        return _manager_instance


# Convenience functions for backward compatibility
def get_language_safe(lang: str) -> Language:
    return get_tree_sitter_manager().get_language_safe(lang)


def create_parser(lang: str) -> Parser:
    return get_tree_sitter_manager().create_parser(lang)


def execute_query(language: Language, query_string: str, node: Any):
    """
    Execute a tree-sitter query and return captures in backward-compatible format.
    Compatible with tree-sitter 0.20.x, 0.24.x, and 0.25+ APIs.
    """
    try:
        from tree_sitter import Query, QueryCursor
    except ImportError as e:
        raise _missing_tree_sitter_error(e) from e
    query = Query(language, query_string)

    # Try 0.25.x API: QueryCursor(query) then cursor.matches(node)
    # Returns [(pattern_idx, {capture_name: [node, ...]})]
    try:
        cursor = QueryCursor(query)
        matched = cursor.matches(node)
        captures = []
        for _pattern_idx, capture_dict in matched:
            for name, nodes in capture_dict.items():
                if not isinstance(nodes, list):
                    continue
                for n in nodes:
                    captures.append((n, name))
        if captures:
            return captures
    except (TypeError, AttributeError):
        pass

    # Try 0.20.x API: QueryCursor() then cursor.exec() / cursor.next_capture()
    try:
        cursor = QueryCursor()
        cursor.exec(query, node)
        captures = []
        capture = cursor.next_capture()
        while capture is not None:
            node_ref, capture_index = capture
            captures.append((node_ref, query.capture_names[capture_index]))
            capture = cursor.next_capture()
        return captures
    except (TypeError, AttributeError):
        pass

    return []


# ── Query.captures() backward compatibility is handled by replacing
#    query.captures() with execute_query() in each language parser.
#    See src/domain/codeindex/infrastructure/parsers/languages/*.py
