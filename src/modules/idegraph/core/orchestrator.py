"""
@project   CodeCortex
@package   modules.idegraph.core
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.core
:standard: CODDY-IdeGraph-v1.0

SideCortexOrchestrator — Orchestrates all 16 IDE parsers to harvest cross-IDE memories.
"""

from typing import List, Dict, Any
from pathlib import Path
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram
from src.modules.idegraph.parsers.trae_parser import TraeParser
from src.modules.idegraph.parsers.cursor_parser import CursorParser
from src.modules.idegraph.parsers.windsurf_parser import WindsurfParser
from src.modules.idegraph.parsers.gemini_parser import GeminiParser
from src.modules.idegraph.parsers.antigravity_parser import AntigravityParser
from src.modules.idegraph.parsers.claude_parser import ClaudeParser
from src.modules.idegraph.parsers.codex_parser import CodexParser
from src.modules.idegraph.parsers.continue_parser import ContinueParser
from src.modules.idegraph.parsers.opencode_parser import OpenCodeParser
from src.modules.idegraph.parsers.copilot_parser import CopilotParser
from src.modules.idegraph.parsers.kilo_parser import KiloParser
from src.modules.idegraph.parsers.kiro_parser import KiroParser
from src.modules.idegraph.parsers.verdent_parser import VerdentParser
from src.modules.idegraph.parsers.codebuddy_parser import CodeBuddyParser
from src.modules.idegraph.parsers.qwen_parser import QwenParser
from src.modules.idegraph.parsers.kimi_parser import KimiParser
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class SideCortexOrchestrator:
    """Orchestrates multiple IDE parsers to ingest AI interaction data."""

    def __init__(self):
        self.parsers: List[BaseIDEParser] = [
            TraeParser(),
            CursorParser(),
            WindsurfParser(),
            GeminiParser(),
            AntigravityParser(),
            ClaudeParser(),
            CodexParser(),
            ContinueParser(),
            OpenCodeParser(),
            CopilotParser(),
            KiloParser(),
            KiroParser(),
            VerdentParser(),
            CodeBuddyParser(),
            QwenParser(),
            KimiParser(),
        ]

    def run_all(self) -> List[Engram]:
        """Run all registered parsers and return a combined list of engrams."""
        all_engrams = []

        for parser in self.parsers:
            try:
                logger.info(f"Running parser: {parser.ide_name}")
                engrams = parser.parse_all()
                all_engrams.extend(engrams)
                logger.info(f"Parser {parser.ide_name} found {len(engrams)} engrams.")
            except Exception as e:
                logger.error(f"Error running parser {parser.ide_name}: {e}")

        return all_engrams

    def get_stats(self, engrams: List[Engram]) -> Dict[str, int]:
        """Generate statistics about the ingested engrams."""
        stats = {}
        for engram in engrams:
            stats[engram.source] = stats.get(engram.source, 0) + 1
        return stats
