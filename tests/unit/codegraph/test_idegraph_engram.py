"""
@project   CodeCortex
@package   modules.idegraph.tests
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.tests
:standard: Aegis-IdeGraph-v1.0

Tests for idegraph Engram domain model.
"""

import pytest
from datetime import datetime
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo


class TestIDEInfo:
    """Test IDEInfo dataclass."""

    def test_ideinfo_to_dict(self):
        """Test IDEInfo serialization to dict."""
        info = IDEInfo(
            name="cursor",
            type="vscode-extension",
            installation_path="/path/to/cursor",
            version="0.45.0"
        )
        data = info.to_dict()
        assert data["name"] == "cursor"
        assert data["type"] == "vscode-extension"
        assert data["installation_path"] == "/path/to/cursor"
        assert data["version"] == "0.45.0"
        assert "detected_at" in data

    def test_ideinfo_from_dict(self):
        """Test IDEInfo deserialization from dict."""
        data = {
            "name": "trae",
            "type": "desktop",
            "installation_path": "/path/to/trae",
            "version": "1.0.0",
            "detected_at": "2026-01-01T00:00:00"
        }
        info = IDEInfo.from_dict(data)
        assert info.name == "trae"
        assert info.type == "desktop"
        assert info.installation_path == "/path/to/trae"
        assert info.version == "1.0.0"


class TestMessage:
    """Test Message dataclass."""

    def test_message_to_dict(self):
        """Test Message serialization."""
        msg = Message(
            role="user",
            content="Hello world",
            timestamp="2026-01-01T00:00:00",
            metadata={"key": "value"}
        )
        data = msg.to_dict()
        assert data["role"] == "user"
        assert data["content"] == "Hello world"
        assert data["timestamp"] == "2026-01-01T00:00:00"
        assert data["metadata"] == {"key": "value"}

    def test_message_content_normalization(self):
        """Test Message content normalization for non-string inputs."""
        msg = Message(role="assistant", content=["line1", "line2"])
        assert msg.content == "line1\nline2"

    def test_message_from_dict(self):
        """Test Message deserialization."""
        data = {
            "role": "user",
            "content": "test content",
            "timestamp": "2026-01-01T00:00:00",
            "metadata": {"foo": "bar"}
        }
        msg = Message.from_dict(data)
        assert msg.role == "user"
        assert msg.content == "test content"


class TestEngram:
    """Test Engram dataclass."""

    def test_engram_to_export_record(self):
        """Test full export record generation."""
        engram = Engram(
            id="test-123",
            source="cursor",
            source_file="/path/to/file.py",
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there")
            ],
            title="Test conversation",
            project_name="my-project"
        )
        record = engram.to_export_record(request_id="req_123", version="1.0.0")
        assert record["success"] is True
        assert record["status_code"] == 200
        assert record["data"]["type"] == "engram"
        assert record["data"]["id"] == "test-123"
        assert record["data"]["attributes"]["source"] == "cursor"
        assert len(record["data"]["attributes"]["messages"]) == 2
        assert "workspace_key" in record["data"]["attributes"]

    def test_engram_to_summary_record(self):
        """Test summary record generation (token efficient)."""
        engram = Engram(
            id="test-456",
            source="cursor",
            source_file="/path/to/file.py",
            messages=[
                Message(role="user", content="This is a very long message that should be truncated in summary mode"),
                Message(role="assistant", content="Another long response here"),
                Message(role="user", content="Third message")
            ],
            title="Test conversation",
            project_name="my-project"
        )
        record = engram.to_summary_record(request_id="req_456", version="1.0.0")
        assert record["success"] is True
        assert record["data"]["type"] == "engram_summary"
        assert record["data"]["attributes"]["message_count"] == 3
        # Summary should have first 100 chars only
        snippet = record["data"]["attributes"]["first_message_snippet"]
        assert len(snippet) <= 103  # 100 + "..."
        assert "messages" not in record["data"]["attributes"]

    def test_engram_compute_workspace_key(self):
        """Test workspace key computation."""
        key1 = Engram.compute_workspace_key(
            project_path="/path/to/project",
            project_name="project",
            workspace_id=None,
            source_file="/path/to/file.py"
        )
        key2 = Engram.compute_workspace_key(
            project_path="/path/to/project",
            project_name="project",
            workspace_id=None,
            source_file="/path/to/file.py"
        )
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex

    def test_engram_from_dict(self):
        """Test Engram deserialization."""
        data = {
            "id": "test-789",
            "source": "trae",
            "source_file": "/path/to/file.py",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "project_name": "test-project",
            "title": "Test"
        }
        engram = Engram.from_dict(data)
        assert engram.id == "test-789"
        assert engram.source == "trae"
        assert len(engram.messages) == 1

    def test_engram_from_export_record_format(self):
        """Test Engram from export record format."""
        export_data = {
            "data": {
                "id": "engram-001",
                "attributes": {
                    "source": "cursor",
                    "source_file": "/test.py",
                    "messages": [{"role": "user", "content": "test"}],
                    "project_name": "test"
                }
            }
        }
        engram = Engram.from_dict(export_data)
        assert engram.id == "engram-001"
        assert engram.source == "cursor"
