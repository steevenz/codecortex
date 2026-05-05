import os
import time
from pathlib import Path


def test_repository_sync_with_changes_detects_delta(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".gitignore").write_text("", encoding="utf-8")
    target = repo_root / "a.txt"
    target.write_text("hello", encoding="utf-8")

    db_path = tmp_path / "db.db"
    os.environ["CODECORTEX_DB_PATH"] = str(db_path)

    from src.core.database import DatabaseManager
    from src.domain.repository.service import RepositoryService

    db = DatabaseManager()
    repo = RepositoryService(db)

    repo_id, changed = repo.sync_repository_with_changes(str(repo_root))
    assert repo_id
    assert "a.txt" in changed

    repo_id2, changed2 = repo.sync_repository_with_changes(str(repo_root))
    assert repo_id2 == repo_id
    assert changed2 == []

    time.sleep(1.1)
    target.write_text("hello2", encoding="utf-8")

    repo_id3, changed3 = repo.sync_repository_with_changes(str(repo_root))
    assert repo_id3 == repo_id
    assert "a.txt" in changed3
    db.close()
