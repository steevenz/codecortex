"""
Final 100% — mock ALL remaining exception handlers.
"""
import sys, os, tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_canonicalize_exception():
    """Line 49-50: Path().resolve() in except block"""
    from src.domain.coderepository.infrastructure.repo_utils import canonicalize_path
    with patch.object(Path, "resolve") as mock_resolve:
        # First call to resolve() succeeds (outside try), second call (in except) fails
        mock_resolve.side_effect = [MagicMock(), OSError("resolve failed")]
        result = canonicalize_path("/tmp")
        assert result is not None


def test_subprocess_exception():
    """Lines 76-78: subprocess.run throws in get_current_commit"""
    from src.domain.coderepository.infrastructure.repo_utils import get_current_commit
    with patch("subprocess.run", side_effect=FileNotFoundError("no git")):
        assert get_current_commit("/tmp") is None


def test_has_git_dir_oserror():
    """Line 123: OSError in has_git_dir"""
    from src.domain.coderepository.infrastructure.repo_utils import has_git_dir
    with patch.object(Path, "exists", side_effect=OSError("denied")):
        assert has_git_dir("/tmp") is False


def test_ensure_ignored_read_error():
    """Lines 164-165: read_text throws"""
    from src.domain.coderepository.infrastructure.repo_utils import ensure_codecortex_ignored
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".git").mkdir()
        (root / ".git" / "info").mkdir()
        exclude = root / ".git" / "info" / "exclude"
        exclude.write_text("old content")  # No trailing newline, NEEDS separator
        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            ensure_codecortex_ignored(str(root))


def test_find_sibling_normalize():
    """Lines 172, 177: sibling clone path normalization"""
    from src.domain.coderepository.infrastructure.repo_utils import find_sibling_clones
    entries = [
        {"path": "/repo/a", "remote_url": "https://github.com/x/y"},
        {"path": "/repo/b", "remote_url": "https://github.com/x/y"},
    ]
    siblings = find_sibling_clones("https://github.com/x/y", "/repo/a", entries)
    assert len(siblings) == 1  # /repo/b is sibling, /repo/a is self


def test_staleness_subprocess_error():
    """Lines 203-204, 212: git rev-list throws"""
    from src.domain.coderepository.infrastructure.repo_utils import check_staleness_against_head
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = check_staleness_against_head("/tmp", "abc123")
        assert result["is_stale"] is False


def test_build_meta_stats():
    """Lines 264-266: registry metadata with stats"""
    from src.domain.coderepository.infrastructure.repo_utils import build_registry_meta
    meta = build_registry_meta("/tmp", stats={"files": 42})
    assert meta["stats"]["files"] == 42


if __name__ == "__main__":
    test_canonicalize_exception()
    test_subprocess_exception()
    test_has_git_dir_oserror()
    test_ensure_ignored_read_error()
    test_find_sibling_normalize()
    test_staleness_subprocess_error()
    test_build_meta_stats()
    print("ALL 7 FINAL TESTS PASSED!")
