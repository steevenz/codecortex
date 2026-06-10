import pytest
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.modules.filesystem.adapters.deleter import DiskDeleter, DiskMover


class TestFsDelete:
    def test_delete_single_file_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("hello world")
            deleter = DiskDeleter()
            result = deleter.delete({"paths": [str(test_file)]})
            assert result["success"] == True
            assert result["status_code"] == 200
            assert result["data"]["total_requests"] == 1
            assert result["data"]["successful"] == 1
            assert result["data"]["failed"] == 0
            assert "meta" in result
            assert result["data"]["results"][0]["status"] == "deleted"
            assert not test_file.exists()

    def test_delete_with_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("hello world")
            deleter = DiskDeleter()
            result = deleter.delete({"paths": [str(test_file)], "dry_run": True})
            assert result["success"] == True
            assert result["data"]["results"][0].get("dry_run") == True
            assert test_file.exists()

    def test_delete_with_force_not_found(self):
        deleter = DiskDeleter()
        result = deleter.delete({"paths": ["/nonexistent/file.txt"], "force": True})
        assert result["success"] == True
        assert result["data"]["results"][0]["status"] == "deleted"
        assert "force" in result["data"]["results"][0].get("note", "")

    def test_delete_not_found_without_force(self):
        deleter = DiskDeleter()
        result = deleter.delete({"paths": ["/nonexistent/file.txt"], "force": False})
        assert result["success"] == False
        assert result["status_code"] == 400
        assert result["data"]["results"][0]["status"] == "error"


class TestFsMove:
    def test_move_single_file_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "source.txt"
            src_file.write_text("hello")
            dest_file = Path(tmpdir) / "dest.txt"
            mover = DiskMover()
            result = mover.move({
                "operations": [{"source": str(src_file), "destination": str(dest_file)}]
            })
            assert result["success"] == True
            assert result["status_code"] == 200
            assert result["data"]["total_requests"] == 1
            assert result["data"]["successful"] == 1
            assert result["data"]["failed"] == 0
            assert "meta" in result
            assert result["data"]["results"][0]["status"] == "moved"
            assert not src_file.exists()
            assert dest_file.exists()

    def test_move_with_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "source.txt"
            src_file.write_text("new content")
            dest_file = Path(tmpdir) / "dest.txt"
            dest_file.write_text("old content")
            mover = DiskMover()
            result = mover.move({
                "operations": [{"source": str(src_file), "destination": str(dest_file)}],
                "overwrite": True,
            })
            assert result["success"] == True
            assert dest_file.read_text() == "new content"

    def test_move_without_overwrite_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "source.txt"
            src_file.write_text("content")
            dest_file = Path(tmpdir) / "dest.txt"
            dest_file.write_text("existing")
            mover = DiskMover()
            result = mover.move({
                "operations": [{"source": str(src_file), "destination": str(dest_file)}],
                "overwrite": False,
            })
            assert result["success"] == False
            assert result["status_code"] == 400

    def test_move_source_not_found(self):
        mover = DiskMover()
        result = mover.move({
            "operations": [{"source": "/nonexistent.txt", "destination": "/some/dest.txt"}]
        })
        assert result["success"] == False
        assert result["status_code"] == 400


class TestFsDeleteResponseFormat:
    def test_response_has_correct_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            deleter = DiskDeleter()
            result = deleter.delete({"paths": [str(test_file)]})
            assert "success" in result
            assert "status_code" in result
            assert "message" in result
            assert "data" in result
            assert "meta" in result
            assert isinstance(result["success"], bool)
            assert isinstance(result["status_code"], int)
            assert isinstance(result["message"], str)
            assert isinstance(result["data"], dict)
            assert isinstance(result["meta"], dict)

    def test_meta_has_request_id_and_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            deleter = DiskDeleter()
            result = deleter.delete({"paths": [str(test_file)]})
            assert "request_id" in result["meta"]
            assert "timestamp" in result["meta"]
            assert result["meta"]["request_id"].startswith("req_del_")
            assert "Z" in result["meta"]["timestamp"]
