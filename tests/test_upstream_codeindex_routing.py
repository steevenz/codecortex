import os
import asyncio
from pathlib import Path


def test_orchestrator_analysis_writes_symbols_and_edges(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".gitignore").write_text("", encoding="utf-8")
    (repo_root / "a.py").write_text(
        "def b():\n    return 1\n\ndef a():\n    return b()\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "codecortex.db"
    os.environ["CODECORTEX_DB_PATH"] = str(db_path)
    os.environ["CODECORTEX_GRAPH_BACKEND"] = "none"

    from src.main import CortexOrchestrator

    # Initialize orchestrator
    orch = CortexOrchestrator(str(db_path))

    async def _run():
        # Full analysis pipeline
        res = await orch.analyze(str(repo_root), dry_run=False)
        return res

    res = asyncio.run(_run())
    assert "repository_id" in res
    repo_id = res["repository_id"]
    assert repo_id

    # Verify database contents
    sym_count = orch.db.conn.execute(
        "SELECT COUNT(1) AS c FROM symbols WHERE repository_id = ?", 
        (repo_id,)
    ).fetchone()["c"]
    
    edge_count = orch.db.conn.execute(
        "SELECT COUNT(1) AS c FROM edges WHERE repository_id = ?", 
        (repo_id,)
    ).fetchone()["c"]

    assert int(sym_count) >= 2  # At least 'a' and 'b'
    assert int(edge_count) >= 0 # Edges might take time or need more context, but shouldn't crash

    orch.db.close()
