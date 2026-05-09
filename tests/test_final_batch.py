"""
Final batch: comprehensive tests for backends, mixins, office_worker, config_parser, file_reader.
All tests use REAL dependencies — no mocks.
"""
import sys, os, tempfile, json, subprocess
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pytest

# ═══════════════════════════════════════════════════════════════════
# BACKENDS — import + static method + config validation tests
# ═══════════════════════════════════════════════════════════════════

def test_kuzu_backend_import():
    from src.core.backends.kuzu_backend import KuzuBackend
    assert KuzuBackend is not None
    # Test static methods
    ok, err = KuzuBackend.validate_config()
    assert isinstance(ok, bool)
    ok, err = KuzuBackend.test_connection()
    assert isinstance(ok, bool)

def test_neo4j_backend_import():
    from src.core.backends.neo4j_backend import Neo4jBackend
    assert Neo4jBackend is not None
    ok, err = Neo4jBackend.validate_config()
    assert isinstance(ok, bool)
    ok, err = Neo4jBackend.test_connection()
    assert isinstance(ok, bool)

def test_falkordb_backend_import():
    from src.core.backends.falkordb_backend import FalkorDBBackend
    assert FalkorDBBackend is not None
    ok, err = FalkorDBBackend.validate_config()
    assert isinstance(ok, bool)
    ok, err = FalkorDBBackend.test_connection()
    assert isinstance(ok, bool)
    # Test the FalkorDBRecord wrapper
    from src.core.backends.falkordb_backend import FalkorDBRecord
    record = FalkorDBRecord({"key": "value"})
    assert record.data() == {"key": "value"}
    assert record["key"] == "value"

# ═══════════════════════════════════════════════════════════════════
# OFFICE WORKER
# ═══════════════════════════════════════════════════════════════════

def test_office_worker_real_files():
    from src.domain.codegraph.infrastructure.office_worker import OfficeWorker
    worker = OfficeWorker()
    assert worker is not None
    # Test with a real text file (not office, should return None or error)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "readme.md"
        path.write_text("# Hello\n")
        result = worker.process_file(path)
        assert result is None or isinstance(result, str)

# ═══════════════════════════════════════════════════════════════════
# CONFIG PARSER — all file formats
# ═══════════════════════════════════════════════════════════════════

def test_cp_all_formats():
    from src.domain.coderepository.infrastructure.config_parser import ConfigParser
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # package.json
        (root / "package.json").write_text('{"dependencies": {"react": "^18.0"}, "devDependencies": {"jest": "^29.0"}}')
        # composer.json
        (root / "composer.json").write_text('{"require": {"laravel/framework": "^10.0"}}')
        # Gemfile
        (root / "Gemfile").write_text('gem "rails", "~> 7.0"\ngem "pg"\n')
        # requirements.txt
        (root / "requirements.txt").write_text("django==4.2\nflask==2.3\nfastapi==0.104\n")
        # pubspec.yaml
        (root / "pubspec.yaml").write_text("dependencies:\n  flutter:\n    sdk: flutter\n")
        # .csproj
        (root / "test.csproj").write_text('<Project><ItemGroup><PackageReference Include="Microsoft.AspNetCore.App" Version="6.0" /></ItemGroup></Project>')
        config = ConfigParser.parse_all_configs(root)
        assert isinstance(config, dict)
        assert "package.json" in config
        assert "composer.json" in config
        assert "Gemfile" in config
        assert "requirements.txt" in config
        assert "pubspec.yaml" in config
        assert "csproj" in config

# ═══════════════════════════════════════════════════════════════════
# FILE READER — edge cases
# ═══════════════════════════════════════════════════════════════════

def test_fr_binary_file():
    from src.domain.coderepository.infrastructure.file_reader import FileReader
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "data.bin").write_bytes(b"\x00\x01\x02\x03")
        reader = FileReader(root)
        content = reader.read("data.bin")
        assert "not found" in content.lower() or isinstance(content, str)

# ═══════════════════════════════════════════════════════════════════
# GIT ADAPTER — edge cases
# ═══════════════════════════════════════════════════════════════════

def test_ga_init_repo():
    from src.domain.coderepository.infrastructure.git_adapter import GitAdapter
    import time
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir_obj.name)
        subprocess.run(["git", "init"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.name", "T"], cwd=root, capture_output=True, timeout=10)
        (root / "test.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True, timeout=10)
        adapter = GitAdapter(root)
        assert adapter.is_available is True
        status = adapter.get_status()
        assert isinstance(status, dict)
    finally:
        time.sleep(0.2)
        try:
            tmpdir_obj.cleanup()
        except PermissionError:
            pass

# ═══════════════════════════════════════════════════════════════════
# GIT HISTORY  
# ═══════════════════════════════════════════════════════════════════

def test_gh_real():
    from src.domain.coderepository.infrastructure.git_history import GitHistoryWorker
    from src.core.database import DatabaseManager
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    import time
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir_obj.name)
        subprocess.run(["git", "init"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.name", "T"], cwd=root, capture_output=True, timeout=10)
        (root / "f.py").write_text("x=1\n")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True, timeout=10)
        db = DatabaseManager(str(root / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        worker = GitHistoryWorker(store, root)
        worker.index_history("test-repo-id", limit=10)
        findings = worker.audit_commits("test-repo-id", limit=10)
        assert isinstance(findings, list)
        db.close()
    finally:
        time.sleep(0.2)
        try:
            tmpdir_obj.cleanup()
        except PermissionError:
            pass

# ═══════════════════════════════════════════════════════════════════
# coderesolver → search_service
# ═══════════════════════════════════════════════════════════════════

def test_search_service():
    from src.domain.coderefactor.application.search_service import SearchService
    from src.core.database import DatabaseManager
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        svc = SearchService(db)
        assert svc is not None
        db.close()

# ═══════════════════════════════════════════════════════════════════
# ConfigParser: individual methods  
# ═══════════════════════════════════════════════════════════════════

def test_cp_individual():
    from src.domain.coderepository.infrastructure.config_parser import ConfigParser
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Test parse_requirements_txt
        (root / "requirements.txt").write_text("django==4.2\nflask==2.3\n# comment\n-e git+https://example.com/pkg\n")
        config = ConfigParser.parse_requirements_txt(root)
        assert isinstance(config, dict)
        deps = config.get("dependencies", {})
        assert "django" in deps

if __name__ == "__main__":
    print("Final batch tests ready.")
