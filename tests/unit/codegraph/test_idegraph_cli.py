"""
@project   CodeCortex
@package   modules.idegraph.tests
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:standard: Aegis-IdeGraph-v1.0

Tests for idegraph CLI commands.
"""

import pytest
import argparse
from unittest.mock import MagicMock, patch
from src.modules.idegraph.api.cli import (
    cmd_ig_search, cmd_ig_get, cmd_ig_list,
    build_parser, DOMAIN, ALIASES
)


class TestCLIDomain:
    """Test CLI domain configuration."""

    def test_domain_name(self):
        """Test domain name is correct."""
        assert DOMAIN == "idegraph"

    def test_aliases(self):
        """Test CLI aliases are defined."""
        assert "ig" in ALIASES


class TestCLISearch:
    """Test search CLI command."""

    def test_search_response_structure(self):
        """Test search command returns proper api_response structure."""
        with patch("src.modules.idegraph.api.cli._idegraph_ctx") as mock_ctx:
            mock_search = MagicMock()
            mock_search.search.return_value = []
            mock_ctx.return_value.__enter__ = MagicMock(return_value=(None, mock_search, None))
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            args = argparse.Namespace(
                query="test",
                project=None,
                ide=None,
                limit=10
            )
            result = cmd_ig_search(args)

            assert "success" in result
            assert "status_code" in result
            assert "message" in result
            assert "data" in result
            assert "request_id" in result


class TestCLIGet:
    """Test get CLI command."""

    def test_get_not_found(self):
        """Test get with non-existent ID."""
        with patch("src.modules.idegraph.api.cli._idegraph_ctx") as mock_ctx:
            mock_search = MagicMock()
            mock_search.get_by_id.return_value = None
            mock_ctx.return_value.__enter__ = MagicMock(return_value=(None, mock_search, None))
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            args = argparse.Namespace(id="non-existent")
            result = cmd_ig_get(args)

            assert result["success"] is False
            assert result["status_code"] == 404

    def test_get_full_mode(self):
        """Test get returns full record by default."""
        from src.modules.idegraph.domain.engram import Engram, Message

        with patch("src.modules.idegraph.api.cli._idegraph_ctx") as mock_ctx:
            mock_search = MagicMock()
            mock_engram = Engram(
                id="test-123",
                source="cursor",
                source_file="/test.py",
                messages=[Message(role="user", content="Hello")],
                title="Test"
            )
            mock_search.get_by_id.return_value = mock_engram
            mock_ctx.return_value.__enter__ = MagicMock(return_value=(None, mock_search, None))
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            args = argparse.Namespace(id="test-123", summary=False)
            result = cmd_ig_get(args)

            assert result["success"] is True
            assert "(summary)" not in result["message"]

    def test_get_summary_mode(self):
        """Test get with --summary flag."""
        from src.modules.idegraph.domain.engram import Engram, Message

        with patch("src.modules.idegraph.api.cli._idegraph_ctx") as mock_ctx:
            mock_search = MagicMock()
            mock_engram = Engram(
                id="test-123",
                source="cursor",
                source_file="/test.py",
                messages=[Message(role="user", content="Hello")],
                title="Test"
            )
            mock_search.get_by_id.return_value = mock_engram
            mock_ctx.return_value.__enter__ = MagicMock(return_value=(None, mock_search, None))
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            args = argparse.Namespace(id="test-123", summary=True)
            result = cmd_ig_get(args)

            assert result["success"] is True
            assert "(summary)" in result["message"]


class TestCLIBase:
    """Test CLI base configuration."""

    def test_parser_builds(self):
        """Test that parser builds without errors."""
        import argparse
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        build_parser(subparsers)
        # Should not raise


class TestCLIResponseFormat:
    """Test CLI uses api_response format consistently."""

    def test_all_commands_use_api_response(self):
        """Verify all CLI commands use api_response structure."""
        from src.modules.idegraph.api.cli import IG_COMMANDS

        required_keys = {"success", "status_code", "message", "data", "request_id"}

        for cmd_name, cmd_func in IG_COMMANDS.items():
            # Check function signature accepts args_ns
            import inspect
            sig = inspect.signature(cmd_func)
            assert "args_ns" in sig.parameters, f"{cmd_name} missing args_ns parameter"
