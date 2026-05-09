import os
import asyncio
from pathlib import Path


def test_repo_analyze_dry_run_close_db(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".gitignore").write_text("", encoding="utf-8")
    (repo_root / "a.py").write_text(
        "def a():\n"
        "    b()\n"
        "\n"
        "def b():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "codecortex.db"
    os.environ["CODECORTEX_DB_PATH"] = str(db_path)
    os.environ["CODECORTEX_GRAPH_BACKEND"] = "none"

    from src.main import CortexOrchestrator

    orch = CortexOrchestrator(str(db_path))

    async def _run():
        res = await orch.analyze(str(repo_root), dry_run=False)
        return res

    res = asyncio.run(_run())
    assert "repository_id" in res
    assert "analysis" in res
    orch.db.close()


def test_validate_path_accepts_existing_directory(tmp_path: Path) -> None:
    import src.main as m

    ok, msg = m.validate_path(str(tmp_path))
    assert ok is True
    assert msg == ""


def test_codemap_and_trace_execution_flow(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".gitignore").write_text("", encoding="utf-8")
    (repo_root / "a.py").write_text(
        "def b():\n"
        "    return 1\n"
        "\n"
        "def a():\n"
        "    return b()\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "codecortex.db"
    os.environ["CODECORTEX_DB_PATH"] = str(db_path)
    os.environ["CODECORTEX_GRAPH_BACKEND"] = "none"

    from src.main import CortexOrchestrator

    orch = CortexOrchestrator(str(db_path))

    async def _run():
        repo_id = await orch.repo_service.sync_repository(str(repo_root))
        await orch.index_service.index_repository(repo_id)

        dirs = orch.db.conn.execute(
            "SELECT id, relative_path FROM directories WHERE repository_id = ? ORDER BY relative_path",
            (repo_id,)
        ).fetchall()
        assert dirs is not None

        sym = orch.db.conn.execute(
            "SELECT id FROM symbols WHERE repository_id = ? AND name = 'a' AND symbol_type IN ('function','method')",
            (repo_id,),
        ).fetchone()
        assert sym is not None

        flow = await orch.graph_service.trace_execution_flow(sym["id"], max_depth=3)
        assert flow is not None
        assert "flow" in flow
        assert flow["flow"]["name"] == "a"

        return repo_id

    asyncio.run(_run())
    orch.db.close()


def test_trace_execution_flow_rejects_invalid_inputs() -> None:
    import src.main as m

    bad_uuid, _ = m.validate_uuid("not-a-uuid")
    assert bad_uuid is False

    bad_depth, _ = m.validate_max_depth(999)
    assert bad_depth is False
