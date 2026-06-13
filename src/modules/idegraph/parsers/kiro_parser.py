"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.parsers
:standard: CODDY-IdeGraph-v1.0
@fileoverview KiroParser - Parser for Kiro AI interaction data.
"""

import json
import platform
import os
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class KiroParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "kiro"

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
            candidate = base_dir / "Kiro"
            if candidate.exists():
                locations.append(candidate)

        return locations

    def parse_all(self) -> List[Engram]:
        all_engrams = []
        installations = self.find_installations()
        for inst in installations:
            all_engrams.extend(self._parse_session_files(inst))
        return all_engrams

    def _parse_session_files(self, installation: Path) -> List[Engram]:
        engrams = []
        agent_dir = installation / "User/globalStorage/kiro.kiroagent"
        if not agent_dir.exists():
            return engrams

        ws_dir = agent_dir / "workspace-sessions"
        if not ws_dir.exists():
            return engrams

        for workspace_dir in ws_dir.iterdir():
            if not workspace_dir.is_dir():
                continue

            sessions_json = workspace_dir / "sessions.json"
            if not sessions_json.exists():
                continue

            try:
                session_index = json.loads(sessions_json.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Error reading Kiro sessions.json: {e}")
                continue

            for entry in session_index:
                sid = entry.get("sessionId")
                if not sid:
                    continue
                session_file = workspace_dir / f"{sid}.json"
                if not session_file.exists():
                    continue

                engram = self._parse_session_file(session_file, entry, installation)
                if engram:
                    engrams.append(engram)

        return engrams

    def _parse_session_file(self, session_file: Path, index_entry: Dict[str, Any], installation: Path) -> Optional[Engram]:
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Error parsing Kiro session {session_file}: {e}")
            return None

        messages = []
        turns = data.get("history") or data.get("turns") or data.get("messages") or data.get("conversation", [])
        if isinstance(turns, dict):
            turns = list(turns.values())

        project_path = index_entry.get("workspaceDirectory") or data.get("workspaceDirectory")
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            msg_data = turn.get("message") or turn
            role = msg_data.get("role") or turn.get("role") or turn.get("author") or "unknown"
            content_raw = msg_data.get("content") or turn.get("content") or turn.get("text") or ""
            if isinstance(content_raw, list):
                content = "\n".join(str(c.get("text", "")) for c in content_raw if isinstance(c, dict) and c.get("text"))
            else:
                content = str(content_raw)
            if not content.strip():
                continue
            messages.append(Message(
                role=str(role).lower(),
                content=str(content)[:50000],
                timestamp=turn.get("timestamp") or turn.get("createdAt"),
                tool_use=turn.get("toolCalls") or msg_data.get("toolCalls") or [],
                code_context=[c for c in turn.get("contextItems", []) if isinstance(c, dict)],
            ))

        if not messages:
            return None

        title = index_entry.get("title") or data.get("title") or "Kiro session"
        resolved = self._detect_project_root(Path(project_path)) if project_path else None
        project_root = str(resolved) if resolved else project_path

        return Engram(
            id=sid if (sid := index_entry.get("sessionId")) else str(uuid.uuid4()),
            source=self.ide_name,
            source_file=str(session_file),
            messages=messages,
            title=str(title)[:120],
            workspace_id=project_root,
            project_path=project_root,
            metadata={"agent": data.get("agent")},
            ide_info=self._build_ide_info(ide_type="desktop", installation_path=installation),
        )
