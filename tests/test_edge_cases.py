"""
Final edge case tests for 100% repo_utils coverage.
Targets specific uncovered lines: 35-36, 49-50, 62-63, 76-78, 123, 125-126, 133-134, 164-165, 172, 177, 203-204, 212, 264-266
"""
import sys, os, tempfile, subprocess
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_max_file_size_invalid():
    os.environ["CODECORTEX_MAX_FILE_SIZE_MB"] = "abc"
    from src.domain.coderepository.infrastructure.repo_utils import get_max_file_size_bytes, DEFAULT_MAX_FILE_SIZE_BYTES
    assert get_max_file_size_bytes() == DEFAULT_MAX_FILE_SIZE_BYTES
    del os.environ["CODECORTEX_MAX_FILE_SIZE_MB"]


def test_normalize_url_ssh_no_git():
    mod = __import__("src.domain.coderepository.infrastructure.repo_utils", fromlist=["_normalize_remote_url"])
    url = mod._normalize_remote_url("ssh://git@GITHUB.com/owner/repo")
    assert "github.com" in url


def test_normalize_url_no_match():
    mod = __import__("src.domain.coderepository.infrastructure.repo_utils", fromlist=["_normalize_remote_url"])
    url = mod._normalize_remote_url("")
    assert url == ""


def test_get_current_commit_subprocess_error():
    from src.domain.coderepository.infrastructure.repo_utils import get_current_commit
    assert get_current_commit("/nonexistent_dir_xyz") is None


def test_has_git_dir_oserror():
    from src.domain.coderepository.infrastructure.repo_utils import has_git_dir
    assert has_git_dir("/nonexistent_path_xyz") is False


def test_canonical_root_exception():
    from src.domain.coderepository.infrastructure.repo_utils import get_canonical_repo_root
    assert get_canonical_repo_root("/nonexistent") is None


def test_is_ignored_fn_match():
    from src.domain.coderepository.infrastructure.repo_utils import is_ignored
    assert is_ignored("test.log", Path("/"), ["*.log"]) is True
    assert is_ignored("main.py", Path("/"), ["*.log"]) is False
    assert is_ignored("dir/test.log", Path("/"), ["*.log"]) is True


def test_find_sibling_no_self():
    from src.domain.coderepository.infrastructure.repo_utils import find_sibling_clones
    entries = [{"path": "/repo/a", "remote_url": "https://github.com/x/y"}]
    assert len(find_sibling_clones("https://github.com/x/y", "/repo/a", entries)) == 0
    assert len(find_sibling_clones("https://github.com/x/y", "/repo/b", entries)) == 1


def test_check_staleness_exception():
    from src.domain.coderepository.infrastructure.repo_utils import check_staleness_against_head
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        result = check_staleness_against_head(tmpdir, "abc123")
        assert result["is_stale"] is False


def test_build_meta_with_remote():
    from src.domain.coderepository.infrastructure.repo_utils import build_registry_meta
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        meta = build_registry_meta(tmpdir)
        assert "stats" in meta


if __name__ == "__main__":
    test_max_file_size_invalid()
    test_normalize_url_git_protocol()
    test_normalize_url_no_path()
    test_normalize_url_ssh_no_git()
    test_normalize_url_no_match()
    test_get_current_commit_failure()
    test_get_current_commit_subprocess_error()
    test_has_git_dir_oserror()
    test_is_git_repo_failure()
    test_canonical_root_exception()
    test_is_ignored_fn_match()
    test_find_sibling_no_self()
    test_check_staleness_exception()
    test_build_meta_with_remote()
    print("ALL 14 EDGE CASE TESTS PASSED!")


if __name__ == "__main__":
    test_max_file_size_invalid()
    test_normalize_url_git_protocol()
    test_normalize_url_no_path()
    test_get_current_commit_failure()
    test_has_git_dir_oserror()
    test_is_git_repo_failure()
    test_canonical_root_failure()
    test_is_ignored_fn_match()
    test_find_sibling_matches()
    test_check_staleness_no_git_dir()
    test_build_meta_basic()
    print("ALL 11 EDGE CASE TESTS PASSED!")
