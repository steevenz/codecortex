"""
Tests for database takeout/import, compact, cleanup CLI.
"""
import sys, os, tempfile, subprocess, json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
CLI = str(Path(__file__).resolve().parents[1] / "scripts" / "cli.py")


def test_takeout_import():
    from src.core.database import DatabaseManager
    from src.core.takeout import takeout_project, import_project
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    import tempfile
    tmpdir = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir.name)
        db = DatabaseManager(str(root / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        repo_id = store.upsert_repository("takeout-test", str(root))
        result = takeout_project(db.conn, repo_id, str(root))
        assert result["action"] == "takeout"
        assert result["total_records"] > 0
        
        # Re-import into fresh DB
        db2 = DatabaseManager(str(root / "test2.db"))
        result2 = import_project(db2.conn, result["output_path"])
        assert result2["action"] == "import"
        assert result2["total_records"] > 0
        db.close()
        db2.close()
    finally:
        try: tmpdir.cleanup()
        except: pass


def test_cli_compact():
    result = subprocess.run([sys.executable, CLI, "--compact", "nonexistent"],
                           capture_output=True, text=True, timeout=15)
    assert result.returncode == 0


def test_cli_cleanup_nonexistent():
    result = subprocess.run([sys.executable, CLI, "--cleanup", "nonexistent"],
                           capture_output=True, text=True, timeout=15)
    assert result.returncode == 0


def test_cli_help_has_new():
    result = subprocess.run([sys.executable, CLI, "--help"],
                           capture_output=True, text=True, timeout=15)
    assert "--compact" in result.stdout
    assert "--cleanup" in result.stdout
    assert "--takeout" in result.stdout
    assert "--import-dump" in result.stdout


if __name__ == "__main__":
    test_takeout_import()
    test_cli_compact()
    test_cli_cleanup_nonexistent()
    test_cli_help_has_new()
    print("ALL TAKEOUT/IMPORT TESTS PASSED!")
