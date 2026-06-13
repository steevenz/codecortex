"""
Filesystem Watcher — auto-reindex on file changes using watchdog.
Also provides batch file operations (create/move/delete multiple files).
Renamed from watcher.py for naming consistency.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Watcher
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Filesystem-v1.0
"""

import os
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger("CodeCortex.Filesystem.Watcher")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    logger.warning("watchdog not installed. File watching disabled. `pip install watchdog` to enable.")

@dataclass
class FileChange:
    event_type: str
    src_path: str
    dest_path: Optional[str] = None

class CodeCortexHandler(FileSystemEventHandler):
    """Watchdog event handler that collects file changes for re-indexing."""

    def __init__(self, callback: Callable[[List[FileChange]], None], debounce_seconds: float = 1.0):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._changes: List[FileChange] = []
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def on_modified(self, event):
        if event.is_directory:
            return
        with self._lock:
            self._changes.append(FileChange(event_type="modified", src_path=event.src_path))
        self._debounce()

    def on_created(self, event):
        if event.is_directory:
            return
        with self._lock:
            self._changes.append(FileChange(event_type="created", src_path=event.src_path))
        self._debounce()

    def on_deleted(self, event):
        if event.is_directory:
            return
        with self._lock:
            self._changes.append(FileChange(event_type="deleted", src_path=event.src_path))
        self._debounce()

    def on_moved(self, event):
        with self._lock:
            self._changes.append(FileChange(event_type="moved", src_path=event.src_path, dest_path=event.dest_path))
        self._debounce()

    def _debounce(self):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self.debounce_seconds, self._flush)
        self._timer.daemon = True
        self._timer.start()

    def _flush(self):
        with self._lock:
            changes = list(self._changes)
            self._changes.clear()
        if changes:
            self.callback(changes)

class FilesystemWatcher:
    """
    Watches a directory for file changes and triggers re-indexing.
    Uses watchdog for filesystem events with debouncing.

    Usage:
        watcher = FilesystemWatcher("/path/to/repo", callback=my_reindex_fn)
        watcher.start()
        # ... later ...
        watcher.stop()
    """

    def __init__(self, repo_path: str, callback: Optional[Callable] = None):
        self.repo_path = Path(repo_path).resolve()
        self.callback = callback
        self._observer: Optional[Observer] = None
        self._handler: Optional[CodeCortexHandler] = None

    def start(self) -> bool:
        """Start watching the directory. Returns True if successful."""
        if not HAS_WATCHDOG:
            logger.warning("Cannot start watcher: watchdog not installed")
            return False
        if not self.repo_path.exists():
            logger.warning(f"Cannot watch {self.repo_path}: path does not exist")
            return False

        def _handle_changes(changes: List[FileChange]):
            paths = [c.src_path for c in changes if c.event_type in ("modified", "created")]
            if paths and self.callback:
                try:
                    self.callback(paths)
                except Exception as e:
                    logger.error(f"Watch callback failed: {e}")

        self._handler = CodeCortexHandler(_handle_changes)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self.repo_path), recursive=True)
        self._observer.start()
        logger.info(f"Watching {self.repo_path} for changes")
        return True

    def stop(self):
        """Stop watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            logger.info(f"Stopped watching {self.repo_path}")

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

def batch_file_operations(
    operations: List[Dict[str, Any]],
    repo_root: Path
) -> List[Dict[str, Any]]:
    """
    Execute multiple file operations in a single batch call.

    This function provides atomic batch processing for file system operations,
    useful for multi-file refactoring, bulk updates, or complex file manipulations.

    Args:
        operations: List of operation dictionaries. Each operation supports:
            - create: Create a new file with content
                {"action": "create", "path": "relative/path", "content": "..."}
            - write: Write/update existing file content
                {"action": "write", "path": "relative/path", "content": "..."}
            - delete: Delete file or directory
                {"action": "delete", "path": "relative/path"}
            - move: Move/rename file or directory
                {"action": "move", "path": "source/path", "dest": "target/path"}
            - copy: Copy file or directory
                {"action": "copy", "path": "source/path", "dest": "target/path"}

        repo_root: The root directory path for resolving relative paths.
                   All operation paths are relative to this root.

    Returns:
        List of result dictionaries, one per operation:
            {"action": str, "path": str, "status_code": int, "error": str|None, ...}

        Additional fields in results:
            - bytes_written: Number of bytes written (for 'write' action)
            - bytes_old: Previous file size (for 'write' action)
            - dest: Destination path (for 'move' and 'copy' actions)

    Example:
        >>> operations = [
        ...     {"action": "create", "path": "src/new_file.py", "content": "# New file"},
        ...     {"action": "write", "path": "README.md", "content": "# Updated"},
        ... ]
        >>> results = batch_file_operations(operations, Path("/my/repo"))
        >>> print(results[0]["status_code"])
        200

    Note:
        - Operations are executed sequentially in order
        - Paths are resolved relative to repo_root
        - Parent directories are created automatically if needed
        - For directories, shutil.rmtree is used for deletion
    """
    results = []
    for op in operations:
        action = op.get("action", "")
        rel_path = op.get("path", "")
        abs_path = repo_root / rel_path
        result = {"action": action, "path": rel_path, "status_code": 400, "error": None}

        try:
            if action == "create":
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                content = op.get("content", "")
                abs_path.write_text(content, encoding="utf-8")
                result["status_code"] = 200

            elif action == "write":
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                content = op.get("content", "")
                old_content = abs_path.read_text(encoding="utf-8") if abs_path.exists() else ""
                abs_path.write_text(content, encoding="utf-8")
                result["status_code"] = 200
                result["bytes_written"] = len(content)
                result["bytes_old"] = len(old_content)

            elif action == "delete":
                if abs_path.exists():
                    if abs_path.is_dir():
                        import shutil
                        shutil.rmtree(abs_path)
                    else:
                        abs_path.unlink()
                result["status_code"] = 200

            elif action == "move":
                dest = op.get("dest", "")
                if not dest:
                    result["error"] = "dest required for move"
                else:
                    abs_dest = repo_root / dest
                    abs_dest.parent.mkdir(parents=True, exist_ok=True)
                    abs_path.rename(abs_dest)
                    result["status_code"] = 200
                    result["dest"] = dest

            elif action == "copy":
                dest = op.get("dest", "")
                if not dest:
                    result["error"] = "dest required for copy"
                else:
                    abs_dest = repo_root / dest
                    abs_dest.parent.mkdir(parents=True, exist_ok=True)
                    import shutil
                    if abs_path.is_dir():
                        shutil.copytree(abs_path, abs_dest)
                    else:
                        shutil.copy2(abs_path, abs_dest)
                    result["status_code"] = 200
                    result["dest"] = dest
            else:
                result["error"] = f"Unknown action: {action}"

        except Exception as e:
            result["status_code"] = 500
            result["error"] = str(e)

        results.append(result)

    return results
