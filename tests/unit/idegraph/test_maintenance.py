import os
import sys
sys.path.insert(0, os.path.abspath('.'))

import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.services.compact import Compact
from src.modules.idegraph.services.export import Export

def test_compact_fallback(tmp_path: Path):
    c = Compact()
    
    conversation_text = """
    ### USER
    Fix the bug
    ### ASSISTANT
    I'll change the code. Let me test this.
    I decided to use an array instead of a list.
    Here is the `main.py` fix.
    """
    
    res = c._fallback(conversation_text, "Test Session")
    
    assert res["goal"] == "Test Session"
    assert "decisions" in res["walkthrough"]
    assert len(res["walkthrough"]["decisions"]) > 0
    assert len(res["walkthrough"]["files"]) > 0

def test_compact_parse_output():
    c = Compact()
    raw_ollama_output = """
    Goal: Refactor auth logic
    Thinking: Need to improve security
    Action: Used PBKDF2
    Files:
    - auth.py
    Result: completed
    """
    
    parsed = c._parse_output(raw_ollama_output)
    
    assert parsed["goal"] == "Refactor auth logic"
    assert "auth.py" in str(parsed["files"])
    assert parsed["result"] == "completed"

def test_export_markdown():
    e = Export()
    engram = Engram(
        id="test-123",
        source="vscode",
        source_file="test.json",
        project_name="TestProject",
        title="Test Export",
        created_at=datetime.now(timezone.utc),
        messages=[Message(role="user", content="Hello", timestamp="2026-06-03T10:00:00Z")],
        ide_info=IDEInfo(name="vscode", type="editor")
    )
    
    md = e.to_markdown(engram)
    
    assert "# Test Export" in md
    assert "vscode" in md
    assert "Hello" in md

def test_export_json(tmp_path: Path):
    e = Export()
    engram = Engram(
        id="test-123",
        source="vscode",
        source_file="test.json",
        project_name="TestProject",
        created_at=datetime.now(timezone.utc),
        messages=[Message(role="user", content="Hello")]
    )
    
    out_file = tmp_path / "out.json"
    e.save_json([engram], out_file)
    
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["data"]["attributes"]["source"] == "vscode"

def test_export_jsonl(tmp_path: Path):
    e = Export()
    engram = Engram(
        id="test-123",
        source="vscode",
        source_file="test.json",
        project_name="TestProject",
        created_at=datetime.now(timezone.utc),
        messages=[Message(role="user", content="Hello")]
    )
    
    out_file = tmp_path / "out.jsonl"
    e.save_jsonl([engram, engram], out_file)
    
    assert out_file.exists()
    lines = [L for L in out_file.read_text(encoding="utf-8").splitlines() if L.strip()]
    assert len(lines) == 2

if __name__ == "__main__":
    import tempfile
    import shutil
    tmp = Path(tempfile.mkdtemp())
    try:
        test_compact_fallback(tmp)
        test_compact_parse_output()
        test_export_markdown()
        test_export_json(tmp)
        test_export_jsonl(tmp)
        print("All test_maintenance tests PASSED")
    finally:
        shutil.rmtree(tmp)
