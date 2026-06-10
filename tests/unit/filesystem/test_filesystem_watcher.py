"""
Tests for Filesystem watcher and batch operations.
"""
import sys, os, tempfile, time
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
import pytest


def test_batch_file_create():
    from src.modules.filesystem.adapters.watcher import batch_file_operations
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        ops = [{"action": "create", "path": "src/main.py", "content": "print('hello')\n"},
               {"action": "create", "path": "src/utils.py", "content": "def helper(): pass\n"}]
        results = batch_file_operations(ops, root)
        assert len(results) == 2
        assert all(r["status_code"] == 200 for r in results)
        assert (root / "src/main.py").exists()
        assert (root / "src/utils.py").exists()


def test_batch_file_write():
    from src.modules.filesystem.adapters.watcher import batch_file_operations
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "test.py").write_text("old content")
        ops = [{"action": "write", "path": "test.py", "content": "new content"}]
        results = batch_file_operations(ops, root)
        assert results[0]["status_code"] == 200
        assert root / "test.py" is not None


def test_batch_file_delete():
    from src.modules.filesystem.adapters.watcher import batch_file_operations
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "to_delete.py").write_text("delete me")
        ops = [{"action": "delete", "path": "to_delete.py"}]
        results = batch_file_operations(ops, root)
        assert results[0]["status_code"] == 200
        assert not (root / "to_delete.py").exists()


def test_batch_file_move():
    from src.modules.filesystem.adapters.watcher import batch_file_operations
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "source.py").write_text("move me")
        ops = [{"action": "move", "path": "source.py", "dest": "dest.py"}]
        results = batch_file_operations(ops, root)
        assert results[0]["status_code"] == 200
        assert not (root / "source.py").exists()
        assert (root / "dest.py").exists()


def test_batch_file_copy():
    from src.modules.filesystem.adapters.watcher import batch_file_operations
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "original.py").write_text("copy me")
        ops = [{"action": "copy", "path": "original.py", "dest": "copy.py"}]
        results = batch_file_operations(ops, root)
        assert results[0]["status_code"] == 200
        assert (root / "original.py").exists()
        assert (root / "copy.py").exists()


def test_batch_unknown_action():
    from src.modules.filesystem.adapters.watcher import batch_file_operations
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        ops = [{"action": "unknown", "path": "x.py"}]
        results = batch_file_operations(ops, root)
        assert results[0]["status_code"] != 200


def test_watcher_init():
    from src.modules.filesystem.adapters.watcher import FilesystemWatcher
    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FilesystemWatcher(tmpdir)
        assert watcher.repo_path == Path(tmpdir).resolve()
        assert not watcher.is_running


def test_watcher_start_stop():
    from src.modules.filesystem.adapters.watcher import FilesystemWatcher
    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FilesystemWatcher(tmpdir)
        result = watcher.start()
        if result:
            time.sleep(0.5)
            assert watcher.is_running
            watcher.stop()
            assert not watcher.is_running


if __name__ == "__main__":
    test_batch_file_create()
    test_batch_file_write()
    test_batch_file_delete()
    test_batch_file_move()
    test_batch_file_copy()
    test_batch_unknown_action()
    test_watcher_init()
    test_watcher_start_stop()
    print("ALL FILESYSTEM TESTS PASSED!")
