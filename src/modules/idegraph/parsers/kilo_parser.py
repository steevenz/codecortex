"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.parsers
:standard: CODDY-IdeGraph-v1.0
@fileoverview KiloParser - Parser for Kilo Code AI interaction data.
"""

import platform
import os
from pathlib import Path
from typing import List
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

KILO_SQLITE_KEYS = [
    "kilo", "kilocode", "chat", "conversation",
    "kilo-chat", "kilo-session",
]

class KiloParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "kilo"

    def find_installations(self) -> List[Path]:
        system = platform.system()
        home = Path.home()
        locations = []

        dot_kilocode = home / ".kilocode"
        if dot_kilocode.exists():
            locations.append(dot_kilocode)

        if system == "Darwin":
            base_dirs = [home / "Library/Application Support"]
        elif system == "Linux":
            base_dirs = [home / ".config", home / ".local/share"]
        elif system == "Windows":
            base_dirs = [
                Path(os.environ.get('APPDATA', home / 'AppData/Roaming')),
                Path(os.environ.get('LOCALAPPDATA', home / 'AppData/Local')),
            ]
        else:
            base_dirs = [home / ".config"]

        patterns = ['kilo', 'kilocode', '.kilo', '.kilocode', 'Kilo Code', 'KiloCode']

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
            all_engrams.extend(self._scan_vscode_sqlite_storage(inst, KILO_SQLITE_KEYS))
            gs = inst / "globalStorage"
            if gs.exists():
                all_engrams.extend(self._scan_vscode_sqlite_storage(gs, KILO_SQLITE_KEYS, installation_path=inst))

        if not all_engrams:
            for inst in installations:
                all_engrams.extend(self._artifact_fallback(
                    source_file=str(inst), installation=inst,
                    artifact_type="kilo_unparsed",
                ))

        return all_engrams
