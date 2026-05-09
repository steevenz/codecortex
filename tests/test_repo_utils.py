"""
Tests for repository utilities (canonical paths, remote URLs, ignore, siblings).
"""
import sys, os, tempfile, subprocess
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pytest


# ═══════════════════════════════════════════════════════════════════
# MAX FILE SIZE
# ═══════════════════════════════════════════════════════════════════

def test_max_file_size_default():
    from src.domain.coderepository.infrastructure.repo_utils import get_max_file_size_bytes, DEFAULT_MAX_FILE_SIZE_BYTES
    assert get_max_file_size_bytes() == DEFAULT_MAX_FILE_SIZE_BYTES

def test_max_file_size_env():
    os.environ["CODECORTEX_MAX_FILE_SIZE_MB"] = "5"
    from src.domain.coderepository.infrastructure.repo_utils import get_max_file_size_bytes
    assert get_max_file_size_bytes() == 5 * 1024 * 1024
    del os.environ["CODECORTEX_MAX_FILE_SIZE_MB"]

# ═══════════════════════════════════════════════════════════════════
# CANONICAL PATH
# ═══════════════════════════════════════════════════════════════════

def test_canonicalize_path():
    from src.domain.coderepository.infrastructure.repo_utils import canonicalize_path
    with tempfile.TemporaryDirectory() as tmpdir:
        path = canonicalize_path(tmpdir)
        assert path == str(Path(tmpdir).resolve())

# ═══════════════════════════════════════════════════════════════════
# GIT OPERATIONS
# ═══════════════════════════════════════════════════════════════════

def test_get_current_commit():
    from src.domain.coderepository.infrastructure.repo_utils import get_current_commit
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.name", "T"], cwd=root, capture_output=True, timeout=10)
        (root / "f.py").write_text("x=1\n")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", "m"], cwd=root, capture_output=True, timeout=10)
        commit = get_current_commit(tmpdir)
        assert commit is not None
        assert len(commit) == 40

def test_get_remote_url_no_remote():
    from src.domain.coderepository.infrastructure.repo_utils import get_remote_url
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, timeout=10)
        url = get_remote_url(tmpdir)
        assert url is None

def test_get_current_commit_no_git():
    from src.domain.coderepository.infrastructure.repo_utils import get_current_commit
    with tempfile.TemporaryDirectory() as tmpdir:
        assert get_current_commit(tmpdir) is None

# ═══════════════════════════════════════════════════════════════════
# REMOTE URL PARSING
# ═══════════════════════════════════════════════════════════════════

def test_normalize_remote_url():
    from src.domain.coderepository.infrastructure.repo_utils import _normalize_remote_url
    assert "github.com" in _normalize_remote_url("https://GitHub.com/owner/repo")
    assert _normalize_remote_url("https://github.com/owner/repo.git") == _normalize_remote_url("https://github.com/owner/repo")

def test_parse_repo_name():
    from src.domain.coderepository.infrastructure.repo_utils import parse_repo_name_from_url
    assert parse_repo_name_from_url("https://github.com/owner/my-repo") == "my-repo"
    assert parse_repo_name_from_url("git@github.com:owner/my-repo.git") == "my-repo"
    assert parse_repo_name_from_url("") is None
    assert parse_repo_name_from_url(None) is None

def test_get_inferred_repo_name():
    from src.domain.coderepository.infrastructure.repo_utils import get_inferred_repo_name
    with tempfile.TemporaryDirectory() as tmpdir:
        name = get_inferred_repo_name(tmpdir)
        assert name is None  # No remote configured

# ═══════════════════════════════════════════════════════════════════
# CANONICAL REPO ROOT
# ═══════════════════════════════════════════════════════════════════

def test_get_canonical_repo_root():
    from src.domain.coderepository.infrastructure.repo_utils import get_canonical_repo_root, is_git_repo, has_git_dir
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=root, capture_output=True, timeout=10)
        assert is_git_repo(tmpdir) is True
        assert has_git_dir(tmpdir) is True
        canonical = get_canonical_repo_root(tmpdir)
        assert canonical is not None

def test_is_git_repo_false():
    from src.domain.coderepository.infrastructure.repo_utils import is_git_repo
    with tempfile.TemporaryDirectory() as tmpdir:
        assert is_git_repo(tmpdir) is False

def test_has_git_dir_false():
    from src.domain.coderepository.infrastructure.repo_utils import has_git_dir
    with tempfile.TemporaryDirectory() as tmpdir:
        assert has_git_dir(tmpdir) is False

# ═══════════════════════════════════════════════════════════════════
# AUTO-GITIGNORE
# ═══════════════════════════════════════════════════════════════════

def test_ensure_codecortex_ignored():
    from src.domain.coderepository.infrastructure.repo_utils import ensure_codecortex_ignored
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=root, capture_output=True, timeout=10)
        ensure_codecortex_ignored(tmpdir)
        exclude = root / ".git" / "info" / "exclude"
        assert exclude.exists()
        content = exclude.read_text()
        assert ".codecortex/" in content

def test_ensure_codecortex_ignored_no_git():
    from src.domain.coderepository.infrastructure.repo_utils import ensure_codecortex_ignored
    with tempfile.TemporaryDirectory() as tmpdir:
        ensure_codecortex_ignored(tmpdir)  # Should not raise

# ═══════════════════════════════════════════════════════════════════
# IGNORE SERVICE
# ═══════════════════════════════════════════════════════════════════

