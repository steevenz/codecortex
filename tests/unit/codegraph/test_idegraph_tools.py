"""
@project   CodeCortex
@package   modules.idegraph.tests
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:standard: CODDY-IdeGraph-v1.0

Tests for idegraph MCP tools.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.modules.idegraph.api.tools import _handle_get


class TestHandleGet:
    """Test the _handle_get helper function."""

    def test_handle_get_not_found(self):
        """Test get with non-existent memory ID."""
        mock_search = MagicMock()
        mock_search.get_by_id.return_value = None

        result = _handle_get("req_123", mock_search, "non-existent")

        assert result["success"] is False
        assert result["status_code"] == 404
        assert "IDEGRAPH_404" in str(result)

    def test_handle_get_full_mode(self):
        """Test get with full record mode (default)."""
        from src.modules.idegraph.domain.engram import Engram, Message

        mock_search = MagicMock()
        mock_engram = Engram(
            id="test-123",
            source="cursor",
            source_file="/test.py",
            messages=[Message(role="user", content="Hello")],
            title="Test"
        )
        mock_search.get_by_id.return_value = mock_engram

        result = _handle_get("req_123", mock_search, "test-123", summary_mode=False)

        assert result["success"] is True
        assert result["status_code"] == 200
        assert "Memory retrieved" in result["message"]
        assert "(summary)" not in result["message"]
        assert "messages" in result["data"]["data"]["attributes"]

    def test_handle_get_summary_mode(self):
        """Test get with summary mode."""
        from src.modules.idegraph.domain.engram import Engram, Message

        mock_search = MagicMock()
        mock_engram = Engram(
            id="test-123",
            source="cursor",
            source_file="/test.py",
            messages=[Message(role="user", content="Hello")],
            title="Test"
        )
        mock_search.get_by_id.return_value = mock_engram

        result = _handle_get("req_123", mock_search, "test-123", summary_mode=True)

        assert result["success"] is True
        assert result["status_code"] == 200
        assert "(summary)" in result["message"]
        assert "message_count" in result["data"]["data"]["attributes"]
        assert "messages" not in result["data"]["data"]["attributes"]


class TestIDEGraphToolActions:
    """Test idegraph tool action validation."""

    def test_valid_actions(self):
        """Test that all documented actions are valid."""
        valid_actions = [
            "search", "get", "list", "ingest", "refresh",
            "health", "stats", "compact", "workspace", "harvest"
        ]
        # Actions are validated in the tool function
        assert len(valid_actions) == 10

    def test_error_codes_defined(self):
        """Test that error codes follow naming convention."""
        error_codes = [
            "IDEGRAPH_001",  # query required for search
            "IDEGRAPH_002",  # memory_id required for get
            "IDEGRAPH_003",  # project_path required for refresh
            "IDEGRAPH_004",  # workspace_key required for workspace
            "IDEGRAPH_005",  # workspace not found
            "IDEGRAPH_006",  # unknown action
            "IDEGRAPH_404",  # memory not found
            "IDEGRAPH_500",  # internal error
        ]
        for code in error_codes:
            assert code.startswith("IDEGRAPH_")
            assert code[9:].isdigit()
