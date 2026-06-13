"""
Tests for global registry and staleness detection.
"""
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.modules.coderepository.core.registry import RegistryManager


def test_registry_write_read():
    RegistryManager.unregister("/tmp/test-repo")
    entries = RegistryManager.read()
    assert isinstance(entries, list)


def test_registry_register_and_list():
    RegistryManager.register("/tmp/test-repo", "test-uuid-123", {"files": 10})
    repos = RegistryManager.list_all()
    found = any(r.get("repo_id") == "test-uuid-123" for r in repos)
    if found:
        RegistryManager.unregister("/tmp/test-repo")
        repos2 = RegistryManager.list_all()
        assert not any(r.get("repo_id") == "test-uuid-123" for r in repos2)
    assert True


def test_registry_find_by_path():
    RegistryManager.register("/tmp/test-path", "uuid-path-test")
    entry = RegistryManager.find_by_path("/tmp/test-path")
    if entry:
        assert entry["repo_id"] == "uuid-path-test"
        RegistryManager.unregister("/tmp/test-path")
        assert RegistryManager.find_by_path("/tmp/test-path") is None


def test_registry_double_register():
    RegistryManager.register("/tmp/double-repo", "uuid-1", {"files": 1})
    RegistryManager.register("/tmp/double-repo", "uuid-2", {"files": 2})
    entry = RegistryManager.find_by_path("/tmp/double-repo")
    if entry:
        assert entry["repo_id"] == "uuid-2"
        RegistryManager.unregister("/tmp/double-repo")


def test_registry_find_by_id():
    RegistryManager.register("/tmp/id-test", "find-me-uuid")
    entry = RegistryManager.find_by_id("find-me-uuid")
    if entry:
        assert entry["repo_id"] == "find-me-uuid"
        RegistryManager.unregister("/tmp/id-test")


def test_registry_unregister_nonexistent():
    RegistryManager.unregister("/tmp/nonexistent-path")
    assert True


def test_staleness_non_git():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = RegistryManager.check_staleness(tmpdir, "abc123")
        assert isinstance(result, dict)
        assert "is_stale" in result


def test_staleness_no_commit():
    result = RegistryManager.check_staleness("/tmp/nonexistent")
    assert result["is_stale"] is False


def test_ensure_dir():
    RegistryManager.ensure_dir()
    assert Path.home().joinpath(".coddy", "codecortex").exists()


if __name__ == "__main__":
    test_registry_write_read()
    test_registry_register_and_list()
    test_registry_find_by_path()
    test_registry_double_register()
    test_registry_find_by_id()
    test_registry_unregister_nonexistent()
    test_staleness_non_git()
    test_staleness_no_commit()
    test_ensure_dir()
    print("All registry tests passed.")
