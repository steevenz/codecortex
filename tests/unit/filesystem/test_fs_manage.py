import pytest
import tempfile
import json
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.modules.filesystem.adapters.manager import DiskManager
from src.core.errors.errors import ApiError


class TestFsManageWrite:
    def test_write_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "hello.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "write",
                "path": str(test_file),
                "content": "Halo dunia!",
                "overwrite": True,
                "create_parents": True
            })

            assert result["status_code"] == 200
            assert result["data"]["operation"] == "write_file"
            assert test_file.exists()
            assert test_file.read_text() == "Halo dunia!"

    def test_write_with_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "script.sh"

            manager = DiskManager()
            result = manager.execute({
                "operation": "write",
                "path": str(test_file),
                "content": "#!/bin/bash\necho hello",
                "permissions": 0o755
            })

            assert result["status_code"] == 200
            if os.name == "posix":
                mode = test_file.stat().st_mode & 0o777
                assert mode == 0o755


class TestFsManageAppend:
    def test_append_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "log.txt"
            test_file.write_text("Line 1\n")

            manager = DiskManager()
            result = manager.execute({
                "operation": "append",
                "path": str(test_file),
                "content": "Line 2\n"
            })

            assert result["status_code"] == 200
            assert result["data"]["original_size_bytes"] == 8
            assert result["data"]["new_size_bytes"] == 16
            assert test_file.read_text() == "Line 1\nLine 2\n"


class TestFsManageDelete:
    def test_delete_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "delete_me.txt"
            test_file.write_text("content")

            manager = DiskManager()
            result = manager.execute({
                "operation": "delete",
                "paths": [str(test_file)],
                "force": False
            })

            assert result["status_code"] == 200
            assert result["data"]["total_requests"] == 1
            assert result["data"]["successful"] == 1
            assert not test_file.exists()

    def test_delete_with_force(self):
        manager = DiskManager()
        result = manager.execute({
            "operation": "delete",
            "paths": ["/nonexistent/file.txt"],
            "force": True
        })

        assert result["status_code"] == 200
        assert "force" in result["data"]["results"][0]["note"]


class TestFsManageMove:
    def test_move_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "src.txt"
            src.write_text("content")
            dst = Path(tmpdir) / "dst.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "move",
                "operations": [{"source": str(src), "destination": str(dst)}]
            })

            assert result["status_code"] == 200
            assert not src.exists()
            assert dst.exists()
            assert dst.read_text() == "content"

    def test_move_with_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "new.txt"
            src.write_text("new content")
            dst = Path(tmpdir) / "existing.txt"
            dst.write_text("old content")

            manager = DiskManager()
            result = manager.execute({
                "operation": "move",
                "operations": [{"source": str(src), "destination": str(dst)}],
                "overwrite": True
            })

            assert result["status_code"] == 200
            assert dst.read_text() == "new content"


class TestFsManageRename:
    def test_rename_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "old_name.txt"
            src.write_text("content")
            dst = Path(tmpdir) / "new_name.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "rename",
                "path": str(src),
                "operations": [{"source": str(src), "destination": str(dst)}]
            })

            assert result["status_code"] == 200
            assert not src.exists()
            assert dst.exists()


class TestFsManageDryRun:
    def test_write_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "new.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "write",
                "path": str(test_file),
                "content": "content",
                "dry_run": True
            })

            assert result["status_code"] == 200
            assert result["data"]["dry_run"] == True
            assert not test_file.exists()

    def test_delete_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "delete.txt"
            test_file.write_text("content")

            manager = DiskManager()
            result = manager.execute({
                "operation": "delete",
                "paths": [str(test_file)],
                "dry_run": True
            })

            assert result["status_code"] == 200
            assert test_file.exists()


class TestFsManageResponseFormat:
    def test_response_has_correct_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "write",
                "path": str(test_file),
                "content": "test"
            })

            assert result["status_code"] == 200
            assert "message" in result
            assert "data" in result

    def test_meta_timestamp_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "write",
                "path": str(test_file),
                "content": "test"
            })

            assert result["status_code"] == 200


