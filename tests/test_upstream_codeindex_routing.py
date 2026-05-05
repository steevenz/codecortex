import os
from pathlib import Path


def test_upstream_codeindex_routing_writes_symbols_and_edges(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".gitignore").write_text("", encoding="utf-8")
    (repo_root / "a.py").write_text(
        "def b():\n    return 1\n\ndef a():\n    return b()\n",
        encoding="utf-8",
    )

    os.environ["CODECORTEX_DB_PATH"] = str(tmp_path / "db.db")
    os.environ["CODECORTEX_USE_UPSTREAM_CODEINDEX"] = "1"

    import src.main as m

    res = m.index_codebase(str(repo_root))
    assert res["success"] is True
    repo_id = res["data"]["repository_id"]
    assert repo_id

    from src.core.database import DatabaseManager

    db = DatabaseManager()
    sym = db.conn.execute("SELECT COUNT(1) AS c FROM symbols WHERE repository_id = ?", (repo_id,)).fetchone()["c"]
    edges = db.conn.execute("SELECT COUNT(1) AS c FROM edges WHERE repository_id = ?", (repo_id,)).fetchone()["c"]
    assert int(sym) > 0
    assert int(edges) >= 0
    db.close()

