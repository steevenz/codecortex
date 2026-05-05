import os
from pathlib import Path


def test_analyze_and_validate_codebase_close_db(tmp_path: Path) -> None:
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

    import src.main as m

    res = m.analyze_codebase(str(repo_root))
    assert res["success"] is True

    val = m.validate_codebase(str(repo_root))
    assert "success" in val


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

    import src.main as m
    from src.core.database import DatabaseManager

    res = m.index_codebase(str(repo_root))
    assert res["success"] is True
    repo_id = res["data"]["repository_id"]

    cm = m.get_structured_codemap(repo_id)
    assert cm["success"] is True
    assert cm["data"]["id"] == repo_id

    db = DatabaseManager(str(db_path))
    sym = db.conn.execute(
        "SELECT id FROM symbols WHERE repository_id = ? AND name = 'a' AND symbol_type IN ('function','method')",
        (repo_id,),
    ).fetchone()
    assert sym is not None
    db.close()

    flow = m.trace_execution_flow(sym["id"], max_depth=3)
    assert flow["success"] is True
    assert flow["data"]["flow"]["name"] == "a"


def test_trace_execution_flow_rejects_invalid_inputs() -> None:
    import src.main as m

    bad_uuid = m.trace_execution_flow("not-a-uuid")
    assert bad_uuid["success"] is False
    assert bad_uuid["meta"]["error_code"] == "VAL_003"

    bad_depth = m.trace_execution_flow("00000000-0000-0000-0000-000000000000", max_depth=999)
    assert bad_depth["success"] is False
    assert bad_depth["meta"]["error_code"] == "VAL_004"
