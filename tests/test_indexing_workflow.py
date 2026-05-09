import os
import json
from pathlib import Path


def _make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    (root / ".gitignore").write_text("", encoding="utf-8")
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


def test_native_indexing_builds_calls_edges(tmp_path: Path) -> None:
    os.environ["CODECORTEX_USE_UPSTREAM_CODEINDEX"] = "0"
    os.environ["CODECORTEX_GRAPH_BACKEND"] = "none"

    repo_root = _make_repo(
        tmp_path,
        {
            "a.py": (
                "def b():\n"
                "    return 1\n"
                "\n"
                "def a():\n"
                "    return b()\n"
            )
        },
    )

    from src.core.database import DatabaseManager
    from src.domain.coderepository.application.service import CodeRepositoryService
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.codeindex.application.service import CodeIndexService
    import asyncio

    db = DatabaseManager(str(tmp_path / "codecortex.db"))
    store = SQLiteCodeRepositoryStore(db)
    repo_service = CodeRepositoryService(store)
    repo_id = asyncio.run(repo_service.sync_repository(str(repo_root)))

    index_service = CodeIndexService(db, codegraph_service=None)
    asyncio.run(index_service.index_repository(repo_id))

    a_row = db.conn.execute(
        "SELECT id FROM symbols WHERE repository_id = ? AND name = 'a' AND symbol_type IN ('function','method')",
        (repo_id,),
    ).fetchone()
    b_row = db.conn.execute(
        "SELECT id FROM symbols WHERE repository_id = ? AND name = 'b' AND symbol_type IN ('function','method')",
        (repo_id,),
    ).fetchone()
    assert a_row is not None
    assert b_row is not None

    edge = db.conn.execute(
        "SELECT id FROM edges WHERE repository_id = ? AND source_id = ? AND target_id = ? AND relation_type = 'CALLS'",
        (repo_id, a_row["id"], b_row["id"]),
    ).fetchone()
    assert edge is not None

    db.close()


def test_incremental_index_files_updates_manifest(tmp_path: Path) -> None:
    os.environ["CODECORTEX_USE_UPSTREAM_CODEINDEX"] = "0"
    os.environ["CODECORTEX_GRAPH_BACKEND"] = "none"

    repo_root = _make_repo(tmp_path, {"x.py": "def x():\n    return 1\n"})

    from src.core.database import DatabaseManager
    from src.domain.coderepository.application.service import CodeRepositoryService
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.codeindex.application.service import CodeIndexService
    import asyncio

    db = DatabaseManager(str(tmp_path / "codecortex.db"))
    store = SQLiteCodeRepositoryStore(db)
    repo_service = CodeRepositoryService(store)
    repo_id = asyncio.run(repo_service.sync_repository(str(repo_root)))

    index_service = CodeIndexService(db, codegraph_service=None)
    asyncio.run(index_service.index_repository(repo_id))

    (repo_root / "x.py").write_text("def x():\n    return 2\n", encoding="utf-8")
    _, changed = asyncio.run(repo_service.sync_repository_with_changes(str(repo_root)))
    assert "x.py" in changed

    stats = asyncio.run(index_service.index_files(repo_id, changed))
    assert stats["files_indexed"] >= 1

    row = db.conn.execute(
        "SELECT last_hash, last_size_bytes, last_mtime FROM manifest_entries WHERE repository_id = ? AND file_path = ?",
        (repo_id, "x.py"),
    ).fetchone()
    assert row is not None
    assert row["last_hash"]
    assert row["last_size_bytes"] is not None
    assert row["last_mtime"] is not None

    db.close()


def test_python_builtin_fallback_when_parser_import_fails(tmp_path: Path) -> None:
    os.environ["CODECORTEX_USE_UPSTREAM_CODEINDEX"] = "0"
    os.environ["CODECORTEX_GRAPH_BACKEND"] = "none"

    repo_root = _make_repo(tmp_path, {"f.py": "def a():\n    return 1\n"})

    from src.core.database import DatabaseManager
    from src.domain.coderepository.application.service import CodeRepositoryService
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.codeindex.application.service import CodeIndexService
    import asyncio

    db = DatabaseManager(str(tmp_path / "codecortex.db"))
    store = SQLiteCodeRepositoryStore(db)
    repo_service = CodeRepositoryService(store)
    repo_id = asyncio.run(repo_service.sync_repository(str(repo_root)))

    index_service = CodeIndexService(db, codegraph_service=None)
    parser = index_service._get_parser("python")

    def _raise_import_error(*args, **kwargs):
        raise ImportError("forced")

    parser.parse = _raise_import_error  # type: ignore[attr-defined]

    asyncio.run(index_service.index_repository(repo_id))

    sym = db.conn.execute(
        "SELECT id, metadata FROM symbols WHERE repository_id = ? AND name = 'a'",
        (repo_id,),
    ).fetchone()
    assert sym is not None
    meta = json.loads(sym["metadata"]) if sym["metadata"] else {}
    assert meta.get("language") in {"python", "unknown"}

    db.close()


