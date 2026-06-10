import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime, timezone
from pathlib import Path
import pytest
import sqlite3
import uuid

from src.modules.idegraph.services.sqlite_storage import Storage
from src.modules.idegraph.domain.engram import Engram, IDEInfo, Message

@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    db_path = tmp_path / "test_codecortex.db"
    return Storage(db_path=db_path)

def test_storage_init(storage: Storage):
    assert storage.db_path.exists()
    with storage._session() as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [row["name"] for row in tables]
        assert "ides" in table_names
        assert "workspaces" in table_names
        assert "conversations" in table_names

def test_begin_end_sync_run(storage: Storage):
    run_id = storage.begin_sync_run(request_id="req-123")
    assert run_id.startswith("sync_")
    
    with storage._session() as conn:
        row = conn.execute("SELECT status, request_id FROM sync_runs WHERE id=?", (run_id,)).fetchone()
        assert row["status"] == "in_progress"
        assert row["request_id"] == "req-123"

    storage.end_sync_run(run_id, status="completed", summary={"docs": 5})
    
    with storage._session() as conn:
        row = conn.execute("SELECT status, summary_json FROM sync_runs WHERE id=?", (run_id,)).fetchone()
        assert row["status"] == "completed"
        assert "5" in row["summary_json"]

def test_persist_engrams(storage: Storage):
    engram = Engram(
        id="conv-123",
        source="vscode",
        source_file="test.py",
        project_name="MyProject",
        project_path="/home/user/myproject",
        workspace_id="ws-456",
        title="Test Conversation",
        model="gpt-4",
        created_at=datetime.now(timezone.utc),
        messages=[
            Message(role="user", content="Hello", timestamp="2026-06-03T10:00:00Z"),
            Message(role="assistant", content="Hi there", timestamp="2026-06-03T10:00:05Z")
        ],
        ide_info=IDEInfo(name="vscode", type="editor", version="1.80.0"),
        metadata={"tags": ["test"]}
    )

    result = storage.persist_engrams([engram])
    assert result["ides_upserted"] == 1
    assert result["workspaces_upserted"] == 1
    assert result["conversations_upserted"] == 1
    assert result["messages_upserted"] == 2

    # Update the engram with a new message
    engram.messages.append(Message(role="user", content="Follow up", timestamp="2026-06-03T10:01:00Z"))
    result2 = storage.persist_engrams([engram])
    assert result2["ides_upserted"] == 0  # Not changed
    assert result2["workspaces_upserted"] == 0  # Not changed
    assert result2["conversations_upserted"] == 1  # Changed (message count updated)
    assert result2["messages_upserted"] == 1  # Only 1 new message upserted

if __name__ == "__main__":
    import tempfile
    import shutil
    tmp = Path(tempfile.mkdtemp())
    try:
        s = Storage(db_path=tmp / "test_codecortex.db")
        test_storage_init(s)
        test_begin_end_sync_run(s)
        test_persist_engrams(s)
        print("All test_storage tests PASSED")
    finally:
        shutil.rmtree(tmp)
