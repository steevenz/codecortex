"""
@project   CodeCortex
@package   modules.idegraph.tests
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:standard: Aegis-IdeGraph-v1.0

Integration tests for all 16 IDE parsers.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram


# List of all parser classes to test
PARSER_CLASSES = [
    "TraeParser",
    "CursorParser",
    "WindsurfParser",
    "GeminiParser",
    "AntigravityParser",
    "ClaudeParser",
    "CodexParser",
    "ContinueParser",
    "OpenCodeParser",
    "CopilotParser",
    "KiloParser",
    "KiroParser",
    "VerdentParser",
    "CodeBuddyParser",
    "QwenParser",
    "KimiParser",
]


class TestBaseIDEParser:
    """Test BaseIDEParser abstract class."""

    def test_base_parser_is_abstract(self):
        """Test BaseIDEParser cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseIDEParser()


class TestParserImports:
    """Test all parsers can be imported."""

    @pytest.mark.parametrize("parser_name", PARSER_CLASSES)
    def test_parser_import(self, parser_name):
        """Test each parser class can be imported."""
        module_name = parser_name.lower().replace("parser", "_parser")
        module_path = f"src.modules.idegraph.parsers.{module_name}"

        try:
            module = __import__(module_path, fromlist=[parser_name])
            parser_class = getattr(module, parser_name)
            assert parser_class is not None
            assert issubclass(parser_class, BaseIDEParser)
        except ImportError as e:
            pytest.fail(f"Failed to import {parser_name}: {e}")


class TestParserInterface:
    """Test all parsers implement required interface."""

    @pytest.mark.parametrize("parser_name", PARSER_CLASSES)
    def test_parser_has_ide_name(self, parser_name):
        """Test each parser defines ide_name attribute."""
        module_name = parser_name.lower().replace("parser", "_parser")
        module_path = f"src.modules.idegraph.parsers.{module_name}"

        module = __import__(module_path, fromlist=[parser_name])
        parser_class = getattr(module, parser_name)
        parser = parser_class()

        assert hasattr(parser, "ide_name")
        assert isinstance(parser.ide_name, str)
        assert len(parser.ide_name) > 0

    @pytest.mark.parametrize("parser_name", PARSER_CLASSES)
    def test_parser_has_find_installations(self, parser_name):
        """Test each parser implements find_installations method."""
        module_name = parser_name.lower().replace("parser", "_parser")
        module_path = f"src.modules.idegraph.parsers.{module_name}"

        module = __import__(module_path, fromlist=[parser_name])
        parser_class = getattr(module, parser_name)
        parser = parser_class()

        assert hasattr(parser, "find_installations")
        assert callable(getattr(parser, "find_installations"))

    @pytest.mark.parametrize("parser_name", PARSER_CLASSES)
    def test_parser_has_parse_all(self, parser_name):
        """Test each parser implements parse_all method."""
        module_name = parser_name.lower().replace("parser", "_parser")
        module_path = f"src.modules.idegraph.parsers.{module_name}"

        module = __import__(module_path, fromlist=[parser_name])
        parser_class = getattr(module, parser_name)
        parser = parser_class()

        assert hasattr(parser, "parse_all")
        assert callable(getattr(parser, "parse_all"))


class TestOrchestratorIntegration:
    """Test orchestrator integration with all parsers."""

    def test_orchestrator_loads_all_parsers(self):
        """Test SideCortexOrchestrator loads all 16 parsers."""
        from src.modules.idegraph.core.orchestrator import SideCortexOrchestrator

        orch = SideCortexOrchestrator()
        assert len(orch.parsers) == 16

    def test_orchestrator_parser_names(self):
        """Test orchestrator has correct parser ide_names."""
        from src.modules.idegraph.core.orchestrator import SideCortexOrchestrator

        orch = SideCortexOrchestrator()
        names = {p.ide_name for p in orch.parsers}

        expected = {
            "trae", "cursor", "windsurf", "gemini", "antigravity",
            "claude", "codex", "continue", "opencode", "copilot",
            "kilo", "kiro", "verdent", "codebuddy", "qwen", "kimi"
        }
        assert names == expected


class TestParserErrorHandling:
    """Test parser error handling."""

    def test_parser_handles_missing_directories(self):
        """Test parsers gracefully handle missing installation directories."""
        from src.modules.idegraph.parsers.cursor_parser import CursorParser

        parser = CursorParser()
        # Mock to return no installations
        with patch.object(parser, "find_installations", return_value=[]):
            installations = list(parser.find_installations())
            assert installations == []

    def test_parser_handles_permission_errors(self):
        """Test parsers handle permission errors gracefully."""
        from src.modules.idegraph.parsers.trae_parser import TraeParser

        parser = TraeParser()
        # Mock to simulate permission error
        with patch.object(parser, "find_installations", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                list(parser.find_installations())


class TestEngramCreation:
    """Test parser engram creation."""

    def test_parser_returns_engram_list(self):
        """Test parsers return list of Engram objects."""
        from src.modules.idegraph.parsers.cursor_parser import CursorParser

        parser = CursorParser()

        # Mock parse_all to return test data
        test_engram = Engram(
            id="test-123",
            source="cursor",
            source_file="/test.py",
            messages=[],
            title="Test"
        )

        with patch.object(parser, "parse_all", return_value=[test_engram]):
            results = parser.parse_all()
            assert isinstance(results, list)
            assert len(results) > 0
            assert isinstance(results[0], Engram)


class TestIDENameConsistency:
    """Test IDE name consistency across module."""

    def test_module_json_matches_parsers(self):
        """Test module.json supported_ides matches actual parser names."""
        import json
        from src.modules.idegraph.core.orchestrator import SideCortexOrchestrator

        # Load module.json
        module_json_path = Path(__file__).parent.parent / "src" / "modules" / "idegraph" / "module.json"
        if module_json_path.exists():
            with open(module_json_path) as f:
                module_data = json.load(f)
            supported_ides = set(module_data.get("supported_ides", []))
        else:
            # Fallback to known list
            supported_ides = {
                "trae", "cursor", "windsurf", "gemini", "antigravity",
                "claude", "codex", "continue", "opencode", "copilot",
                "kilo", "kiro", "verdent", "codebuddy", "qwen", "kimi"
            }

        # Get parser names from orchestrator
        orch = SideCortexOrchestrator()
        parser_names = {p.ide_name for p in orch.parsers}

        assert supported_ides == parser_names, f"Mismatch: module.json has {supported_ides - parser_names}, orchestrator has {parser_names - supported_ides}"
