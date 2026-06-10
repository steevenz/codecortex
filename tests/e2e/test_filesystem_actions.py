"""
Unit tests for codecortex:filesystem tool - 11 actions.

Actions tested:
1. read - Read a file
2. write - Write/create a file
3. delete - Delete file or directory
4. copy - Copy file or directory
5. move - Move/rename file or directory
6. mkdir - Create directory
7. list - List directory contents
8. search - Search filesystem
9. watch - Poll-based filesystem change detection
10. usage - Disk usage analysis
11. audit - File permissions and security audit
"""
import pytest
import tempfile
import os
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.main import CortexOrchestrator


class TestFilesystemActions:
    """Test all 11 filesystem actions."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Setup test environment."""
        self.test_db_path = str(tmp_path / "test_fs.db")
        self.orchestrator = CortexOrchestrator(self.test_db_path)
        self.test_dir = str(tmp_path / "test_fs")
        os.makedirs(self.test_dir, exist_ok=True)
        yield
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    @pytest.mark.asyncio
    async def test_01_fs_read_action(self):
        """Test: filesystem read action."""
        test_file = Path(self.test_dir) / "read_test.py"
        test_file.write_text("print('hello world')")
        result = await self.orchestrator.fs_service.read_file(str(test_file))
        assert result is not None
        assert "content" in result or "data" in result

    @pytest.mark.asyncio
    async def test_02_fs_write_action(self):
        """Test: filesystem write action."""
        test_file = Path(self.test_dir) / "write_test.py"
        result = await self.orchestrator.fs_service.write_file(
            str(test_file), "def test(): pass\n"
        )
        assert result is not None
        assert test_file.exists()

    @pytest.mark.asyncio
    async def test_03_fs_delete_action(self):
        """Test: filesystem delete action."""
        test_file = Path(self.test_dir) / "delete_test.py"
        test_file.write_text("print('delete')")
        result = await self.orchestrator.fs_service.delete_file(str(test_file))
        assert result is not None
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_04_fs_copy_action(self):
        """Test: filesystem copy action."""
        src_file = Path(self.test_dir) / "copy_src.py"
        src_file.write_text("print('source')")
        dst_file = Path(self.test_dir) / "copy_dst.py"
        result = await self.orchestrator.fs_service.copy_file(
            str(src_file), str(dst_file)
        )
        assert result is not None
        assert dst_file.exists()

    @pytest.mark.asyncio
    async def test_05_fs_move_action(self):
        """Test: filesystem move action."""
        src_file = Path(self.test_dir) / "move_src.py"
        src_file.write_text("print('source')")
        dst_file = Path(self.test_dir) / "move_dst.py"
        result = await self.orchestrator.fs_service.move_file(
            str(src_file), str(dst_file)
        )
        assert result is not None
        assert dst_file.exists()

    @pytest.mark.asyncio
    async def test_06_fs_mkdir_action(self):
        """Test: filesystem mkdir action."""
        new_dir = Path(self.test_dir) / "new_directory"
        result = await self.orchestrator.fs_service.create_directory(str(new_dir))
        assert result is not None
        assert new_dir.exists()

    @pytest.mark.asyncio
    async def test_07_fs_list_action(self):
        """Test: filesystem list action."""
        result = await self.orchestrator.fs_service.list_directory(self.test_dir)
        assert result is not None
        assert "entries" in result or "files" in result or isinstance(result, list)

    @pytest.mark.asyncio
    async def test_08_fs_search_action(self):
        """Test: filesystem search action."""
        test_file = Path(self.test_dir) / "searchable.py"
        test_file.write_text("def find_me(): pass")
        result = await self.orchestrator.fs_service.search_files(
            self.test_dir, pattern="*.py"
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_09_fs_watch_action(self):
        """Test: filesystem watch action."""
        result = await self.orchestrator.fs_service.watch_directory(
            self.test_dir
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_10_fs_usage_action(self):
        """Test: filesystem usage action."""
        result = await self.orchestrator.fs_service.get_disk_usage(
            self.test_dir
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_11_fs_audit_action(self):
        """Test: filesystem audit action."""
        result = await self.orchestrator.fs_service.audit_filesystem(
            self.test_dir
        )
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])