"""
Tests for worker pool.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.domain.codeindex.infrastructure.worker_pool import (
    WorkerPool,
    should_use_worker_pool,
    create_index_worker_pool,
)


def test_should_use_worker_pool_large():
    assert should_use_worker_pool(file_count=100) is True


def test_should_use_worker_pool_small():
    assert should_use_worker_pool(file_count=5) is False


def test_should_use_worker_pool_large_bytes():
    assert should_use_worker_pool(file_count=5, total_bytes=1024 * 1024) is True


def test_worker_pool_map():
    pool = WorkerPool(max_workers=2)
    results = pool.map([1, 2, 3], lambda x: x * 2)
    assert results == [2, 4, 6]


def test_worker_pool_empty():
    pool = WorkerPool(max_workers=2)
    results = pool.map([], lambda x: x)
    assert results == []


def test_worker_pool_chunked():
    pool = WorkerPool(max_workers=2, chunk_size=2)
    items = [1, 2, 3, 4]
    results = pool.map_chunked(items, lambda chunk: [x * 2 for x in chunk])
    assert results == [2, 4, 6, 8]


def test_create_index_worker_pool():
    pool = create_index_worker_pool(max_workers=4)
    assert pool.max_workers == 4


if __name__ == "__main__":
    test_should_use_worker_pool_large()
    test_should_use_worker_pool_small()
    test_should_use_worker_pool_large_bytes()
    test_worker_pool_map()
    test_worker_pool_empty()
    test_worker_pool_chunked()
    test_create_index_worker_pool()
    print("All worker pool tests passed.")
