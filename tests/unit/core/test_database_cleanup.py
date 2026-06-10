"""
Tests for database compact and project cleanup.
"""
import sys, tempfile, json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))


def test_compact():
    from src.core.database import DatabaseManager
    from src.core.database import compact_database
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        result = compact_database(db.conn)
        assert result["status"] == "compact"
        assert "path" in result
        db.close()


def test_cleanup_nonexistent():
    from src.core.database import DatabaseManager
    from src.core.database.cleanup import cleanup_project
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        result = cleanup_project()
        assert "status" in result
        db.close()


def test_cleanup():
    from src.core.database.cleanup import cleanup_project
    result = cleanup_project()
    assert "status" in result


if __name__ == "__main__":
    test_compact()
    test_cleanup_nonexistent()
    test_cleanup()
    print("ALL COMPACT/CLEANUP TESTS PASSED!")