def test_load_ignore_patterns():
    from src.domain.coderepository.infrastructure.repo_utils import load_ignore_patterns
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".gitignore").write_text("*.log\nbuild/\n")
        patterns = load_ignore_patterns(root)
        assert "*.log" in patterns
        assert "build/" in patterns
        # Built-in patterns
        assert ".git/" in patterns

def test_is_ignored():
    from src.domain.coderepository.infrastructure.repo_utils import is_ignored
    from pathlib import Path
    root = Path("/test")
    assert is_ignored("file.pyc", root, ["*.pyc"]) is True
    assert is_ignored("main.py", root, ["*.pyc"]) is False
    assert is_ignored(".git/config", root, [".git/"]) is True

# ═══════════════════════════════════════════════════════════════════
# SIBLING CLONE DETECTION
# ═══════════════════════════════════════════════════════════════════

def test_find_sibling_clones():
    from src.domain.coderepository.infrastructure.repo_utils import find_sibling_clones
    entries = [
        {"path": "/repo/a", "remote_url": "https://github.com/owner/repo"},
        {"path": "/repo/b", "remote_url": "https://github.com/owner/repo"},
        {"path": "/repo/c", "remote_url": "https://github.com/other/repo"},
    ]
    siblings = find_sibling_clones("https://github.com/owner/repo", "/repo/a", entries)
    assert len(siblings) == 1
    assert siblings[0]["path"] == "/repo/b"

def test_find_sibling_clones_no_remote():
    from src.domain.coderepository.infrastructure.repo_utils import find_sibling_clones
    assert find_sibling_clones("", "/repo/a", []) == []

# ═══════════════════════════════════════════════════════════════════
# STALENESS
# ═══════════════════════════════════════════════════════════════════

def test_check_staleness_no_commit():
    from src.domain.coderepository.infrastructure.repo_utils import check_staleness_against_head
    result = check_staleness_against_head("/tmp", None)
    assert result["is_stale"] is False

# ═══════════════════════════════════════════════════════════════════
# REGISTRY METADATA
# ═══════════════════════════════════════════════════════════════════

def test_build_registry_meta():
    from src.domain.coderepository.infrastructure.repo_utils import build_registry_meta
    with tempfile.TemporaryDirectory() as tmpdir:
        meta = build_registry_meta(tmpdir, stats={"files": 10})
        assert "path" in meta
        assert meta["stats"]["files"] == 10
        meta2 = build_registry_meta(tmpdir)
        assert meta2["stats"] == {}


# ═══════════════════════════════════════════════════════════════════
# EDGE CASES — 100% coverage
# ═══════════════════════════════════════════════════════════════════

def test_normalize_url_ssh():
    _normalize = __import__("src.domain.coderepository.infrastructure.repo_utils", fromlist=["_normalize_remote_url"])._normalize_remote_url
    url = _normalize("git@GITHUB.com:owner/repo.git")
    assert "github.com" in url.lower()

def test_normalize_url_with_port():
    _normalize = __import__("src.domain.coderepository.infrastructure.repo_utils", fromlist=["_normalize_remote_url"])._normalize_remote_url
    url = _normalize("https://GITHUB.com:443/owner/repo")
    assert "github.com" in url

def test_get_current_commit_empty_repo():
    from src.domain.coderepository.infrastructure.repo_utils import get_current_commit
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, timeout=10)
        assert get_current_commit(tmpdir) is None

def test_get_remote_url_no_git():
    from src.domain.coderepository.infrastructure.repo_utils import get_remote_url
    with tempfile.TemporaryDirectory() as tmpdir:
        assert get_remote_url(tmpdir) is None

def test_has_git_dir_file():
    from src.domain.coderepository.infrastructure.repo_utils import has_git_dir
    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "file.txt"
        f.write_text("x")
        assert has_git_dir(str(f)) is False

def test_is_git_repo_non_dir():
    from src.domain.coderepository.infrastructure.repo_utils import is_git_repo
    assert is_git_repo("/nonexistent/path") is False

def test_get_canonical_repo_root_no_git():
    from src.domain.coderepository.infrastructure.repo_utils import get_canonical_repo_root
    with tempfile.TemporaryDirectory() as tmpdir:
        assert get_canonical_repo_root(tmpdir) is None

def test_ensure_ignored_no_git():
    from src.domain.coderepository.infrastructure.repo_utils import ensure_codecortex_ignored
    ensure_codecortex_ignored("/nonexistent-path")  # Should not raise

def test_is_ignored_dotgit():
    from src.domain.coderepository.infrastructure.repo_utils import is_ignored
    from pathlib import Path
    assert is_ignored(".git/config", Path("/"), [".git/"]) is True
    assert is_ignored("main.py", Path("/"), ["*.pyc"]) is False

def test_find_sibling_clones_no_match():
    from src.domain.coderepository.infrastructure.repo_utils import find_sibling_clones
    assert len(find_sibling_clones("https://github.com/a/b", "/tmp/x", [])) == 0

def test_check_staleness_nonexistent():
    from src.domain.coderepository.infrastructure.repo_utils import check_staleness_against_head
    result = check_staleness_against_head("/nonexistent", "abc123")
    assert result["is_stale"] is False

def test_check_staleness_no_commit():
    from src.domain.coderepository.infrastructure.repo_utils import check_staleness_against_head
    result = check_staleness_against_head("/tmp", None)
    assert result["is_stale"] is False

if __name__ == "__main__":
    print("All repo utils tests ready.")
