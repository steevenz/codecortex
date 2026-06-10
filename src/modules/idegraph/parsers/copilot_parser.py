"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.parsers
:standard: Aegis-IdeGraph-v1.0
@fileoverview CopilotParser - Parser for GitHub Copilot chat interaction data.
"""

import platform
import os
from pathlib import Path
from typing import List
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

COPILOT_SQLITE_KEYS = [
    "chat", "chats", "conversation", "conversations",
    "github.copilot.chat", "copilot-chat",
]

class CopilotParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "copilot"

    def find_installations(self) -> List[Path]:
        system = platform.system()
        home = Path.home()
        locations = []

        if system == "Darwin":
            base_dirs = [home / "Library/Application Support"]
        elif system == "Linux":
            base_dirs = [home / ".config"]
        elif system == "Windows":
            base_dirs = [
                Path(os.environ.get('APPDATA', home / 'AppData/Roaming')),
            ]
        else:
            base_dirs = [home / ".config"]

        patterns = [
            'Code/User/globalStorage/github.copilot-chat',
            'Code - Insiders/User/globalStorage/github.copilot-chat',
            'Cursor/User/globalStorage/github.copilot-chat',
            'VSCodium/User/globalStorage/github.copilot-chat',
        ]

        for base_dir in base_dirs:
            if not base_dir.exists():
                continue
            for pattern in patterns:
                target = base_dir / pattern
                if target.exists():
                    locations.append(target)

        return list(set(locations))

    def parse_all(self) -> List[Engram]:
        installations = self.find_installations()
        all_engrams = []
        for inst in installations:
            all_engrams.extend(self._parse_vscode_extension_sessions(inst))
            all_engrams.extend(self._scan_vscode_sqlite_storage(inst, COPILOT_SQLITE_KEYS))

        if not all_engrams:
            for inst in installations:
                all_engrams.extend(self._artifact_fallback(
                    source_file=str(inst), installation=inst,
                    artifact_type="copilot_unparsed",
                ))

        return all_engrams
