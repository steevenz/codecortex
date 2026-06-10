"""
Tests for idegraph module — domain models, services, storage, and insight generators.
"""
import os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from datetime import datetime
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.services.engram import Engram as EngramService
from src.modules.idegraph.services.resolver import Resolver
from src.modules.idegraph.services.export import Export
from src.modules.idegraph.services.compact import Compact
from src.core.database.sidecortex_schema import ensure_sidecortex_tables


# ══════════════════════════════════════════════════════════════
# DOMAIN MODELS
# ══════════════════════════════════════════════════════════════

def test_engram_creation():
    msg = Message(role="user", content="hello", timestamp="2026-01-01T00:00:00")
    e = Engram(id="e1", source="cursor", source_file="/tmp/test.jsonl", messages=[msg])
    assert e.id == "e1"
    assert e.source == "cursor"
    assert len(e.messages) == 1
    assert e.messages[0].content == "hello"


def test_engram_defaults():
    e = Engram(id="e2", source="test", source_file="/tmp/t.jsonl", messages=[])
    assert e.created_at is not None
    assert e.project_name is None
    assert e.ide_info is None


def test_message_list_content():
    msg = Message(role="user", content=["line1", "line2"])
    assert msg.content == "line1\nline2"


def test_engram_compute_workspace_key():
    key = Engram.compute_workspace_key(
        project_path="/projects/myapp", project_name="myapp",
        workspace_id="ws_1", source_file="/tmp/x.jsonl",
    )
    assert isinstance(key, str)
    assert len(key) == 64


def test_engram_to_dict_roundtrip():
    msg = Message(role="user", content="test", timestamp="2026-01-01T00:00:00")
    e = Engram(id="e3", source="cursor", source_file="/tmp/t.jsonl", messages=[msg],
               title="test engram", model="gpt-4")
    d = e.to_dict()
    assert d["id"] == "e3"
    assert d["title"] == "test engram"
    assert len(d["messages"]) == 1


def test_engram_from_dict():
    data = {
        "id": "e4", "source": "trae", "source_file": "/tmp/t.jsonl",
        "messages": [{"role": "user", "content": "hi"}],
    }
    e = Engram.from_dict(data)
    assert e.id == "e4"
    assert e.source == "trae"
    assert e.messages[0].content == "hi"


def test_ideinfo_to_dict():
    info = IDEInfo(name="cursor", type="vscode-extension", version="1.0")
    d = info.to_dict()
    assert d["name"] == "cursor"
    assert d["type"] == "vscode-extension"


def test_ideinfo_from_dict():
    info = IDEInfo.from_dict({"name": "trae", "type": "desktop"})
    assert info.name == "trae"
    assert info.type == "desktop"


# ══════════════════════════════════════════════════════════════
# SERVICES
# ══════════════════════════════════════════════════════════════

def test_engram_service_dedup():
    svc = EngramService()
    msgs = [Message(role="user", content="a")]
    e1 = Engram(id="dup1", source="cursor", source_file="/tmp/a.jsonl", messages=msgs)
    e2 = Engram(id="dup1", source="cursor", source_file="/tmp/a.jsonl", messages=msgs)
    e3 = Engram(id="unique", source="trae", source_file="/tmp/b.jsonl", messages=msgs)
    result = svc.deduplicate([e1, e2, e3])
    assert len(result) == 2
    assert result[0].id == "dup1"


def test_resolver_group_by_project():
    r = Resolver()
    e1 = Engram(id="a", source="c", source_file="/tmp/projects/myapp/session.jsonl", project_name="myapp", project_path="/tmp/projects/myapp", messages=[])
    e2 = Engram(id="b", source="c", source_file="/tmp/projects/myapp/session.jsonl", project_name="myapp", project_path="/tmp/projects/myapp", messages=[])
    e3 = Engram(id="c", source="t", source_file="/tmp/other/session.jsonl", messages=[])
    groups = r.group_by_project([e1, e2, e3])
    assert len(groups) >= 2


def test_resolver_fallback():
    r = Resolver()
    e = Engram(id="a", source="cursor", source_file="/tmp/unknown.jsonl", messages=[])
    name = r.resolve_project_name(e)
    assert name == "Unknown-Cursor"


def test_export_to_markdown():
    x = Export()
    msg = Message(role="user", content="hello", timestamp="2026-01-01T00:00:00")
    e = Engram(id="m1", source="cursor", source_file="/tmp/t.jsonl", messages=[msg], title="Test")
    md = x.to_markdown(e)
    assert "# Test" in md
    assert "CURSOR" in md
    assert "hello" in md


