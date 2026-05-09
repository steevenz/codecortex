"""
Tests for glob-based file walker with concurrent stat.
"""
import os
import sys
import tempfile
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.domain.filesystem.infrastructure.glob_walker import walk_repository_paths, read_file_contents, ScannedFile


def test_walk_repository_paths_basic():
    """Verify glob walker finds files in a temp directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "file1.py").write_text("print('hello')")
        (root / "file2.py").write_text("print('world')")
        (root / "subdir").mkdir()
        (root / "subdir" / "file3.py").write_text("print('nested')")

        results = walk_repository_paths(root, max_file_size_mb=10)
        paths = {r.path for r in results}
        assert "file1.py" in paths
        assert "file2.py" in paths
        assert "subdir/file3.py" in paths
        assert len(results) == 3


def test_walk_repository_paths_excludes_gitignore():
    """Verify .gitignore patterns are respected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "main.py").write_text("print('main')")
        (root / ".gitignore").write_text("*.log\n")
        (root / "debug.log").write_text("debug info")

        results = walk_repository_paths(root, max_file_size_mb=10)
        paths = {r.path for r in results}
        assert "main.py" in paths
        assert "debug.log" not in paths


def test_walk_repository_paths_skips_large():
    """Verify files over max_file_size_mb are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        small = root / "small.py"
        small.write_text("x = 1")
        large = root / "large.bin"
        with open(large, "wb") as f:
            f.seek(2 * 1024 * 1024)  # 2MB
            f.write(b"\0")

        results = walk_repository_paths(root, max_file_size_mb=1)
        paths = {r.path for r in results}
        assert "small.py" in paths
        assert "large.bin" not in paths


def test_read_file_contents():
    """Verify content reading skips binary and non-code files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "code.py").write_text("print('code')")
        (root / "doc.md").write_text("# Title")
        (root / "data.bin").write_bytes(b"\x00\x01\x02")

        scanned = [
            ScannedFile(path="code.py", size=14),
            ScannedFile(path="doc.md", size=7),
            ScannedFile(path="data.bin", size=3),
        ]
        contents = read_file_contents(root, scanned, max_file_size_mb=10)
        content_map = {c.path: c.content for c in contents}
        assert content_map["code.py"] == "print('code')"
        assert content_map["doc.md"] == "# Title"
        assert content_map["data.bin"] is None  # binary skipped


if __name__ == "__main__":
    test_walk_repository_paths_basic()
    test_walk_repository_paths_excludes_gitignore()
    test_walk_repository_paths_skips_large()
    test_read_file_contents()
    print("All glob_walker tests passed.")