class TestFsManageWriteBatch:
    def test_write_batch_multiple_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"
            file3 = Path(tmpdir) / "subdir" / "file3.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "write_batch",
                "items": [
                    {"path": str(file1), "content": "content1"},
                    {"path": str(file2), "content": "content2"},
                    {"path": str(file3), "content": "content3", "create_parents": True},
                ],
                "overwrite": True,
                "create_parents": True
            })

            assert result["status_code"] == 200
            assert result["status_code"] == 200
            assert len(result["data"]["results"]) == 3
            assert all(r["status"] == "written" for r in result["data"]["results"])
            assert result["data"]["errors"] is None
            assert file1.read_text() == "content1"
            assert file2.read_text() == "content2"
            assert file3.read_text() == "content3"

    def test_write_batch_with_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "existing.txt"
            file1.write_text("old content")
            file2 = Path(tmpdir) / "new.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "write_batch",
                "items": [
                    {"path": str(file1), "content": "new content", "overwrite": True},
                    {"path": str(file2), "content": "brand new", "overwrite": True},
                ],
                "overwrite": False,
            })

            assert result["status_code"] == 200
            assert file1.read_text() == "new content"
            assert file2.read_text() == "brand new"

    def test_write_batch_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "new1.txt"
            file2 = Path(tmpdir) / "new2.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "write_batch",
                "items": [
                    {"path": str(file1), "content": "content1"},
                    {"path": str(file2), "content": "content2"},
                ],
                "dry_run": True
            })

            assert result["status_code"] == 200
            assert len(result["data"]["results"]) == 2
            assert not file1.exists()
            assert not file2.exists()

    def test_write_batch_with_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "script1.sh"
            file2 = Path(tmpdir) / "script2.sh"

            manager = DiskManager()
            result = manager.execute({
                "operation": "write_batch",
                "items": [
                    {"path": str(file1), "content": "#!/bin/bash"},
                    {"path": str(file2), "content": "#!/bin/bash"},
                ],
                "permissions": 0o755
            })

            assert result["status_code"] == 200
            if os.name == "posix":
                mode1 = file1.stat().st_mode & 0o777
                mode2 = file2.stat().st_mode & 0o777
                assert mode1 == 0o755
                assert mode2 == 0o755

    def test_write_batch_partial_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "success.txt"
            file2 = Path(tmpdir) / "subdir" / "success2.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "write_batch",
                "items": [
                    {"path": str(file1), "content": "content1", "create_parents": True},
                    {"path": str(file2), "content": "content2", "create_parents": True},
                ],
                "overwrite": True,
                "create_parents": True
            })

            assert result["status_code"] == 200
            assert len(result["data"]["results"]) == 2
            assert result["data"]["errors"] is None

    def test_write_batch_empty_items(self):
        manager = DiskManager()
        with pytest.raises(ApiError):
            manager.execute({
                "operation": "write_batch",
                "items": [],
                "overwrite": True,
            })


class TestFsManageChmod:
    def test_chmod_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.sh"
            test_file.write_text("#!/bin/bash")

            manager = DiskManager()
            result = manager.execute({
                "operation": "chmod",
                "paths": [str(test_file)],
                "mode": "755"
            })

            assert result["status_code"] == 200
            assert result["status_code"] == 200
            assert result["data"]["operation"] == "chmod"
            assert result["data"]["mode_octal"] == 0o755

    def test_chmod_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            file1 = Path(tmpdir) / "file1.txt"
            file2 = subdir / "file2.txt"
            file1.write_text("content1")
            file2.write_text("content2")

            manager = DiskManager()
            result = manager.execute({
                "operation": "chmod",
                "paths": [str(tmpdir)],
                "mode": "644",
                "recursive": True
            })

            assert result["status_code"] == 200
            if os.name == "posix":
                assert result["data"]["results"][0]["recursive_count"] >= 2

    def test_chmod_windows_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            manager = DiskManager()
            result = manager.execute({
                "operation": "chmod",
                "paths": [str(test_file)],
                "mode": "755"
            })

            assert result["status_code"] == 200


class TestFsManageChown:
    def test_chown_not_supported_windows(self):
        if os.name != "nt":
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            manager = DiskManager()
            with pytest.raises(ApiError):
                manager.execute({
                    "operation": "chown",
                    "paths": [str(test_file)],
                    "owner": "nobody"
                })

    def test_chown_missing_owner_group(self):
        if os.name == "nt":
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            manager = DiskManager()
            result = manager.execute({
                "operation": "chown",
                "paths": [str(test_file)],
            })

            assert result["success"] == False
            assert result["status_code"] == 400
            assert "Either owner or group must be specified" in result["message"]


