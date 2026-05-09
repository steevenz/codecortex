import os
import asyncio
from pathlib import Path


def test_index_and_reindex_tools_smoke(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".gitignore").write_text("", encoding="utf-8")
    (repo_root / "x.py").write_text("def a():\n    return 1\n", encoding="utf-8")

    db_path = tmp_path / "codecortex.db"
    os.environ["CODECORTEX_DB_PATH"] = str(db_path)

    from src.main import CortexOrchestrator

    orchestrator = CortexOrchestrator(str(db_path))
    
    # 1. Test full analysis (which includes indexing)
    res = asyncio.run(orchestrator.analyze(str(repo_root), dry_run=False))
    assert res["repository_id"]
    repo_id = res["repository_id"]

    # 2. Test incremental sync and indexing
    (repo_root / "x.py").write_text("def a():\n    return 2\n", encoding="utf-8")
    _, changed = asyncio.run(orchestrator.repo_service.sync_repository_with_changes(str(repo_root)))
    assert "x.py" in changed
    
    res2 = asyncio.run(orchestrator.index_service.index_files(repo_id, changed))
    assert res2["files_indexed"] >= 1

    # 3. Test single file indexing
    file_row = orchestrator.db.conn.execute(
        "SELECT id FROM files WHERE repository_id = ? AND name = 'x.py'", 
        (repo_id,)
    ).fetchone()
    assert file_row
    file_id = file_row["id"]
    
    res3 = asyncio.run(orchestrator.index_service.index_file_with_tree_sitter(repo_id, file_id, repo_root / "x.py"))
    assert "error" not in res3

    orchestrator.db.close()