def test_converters_build_code_refs_and_file_symbol() -> None:
    from src.domain.codeindex.core.converters import parsed_data_to_raw_symbols

    parsed = {
        "lang": "python",
        "variables": [{"name": "X"}],
        "imports": [{"name": "os"}],
        "function_calls": [{"name": "b"}],
        "classes": [{"name": "C", "line_number": 1, "end_line": 3, "bases": ["Base"]}],
        "functions": [
            {
                "name": "a",
                "line_number": 10,
                "end_line": 12,
                "args": ["x"],
                "function_calls": [{"name": "b", "line_number": 11}],
            }
        ],
    }

    raw = parsed_data_to_raw_symbols("x.py", parsed)
    assert raw[0].symbol_type == "file"
    assert raw[0].imports
    assert any(s.symbol_type == "class" and s.name == "C" for s in raw)
    assert any(s.symbol_type in {"function", "method"} and s.name == "a" for s in raw)
    assert any(s.code_ref.startswith("x.py:") for s in raw if s.code_ref)


def test_persist_raw_symbols_resolves_parent_ids(tmp_path: Path) -> None:
    from src.core.database import DatabaseManager
    from src.domain.coderepository.application.service import CodeRepositoryService
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.codeindex.application.service import CodeIndexService
    from src.domain.codeindex.infrastructure.strategies.base import RawSymbol
    import asyncio

    repo_root = _make_repo(tmp_path, {"p.py": "class C:\n    def m(self):\n        return 1\n"})
    db = DatabaseManager(str(tmp_path / "codecortex.db"))
    store = SQLiteCodeRepositoryStore(db)
    repo_service = CodeRepositoryService(store)
    repo_id = asyncio.run(repo_service.sync_repository(str(repo_root)))

    row = db.conn.execute(
        "SELECT f.id AS file_id, d.relative_path AS dir_path, f.name AS name FROM files f JOIN directories d ON d.id = f.directory_id WHERE f.repository_id = ?",
        (repo_id,),
    ).fetchone()
    assert row is not None
    file_rel = f"{(row['dir_path'] or '').replace(chr(92), '/')}".strip('/')
    file_rel_path = f"{file_rel}/{row['name']}" if file_rel else row["name"]

    parent_ref = f"{file_rel_path}:class:C@1"
    child_ref = f"{file_rel_path}:method:C.m@2"

    raw_symbols = [
        RawSymbol(name="C", symbol_type="class", start_line=1, end_line=3, code_ref=parent_ref),
        RawSymbol(name="m", symbol_type="method", start_line=2, end_line=3, code_ref=child_ref, parent_id=parent_ref),
    ]

    idx = CodeIndexService(db, codegraph_service=None)
    written = asyncio.run(idx._persist_raw_symbols(repo_id, row["file_id"], raw_symbols))
    assert written == 2

    child = db.conn.execute("SELECT parent_id FROM symbols WHERE code = ?", (child_ref,)).fetchone()
    assert child is not None
    assert child["parent_id"] is not None

    db.close()


def test_index_file_with_tree_sitter_rejects_unsupported_ext_and_too_large(tmp_path: Path) -> None:
    from src.core.database import DatabaseManager
    from src.domain.coderepository.application.service import CodeRepositoryService
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.codeindex.application.service import CodeIndexService
    import asyncio

    repo_root = _make_repo(tmp_path, {"x.unknown": "hello\n", "big.py": "x" * 10})
    db = DatabaseManager(str(tmp_path / "codecortex.db"))
    store = SQLiteCodeRepositoryStore(db)
    repo_service = CodeRepositoryService(store)
    repo_id = asyncio.run(repo_service.sync_repository(str(repo_root)))

    file_unknown = db.conn.execute(
        "SELECT f.id AS file_id, d.relative_path AS dir_path, f.name AS name FROM files f JOIN directories d ON d.id = f.directory_id WHERE f.repository_id = ? AND f.name = 'x.unknown'",
        (repo_id,),
    ).fetchone()
    assert file_unknown is not None
    p_unknown = repo_root / "x.unknown"

    idx = CodeIndexService(db, codegraph_service=None)
    parsed = asyncio.run(idx.index_file_with_tree_sitter(repo_id, file_unknown["file_id"], p_unknown))
    assert "error" in parsed

    file_big = db.conn.execute(
        "SELECT f.id AS file_id FROM files f WHERE f.repository_id = ? AND f.name = 'big.py'",
        (repo_id,),
    ).fetchone()
    assert file_big is not None
    p_big = repo_root / "big.py"
    idx.MAX_FILE_SIZE_BYTES = 1
    parsed2 = asyncio.run(idx.index_file_with_tree_sitter(repo_id, file_big["file_id"], p_big))
    assert parsed2.get("error") == "file_too_large"

    db.close()