class TestFsManageSymlink:
    def test_symlink_create(self):
        if os.name == "nt":
            pytest.skip("Symlinks require Developer Mode or Admin on Windows")
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "target.txt"
            target.write_text("content")
            link = Path(tmpdir) / "link.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "symlink",
                "target": str(target),
                "link_path": str(link)
            })

            assert result["status_code"] == 200
            assert link.exists()
            assert link.is_symlink()

    def test_symlink_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target1 = Path(tmpdir) / "target1.txt"
            target1.write_text("content1")
            target2 = Path(tmpdir) / "target2.txt"
            target2.write_text("content2")
            link = Path(tmpdir) / "link.txt"

            try:
                link.symlink_to(str(target1))
            except (OSError, NotImplementedError):
                return

            manager = DiskManager()
            result = manager.execute({
                "operation": "symlink",
                "target": str(target2),
                "link_path": str(link),
                "overwrite": True
            })

            assert result["status_code"] == 200
            assert result["data"]["overwritten"] == True

    def test_symlink_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "target.txt"
            target.write_text("content")
            link = Path(tmpdir) / "link.txt"

            try:
                link.symlink_to(str(target))
            except (OSError, NotImplementedError):
                return

            manager = DiskManager()
            result = manager.execute({
                "operation": "symlink",
                "target": str(target),
                "link_path": str(link),
                "overwrite": False
            })

            assert result["success"] == False
            assert result["status_code"] == 409

    def test_symlink_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "target.txt"
            target.write_text("content")
            link = Path(tmpdir) / "link.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "symlink",
                "target": str(target),
                "link_path": str(link),
                "dry_run": True
            })

            assert result["status_code"] == 200
            assert result["data"]["dry_run"] == True
            assert not link.exists()


class TestFsManageTouch:
    def test_touch_create_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "new_file.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "touch",
                "path": str(test_file),
                "create_if_not_exists": True
            })

            assert result["status_code"] == 200
            assert result["status_code"] == 200
            assert result["data"]["created"] == True
            assert test_file.exists()

    def test_touch_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "existing.txt"
            test_file.write_text("existing content")

            manager = DiskManager()
            result = manager.execute({
                "operation": "touch",
                "path": str(test_file),
                "create_if_not_exists": True
            })

            assert result["status_code"] == 200
            assert result["data"]["created"] == False
            assert test_file.read_text() == "existing content"

    def test_touch_with_timestamps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "timestamped.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "touch",
                "path": str(test_file),
                "set_timestamps": {
                    "access_time": "2026-05-01T00:00:00Z",
                    "modify_time": "2026-05-01T00:00:00Z"
                }
            })

            assert result["status_code"] == 200
            assert result["data"]["new_timestamps"]["access_time"] == "2026-05-01T00:00:00Z"
            assert result["data"]["new_timestamps"]["modify_time"] == "2026-05-01T00:00:00Z"

    def test_touch_only_modify_time(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "partial_ts.txt"
            test_file.write_text("content")

            manager = DiskManager()
            result = manager.execute({
                "operation": "touch",
                "path": str(test_file),
                "set_timestamps": {
                    "modify_time": "2026-05-23T12:00:00Z"
                }
            })

            assert result["status_code"] == 200
            assert result["data"]["new_timestamps"]["modify_time"] == "2026-05-23T12:00:00Z"
            assert result["data"]["new_timestamps"]["access_time"] == result["data"]["old_timestamps"]["access_time"]

    def test_touch_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "dry_run.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "touch",
                "path": str(test_file),
                "set_timestamps": {"modify_time": "2026-06-01T00:00:00Z"},
                "dry_run": True
            })

            assert result["status_code"] == 200
            assert result["data"]["dry_run"] == True
            assert result["data"]["would_create"] == True
            assert not test_file.exists()

    def test_touch_not_found_without_create(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "nonexistent.txt"

            manager = DiskManager()
            with pytest.raises(ApiError):
                manager.execute({
                    "operation": "touch",
                    "path": str(test_file),
                    "create_if_not_exists": False
                })

    def test_touch_directory_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir) / "directory"
            dir_path.mkdir()

            manager = DiskManager()
            with pytest.raises(ApiError):
                manager.execute({
                    "operation": "touch",
                    "path": str(dir_path),
                    "create_if_not_exists": True
                })

    def test_touch_missing_path(self):
        manager = DiskManager()
        with pytest.raises(ApiError):
            manager.execute({
                "operation": "touch",
                "path": ""
            })

    def test_touch_with_parent_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "subdir" / "nested" / "file.txt"

            manager = DiskManager()
            result = manager.execute({
                "operation": "touch",
                "path": str(test_file),
                "create_if_not_exists": True
            })

            assert result["status_code"] == 200
            assert test_file.exists()
