"""
Tests for AST cache module.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.core.parser.ast_cache import AstCache, get_ast_cache


def test_ast_cache_basic():
    cache = AstCache(maxsize=100)
    assert cache.size == 0
    cache.set("file1.py", "print('hello')", {"symbols": ["hello"], "tree": "mock"})
    assert cache.size == 1
    result = cache.get("file1.py", "print('hello')")
    assert result is not None
    assert result["symbols"] == ["hello"]


def test_ast_cache_cache_miss():
    cache = AstCache(maxsize=100)
    cache.set("file1.py", "content1", {"data": "a"})
    result = cache.get("file1.py", "content2")  # Different content = different hash
    assert result is None


def test_ast_cache_lru_eviction():
    cache = AstCache(maxsize=3)
    cache.set("a.py", "a", 1)
    cache.set("b.py", "b", 2)
    cache.set("c.py", "c", 3)
    assert cache.size == 3
    # Access 'a' to make it recently used
    cache.get("a.py", "a")
    # Add 'd' which should evict 'b' (LRU)
    cache.set("d.py", "d", 4)
    assert cache.size == 3
    assert cache.get("a.py", "a") is not None  # 'a' was accessed, so kept
    assert cache.get("b.py", "b") is None  # 'b' should be evicted
    assert cache.get("c.py", "c") is not None
    assert cache.get("d.py", "d") is not None


def test_ast_cache_invalidate():
    cache = AstCache(maxsize=100)
    cache.set("file1.py", "v1", 1)
    cache.set("file1.py", "v2", 2)
    cache.set("file2.py", "v1", 3)
    assert cache.size == 3
    removed = cache.invalidate("file1.py")
    assert removed == 2
    assert cache.size == 1
    assert cache.get("file2.py", "v1") is not None


def test_ast_cache_clear():
    cache = AstCache(maxsize=100)
    cache.set("a.py", "x", 1)
    cache.set("b.py", "y", 2)
    assert cache.size == 2
    cache.clear()
    assert cache.size == 0


def test_global_cache_singleton():
    c1 = get_ast_cache()
    c2 = get_ast_cache()
    assert c1 is c2


def test_ast_cache_is_full():
    cache = AstCache(maxsize=2)
    assert not cache.is_full
    cache.set("a.py", "a", 1)
    assert not cache.is_full
    cache.set("b.py", "b", 2)
    assert cache.is_full


def test_ast_cache_none_content():
    cache = AstCache(maxsize=100)
    cache.set("f.py", "", {"data": "empty"})
    result = cache.get("f.py", "")
    assert result is not None


def test_ast_cache_invalidate_nonexistent():
    cache = AstCache(maxsize=100)
    removed = cache.invalidate("nonexistent.py")
    assert removed == 0


if __name__ == "__main__":
    test_ast_cache_basic()
    test_ast_cache_cache_miss()
    test_ast_cache_lru_eviction()
    test_ast_cache_invalidate()
    test_ast_cache_clear()
    test_global_cache_singleton()
    print("All AST cache tests passed.")
