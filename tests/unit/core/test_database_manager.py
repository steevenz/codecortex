import os
from pathlib import Path
import pytest


def test_database_manager_uses_env_path(tmp_path: Path) -> None:
    db_path = tmp_path / "codecortex-test.db"
    os.environ["CODECORTEX_DB_PATH"] = str(db_path)

    from src.core.database import DatabaseManager

    DatabaseManager._instance = None
    db = DatabaseManager()
    assert db._db_path.resolve() == db_path.resolve()
    db.close()
    DatabaseManager._instance = None