def test_export_save_json(tmp_path):
    import json
    x = Export()
    msg = Message(role="user", content="test")
    e = Engram(id="j1", source="cursor", source_file="/tmp/t.jsonl", messages=[msg])
    out = tmp_path / "export.json"
    x.save_json([e], out)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 1


def test_compact_fallback():
    c = Compact()
    result = c.compact("### USER\nhello\n### ASSISTANT\ncheck `src/main.py` for bugs", title="test session")
    assert result is not None
    assert "goal" in result
    assert result["schema_version"] == "2.0.0"
    files = result.get("walkthrough", {}).get("files", [])
    assert len(files) > 0
    assert any("src/main.py" in f.get("path", "") for f in files)


# ══════════════════════════════════════════════════════════════
# STORAGE (in-memory SQLite)
# ══════════════════════════════════════════════════════════════

def _make_storage():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_sidecortex_tables(conn)
    from src.modules.idegraph.services.sqlite_storage import Storage
    class MockDB:
        pass
    MockDB.conn = conn
    MockDB._db_path = ":memory:"
    return conn, Storage(db=MockDB())


def test_storage_init_with_db():
    import sqlite3
    from src.modules.idegraph.services.sqlite_storage import Storage
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_sidecortex_tables(conn)

    class MockDB:
        pass
    MockDB.conn = conn
    MockDB._db_path = ":memory:"

    db = MockDB()
    s = Storage(db=db)
    assert s._db is not None


def test_storage_persist_engrams():
    import sqlite3
    from src.modules.idegraph.services.sqlite_storage import Storage
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_sidecortex_tables(conn)

    class MockDB:
        pass
    MockDB.conn = conn
    MockDB._db_path = ":memory:"

    s = Storage(db=MockDB())
    msg = Message(role="user", content="hello")
    e = Engram(id="st1", source="cursor", source_file="/tmp/t.jsonl", messages=[msg],
               project_name="testproj", project_path="/tmp/testproj",
               workspace_id="ws1")
    result = s.persist_engrams([e])
    assert result["conversations_upserted"] >= 1
    assert result["messages_upserted"] >= 1


def test_storage_list_workspaces():
    import sqlite3
    from src.modules.idegraph.services.sqlite_storage import Storage
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_sidecortex_tables(conn)

    class MockDB:
        pass
    MockDB.conn = conn
    MockDB._db_path = ":memory:"

    s = Storage(db=MockDB())
    ws = s.list_workspaces()
    assert isinstance(ws, list)


def test_storage_health_snapshot():
    import sqlite3
    from src.modules.idegraph.services.sqlite_storage import Storage
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_sidecortex_tables(conn)

    class MockDB:
        pass
    MockDB.conn = conn
    MockDB._db_path = ":memory:"

    s = Storage(db=MockDB())
    h = s.health_snapshot()
    assert "db_path" in h
    assert "conversations" in h
    assert "messages" in h


# ══════════════════════════════════════════════════════════════
# INSIGHT GENERATORS
# ══════════════════════════════════════════════════════════════

def test_idegraph_insight_generators():
    from src.core.insight import generate_insight
    cases = [
        ("idegraph_search", {"count": 3}, "Found 3 IDE memories"),
            ("idegraph_get", {"attributes": {"source": "cursor"}}, "Retrieved IDE memory from cursor"),
        ("idegraph_list", {"items": [1, 2]}, "Listed 2 IDE memories"),
            ("idegraph_ingest", {"summary": {"total_engrams": 5}}, "Ingested 5 cross-IDE memories"),
        ("idegraph_health", {"conversations": 10, "status": "healthy"}, "IDE Graph health: healthy"),
        ("idegraph_stats", {"by_ide": [{"engrams": 5}]}, "Ingestion stats: 5 engrams across 1 IDEs"),
        ("idegraph_compact", {"total": 2}, "Compacted 2 conversations"),
        ("idegraph_workspace", {"workspace_key": "abc123"}, "Workspace: abc123"),
        ("idegraph_harvest", {"ides": 3, "configs": 10}, "Harvested 3 IDEs"),
        ("codecortex_idegraph", {"count": 0}, "IDE Graph action"),
    ]
    for key, data, expect_sub in cases:
        ins = generate_insight(key, data)
        assert ins is not None, f"{key} returned None"
        assert expect_sub in ins.summary, f"{key}: expected '{expect_sub}' in '{ins.summary}'"
