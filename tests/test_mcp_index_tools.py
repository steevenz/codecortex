import os
from pathlib import Path


def test_index_and_reindex_tools_smoke(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".gitignore").write_text("", encoding="utf-8")
    (repo_root / "x.py").write_text("def a():\n    return 1\n", encoding="utf-8")

    db_path = tmp_path / "codecortex.db"
    os.environ["CODECORTEX_DB_PATH"] = str(db_path)

    import src.main as m

    res = m.index_codebase(str(repo_root))
    assert res["success"] is True
    assert res["data"]["repository_id"]

    res2 = m.reindex_codebase(str(repo_root))
    assert res2["success"] is True
    assert res2["data"]["skipped"] is True

    res3 = m.index_file(str(repo_root), "x.py")
    assert res3["success"] is True

    m.CortexOrchestrator().db.close()
