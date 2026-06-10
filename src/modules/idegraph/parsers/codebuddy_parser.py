"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.parsers
:standard: Aegis-IdeGraph-v1.0
@fileoverview CodeBuddyParser - Parser for CodeBuddy AI interaction data.
"""

import json
import sqlite3
import platform
import os
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

CODEBUDDY_SESSION_KEYS = ["session:", "conversation:"]

class CodeBuddyParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "codebuddy"

    def find_installations(self) -> List[Path]:
        system = platform.system()
        home = Path.home()
        locations = []

        if system == "Darwin":
            base_dirs = [home / "Library/Application Support"]
        elif system == "Linux":
            base_dirs = [home / ".config"]
        elif system == "Windows":
            base_dirs = [Path(os.environ.get('APPDATA', home / 'AppData/Roaming'))]
        else:
            base_dirs = [home / ".config"]

        for base_dir in base_dirs:
            candidate = base_dir / "CodeBuddy"
            if candidate.exists():
                locations.append(candidate)

        return locations

    def parse_all(self) -> List[Engram]:
        all_engrams = []
        installations = self.find_installations()
        for inst in installations:
            all_engrams.extend(self._parse_sessions_db(inst))
            all_engrams.extend(self._parse_workspace_storages(inst))

        if not all_engrams and installations:
            all_engrams.extend(self._artifact_fallback(
                source_file=str(installations[0]), installation=installations[0],
                artifact_type="codebuddy_unparsed",
            ))

        return all_engrams

    def _parse_sessions_db(self, installation: Path) -> List[Engram]:
        db_path = installation / "codebuddy-sessions.vscdb"
        if not db_path.exists():
            return []

        engrams = []
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT key, value FROM ItemTable ORDER BY key").fetchall()
            for r in rows:
                key = r["key"]
                val = r["value"]
                if not any(key.startswith(p) for p in CODEBUDDY_SESSION_KEYS):
                    continue
                try:
                    data = json.loads(val) if isinstance(val, str) else val
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue

                cwd = data.get("cwd")
                resolved = self._detect_project_root(Path(cwd)) if cwd else None
                project_root = str(resolved) if resolved else cwd

                engrams.append(Engram(
                    id=data.get("conversationId", str(uuid.uuid4())),
                    source=self.ide_name,
                    source_file=str(db_path),
                    messages=[
                        Message(role="system", content=f"session_metadata:{data.get('title', 'Untitled')}"),
                    ],
                    title=data.get("title", "CodeBuddy session"),
                    workspace_id=project_root,
                    project_path=project_root,
                    metadata={"status": data.get("status"), "conversation_id": data.get("conversationId")},
                    ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
                ))
            conn.close()
        except Exception as e:
            logger.error(f"Error parsing CodeBuddy sessions DB: {e}")

        return engrams

    def _parse_workspace_storages(self, installation: Path) -> List[Engram]:
        ws_dir = installation / "User/workspaceStorage"
        if not ws_dir.exists():
            return []
        engrams = []
        for ws in ws_dir.iterdir():
            if not ws.is_dir():
                continue
            vscdb = ws / "state.vscdb"
            if vscdb.exists():
                engrams.extend(self._artifact_fallback(
                    source_file=str(vscdb), installation=installation,
                    artifact_type="codebuddy_workspace_db",
                    details={"workspace_id": ws.name, "tables": self._sqlite_list_tables(vscdb)},
                ))
        return engrams
