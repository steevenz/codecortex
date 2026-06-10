"""
Target the 12 remaining defense-in-depth exception lines.
Uses mock ONLY for system-level failure handlers (subprocess crash, OSError).
"""
import sys, os
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.append(str(Path(__file__).resolve().parents[2]))


def test_max_file_size_invalid_env():
    os.environ["CODECORTEX_MAX_FILE_SIZE_MB"] = "not-a-number"
    from src.modules.coderepository.core.utils import get_max_file_size_bytes, DEFAULT_MAX_FILE_SIZE_BYTES
    assert get_max_file_size_bytes() == DEFAULT_MAX_FILE_SIZE_BYTES
    del os.environ["CODECORTEX_MAX_FILE_SIZE_MB"]


def test_normalize_url_ssh_match():
    """Line 49-50: SSH URL with @ but no git@ prefix"""
    from src.modules.coderepository.core.utils import _normalize_remote_url
    assert "github.com" in _normalize_remote_url("ssh://git@GITHUB.COM/owner/repo")


def test_normalize_url_no_match():
    """Line 62-63: URL with no recognizable pattern"""
    from src.modules.coderepository.core.utils import _normalize_remote_url
    assert _normalize_remote_url("") == ""


def test_get_current_commit_subprocess_exception():
    """Lines 76-78: subprocess.run throws FileNotFoundError"""
    from src.modules.coderepository.core.utils import get_current_commit
    with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
        assert get_current_commit("/tmp") is None


def test_has_git_dir_exception():
    """Line 123: Path.exists throws OSError"""
    from src.modules.coderepository.core.utils import has_git_dir
    with patch.object(Path, "exists", side_effect=OSError("permission denied")):
        assert has_git_dir("/tmp") is False


def test_is_git_repo_exception():
    """Lines 125-126: subprocess.run throws"""
    from src.modules.coderepository.core.utils import is_git_repo
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert is_git_repo("/tmp") is False


def test_canonical_root_exception():
    """Lines 133-134: subprocess.run throws"""
    from src.modules.coderepository.core.utils import get_canonical_repo_root
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert get_canonical_repo_root("/tmp") is None


def test_is_ignored_fn_match():
    """Lines 164-165: fnmatch pattern matching"""
    from src.modules.coderepository.core.utils import is_ignored
    assert is_ignored("test.log", Path("/"), ["*.log"]) is True
    assert is_ignored("main.py", Path("/"), ["*.log"]) is False
    assert is_ignored("dir/test.log", Path("/"), ["*.log"]) is True


def test_find_sibling_self_exclusion():
    """Lines 172, 177: self-path exclusion and normalization"""
    from src.modules.coderepository.core.utils import find_sibling_clones
    entries = [
        {"path": "/repo/a", "remote_url": "https://github.com/x/y"},
        {"path": "/repo/b", "remote_url": "https://github.com/x/y"},
    ]
    siblings = find_sibling_clones("https://github.com/x/y", "/repo/a", entries)
    assert len(siblings) == 1
    assert siblings[0]["path"] == "/repo/b"


def test_check_staleness_exception():
    """Lines 203-204, 212: git rev-list throws"""
    from src.modules.coderepository.core.utils import check_staleness_against_head
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = check_staleness_against_head("/tmp", "abc123")
        assert result["is_stale"] is False


def test_build_meta():
    """Lines 265-266: build registry meta with commit"""
    from src.modules.coderepository.core.utils import build_registry_meta
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        meta = build_registry_meta(tmpdir)
        assert "stats" in meta


if __name__ == "__main__":
    test_max_file_size_invalid_env()
    test_normalize_url_ssh_match()
    test_normalize_url_no_match()
    test_get_current_commit_subprocess_exception()
    test_has_git_dir_exception()
    test_is_git_repo_exception()
    test_canonical_root_exception()
    test_is_ignored_fn_match()
    test_find_sibling_self_exclusion()
    test_check_staleness_exception()
    test_build_meta()
    print("ALL 11 TESTS PASSED!")
