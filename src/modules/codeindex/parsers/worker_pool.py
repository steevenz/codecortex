"""
Worker Pool — parallel file parsing with configurable concurrency.
Ported from GitNexus's worker-pool.ts.
Uses ThreadPoolExecutor for CPU-bound parsing tasks.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Worker_pool
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, TypeVar, Generic, Optional

logger = logging.getLogger("CodeCortex.CodeIndex.WorkerPool")

T = TypeVar("T")
R = TypeVar("R")

MIN_FILES_FOR_PARALLEL = 15
MIN_BYTES_FOR_PARALLEL = 512 * 1024  # 512KB

def should_use_worker_pool(file_count: int, total_bytes: int = 0) -> bool:
    """Determine if worker pool should be used based on file count or total size."""
    return file_count >= MIN_FILES_FOR_PARALLEL or total_bytes >= MIN_BYTES_FOR_PARALLEL

class WorkerPool(Generic[T, R]):
    """
    Configurable thread pool for parallel file processing.

    Uses ThreadPoolExecutor with configurable max_workers.
    Default: CPU count (optimal for CPU-bound parsing).
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        chunk_size: int = 50,
    ):
        self.max_workers = max_workers or os.cpu_count() or 4
        self.chunk_size = chunk_size

    def map(
        self,
        items: List[T],
        fn: Callable[[T], R],
        desc: str = "Processing",
    ) -> List[R]:
        """Process items in parallel using thread pool."""
        if len(items) == 0:
            return []

        if not should_use_worker_pool(len(items)):
            logger.debug(f"{desc}: serial (n={len(items)}, threshold={MIN_FILES_FOR_PARALLEL})")
            return [fn(item) for item in items]

        logger.info(f"{desc}: parallel (n={len(items)}, workers={self.max_workers})")
        results: List[R] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {executor.submit(fn, item): item for item in items}
            for future in as_completed(future_map):
                try:
                    results.append(future.result())
                except Exception as e:
                    item = future_map[future]
                    logger.error(f"{desc} failed for {item}: {e}")
                    results.append(None)  # type: ignore
        return results

    def map_chunked(
        self,
        items: List[T],
        fn: Callable[[List[T]], List[R]],
        desc: str = "Chunked processing",
    ) -> List[R]:
        """Process items in chunks in parallel."""
        if len(items) == 0:
            return []

        chunks = [items[i:i + self.chunk_size] for i in range(0, len(items), self.chunk_size)]
        results: List[R] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {executor.submit(fn, chunk): i for i, chunk in enumerate(chunks)}
            ordered = sorted(future_map.items(), key=lambda x: x[1])
            for future, _idx in ordered:
                try:
                    chunk_results = future.result()
                    results.extend(chunk_results)
                except Exception as e:
                    logger.error(f"{desc} chunk {_idx} failed: {e}")
        return results

def create_index_worker_pool(max_workers: Optional[int] = None) -> WorkerPool:
    """Create a worker pool optimized for code indexing tasks."""
    return WorkerPool(max_workers=max_workers, chunk_size=50)
