"""
Lightweight in-process task queue for background processing.
No external dependencies (Redis, RabbitMQ). Thread-safe.

Enables: background workers (15.3), queue system (15.5).

:project: CodeCortex
:package: Core.Worker.Queue
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("CodeCortex.Core.Worker.Queue")


class Task:
    """A single queued task."""

    def __init__(self, name: str, fn: Callable, args: tuple = None, kwargs: dict = None):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.fn = fn
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.status = "pending"  # pending, running, done, failed
        self.result: Any = None
        self.error: Optional[str] = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class TaskQueue:
    """Simple in-process background task queue.

    Usage:
        queue = TaskQueue(max_workers=2)
        queue.enqueue("reindex", my_reindex_func, repo_id="abc")
        status = queue.status("task_id")
        queue.start()  # Start processing
    """

    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self._queue: List[Task] = []
        self._active: Dict[str, Task] = {}
        self._done: List[Task] = []
        self._lock = threading.Lock()
        self._running = False
        self._threads: List[threading.Thread] = []

    def enqueue(self, name: str, fn: Callable, *args, **kwargs) -> str:
        """Add a task to the queue. Returns task ID."""
        task = Task(name, fn, args, kwargs)
        with self._lock:
            self._queue.append(task)
        logger.info(f"Task queued: {task.id} ({name})")
        return task.id

    def start(self) -> None:
        """Start background workers."""
        if self._running:
            return
        self._running = True
        for i in range(self.max_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f"worker-{i}")
            t.start()
            self._threads.append(t)
        logger.info(f"Task queue started with {self.max_workers} workers")

    def stop(self) -> None:
        """Stop background workers."""
        self._running = False
        for t in self._threads:
            t.join(timeout=5)
        logger.info("Task queue stopped")

    def status(self, task_id: str) -> Optional[Dict]:
        """Get task status by ID."""
        with self._lock:
            for task in self._queue:
                if task.id == task_id:
                    return task.to_dict()
            for task in self._active.values():
                if task.id == task_id:
                    return task.to_dict()
            for task in self._done:
                if task.id == task_id:
                    d = task.to_dict()
                    d["result"] = str(task.result)[:200] if task.result else None
                    return d
        return None

    def list_tasks(self, limit: int = 20) -> List[Dict]:
        """List recent tasks."""
        with self._lock:
            tasks = self._done[-limit:] + list(self._active.values()) + self._queue[-limit:]
            return [t.to_dict() for t in tasks[:limit]]

    def _worker_loop(self) -> None:
        """Worker thread: pick tasks from queue and execute."""
        while self._running:
            task: Optional[Task] = None
            with self._lock:
                if self._queue:
                    task = self._queue.pop(0)
                    if task:
                        self._active[task.id] = task

            if task:
                task.status = "running"
                task.started_at = datetime.now(timezone.utc).isoformat()
                try:
                    task.result = task.fn(*task.args, **task.kwargs)
                    task.status = "done"
                except Exception as e:
                    task.error = str(e)
                    task.status = "failed"
                    logger.error(f"Task {task.id} ({task.name}) failed: {e}")
                task.completed_at = datetime.now(timezone.utc).isoformat()

                with self._lock:
                    self._active.pop(task.id, None)
                    self._done.append(task)
            else:
                time.sleep(0.5)

    def stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            return {
                "queued": len(self._queue),
                "active": len(self._active),
                "completed": len(self._done),
                "max_workers": self.max_workers,
                "running": self._running,
            }


# Global singleton
_default_queue: Optional[TaskQueue] = None


def get_queue() -> TaskQueue:
    """Get or create the default task queue."""
    global _default_queue
    if _default_queue is None:
        _default_queue = TaskQueue(max_workers=2)
    return _default_queue


def start_worker() -> None:
    """Start the default worker queue."""
    get_queue().start()
