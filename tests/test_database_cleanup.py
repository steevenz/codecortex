"""
Tests for database compact and project cleanup.
"""
import sys, tempfile, json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_compact():
    from src.core.database import DatabaseManager
    from src.core.database_cleanup import compact_database
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        result = compact_database(db.conn)
        assert result["action"] == "compact"
        assert "space_reclaimed" in result
        db.close()


def test_cleanup_nonexistent():
    from src.core.database import DatabaseManager
    from src.core.database_cleanup import cleanup_project
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        result = cleanup_project(db.conn, "nonexistent-uuid")
        assert "error" in result
        db.close()


def test_cleanup():
    from src.core.database import DatabaseManager
    from src.core.database_cleanup import cleanup_project
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        repo_id = store.upsert_repository("test-repo", str(tmpdir))
        result = cleanup_project(db.conn, repo_id)
        assert result["action"] == "cleanup"
        assert result["repo_id"] == repo_id
        db.close()


if __name__ == "__main__":
    test_compact()
    test_cleanup_nonexistent()
    test_cleanup()
    print("ALL COMPACT/CLEANUP TESTS PASSED!")
