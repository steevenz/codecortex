"""
Tests for fs_manage — VCS integration removed.
Git/SVN operations are now handled by repo_git / repo_svn in CodeRepository domain.
"""

import pytest
import tempfile
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.modules.filesystem.adapters.manager import DiskManager


class TestFsManageNoVcs:
    """Verify fs_manage no longer processes git/svn params."""

    def test_git_param_ignored_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            manager = DiskManager()
            result = manager.execute({
                "operation": "delete",
                "paths": [str(test_file)],
                "git": True,
                "force": True,
            })
            assert result["status_code"] == 200

    def test_git_param_ignored_move(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "src.txt"
            src.write_text("content")
            dst = Path(tmpdir) / "dst.txt"
            manager = DiskManager()
            result = manager.execute({
                "operation": "move",
                "operations": [{"source": str(src), "destination": str(dst)}],
                "git": True,
            })
            assert result["status_code"] == 200

    def test_svn_param_ignored_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            manager = DiskManager()
            result = manager.execute({
                "operation": "write",
                "path": str(test_file),
                "content": "hello",
                "svn": True,
            })
            assert result["status_code"] == 200
            assert test_file.exists()

    def test_unknown_param_no_error(self):
        """Extra params should not crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            manager = DiskManager()
            result = manager.execute({
                "operation": "write",
                "path": str(test_file),
                "content": "hello",
                "some_random_param": 42,
            })
            assert result["status_code"] == 200


class TestFsManageBasicOps:
    """Basic filesystem operations still work."""

    def test_write_and_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            manager = DiskManager()
            result = manager.execute({
                "operation": "write",
                "path": str(test_file),
                "content": "content",
            })
            assert result["status_code"] == 200
            assert test_file.exists()

            result = manager.execute({
                "operation": "delete",
                "paths": [str(test_file)],
                "force": True,
            })
            assert result["status_code"] == 200
            assert not test_file.exists()

    def test_write_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DiskManager()
            result = manager.execute({
                "operation": "write_batch",
                "items": [
                    {"path": str(Path(tmpdir) / "a.txt"), "content": "a"},
                    {"path": str(Path(tmpdir) / "b.txt"), "content": "b"},
                ],
            })
            assert result["status_code"] == 200
            assert len(result["data"]["results"]) == 2

    def test_move(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "src.txt"
            src.write_text("content")
            dst = Path(tmpdir) / "dst.txt"
            manager = DiskManager()
            result = manager.execute({
                "operation": "move",
                "operations": [{"source": str(src), "destination": str(dst)}],
            })
            assert result["status_code"] == 200
            assert not src.exists()
            assert dst.exists()

    def test_response_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            manager = DiskManager()
            result = manager.execute({
                "operation": "delete",
                "paths": [str(test_file)],
                "force": True,
            })
            assert "success" in result
            assert "status_code" in result
            assert "data" in result
