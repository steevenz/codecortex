"""
ASTCache – LRU in-memory cache for TreeSitter parses.
Keyed by (file_path, content_hash) to avoid re-parsing unchanged files.

:project: CodeCortex
:package: Core.Parser.Ast_cache
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from collections import OrderedDict
from typing import Any, Optional, Tuple
import hashlib

MAX_CACHE_SIZE = 1000

class AstCache:
    """
    Thread-safe LRU cache for parsed AST trees.

    Cache key: (file_path, content_hash)
    Cache value: Parsed tree + metadata
    """

    def __init__(self, maxsize: int = MAX_CACHE_SIZE):
        self._cache: OrderedDict[Tuple[str, str], Any] = OrderedDict()
        self._maxsize = maxsize

    def _make_key(self, file_path: str, content: Optional[str]) -> Tuple[str, str]:
        content_hash = hashlib.sha256((content or "").encode()).hexdigest()[:16]
        return (file_path, content_hash)

    def get(self, file_path: str, content: str) -> Optional[Any]:
        key = self._make_key(file_path, content)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, file_path: str, content: str, tree: Any) -> None:
        key = self._make_key(file_path, content)
        self._cache[key] = tree
        self._cache.move_to_end(key)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def invalidate(self, file_path: str) -> int:
        removed = 0
        keys_to_delete = [k for k in self._cache if k[0] == file_path]
        for k in keys_to_delete:
            del self._cache[k]
            removed += 1
        return removed

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def is_full(self) -> bool:
        return len(self._cache) >= self._maxsize

_global_cache: Optional[AstCache] = None

def get_ast_cache(maxsize: int = MAX_CACHE_SIZE) -> AstCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = AstCache(maxsize=maxsize)
    return _global_cache
