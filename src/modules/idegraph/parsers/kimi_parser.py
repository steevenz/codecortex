"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.parsers
:standard: Aegis-IdeGraph-v1.0
@fileoverview KimiParser - Parser for Kimi Code CLI chat data.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class KimiParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "kimi"

    def find_installations(self) -> List[Path]:
        kimi_dir = Path.home() / ".kimi"
        if kimi_dir.exists():
            return [kimi_dir]
        return []

    def parse_all(self) -> List[Engram]:
        all_engrams = []
        for inst in self.find_installations():
            all_engrams.extend(self._parse_sessions(inst))
        return all_engrams

    def _parse_sessions(self, installation: Path) -> List[Engram]:
        engrams = []
        sessions_dir = installation / "sessions"
        if not sessions_dir.exists():
            return engrams

        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue
            for chat_dir in session_dir.iterdir():
                wire_file = chat_dir / "wire.jsonl"
                if wire_file.exists():
                    engram = self._parse_wire_file(wire_file, installation)
                    if engram:
                        engrams.append(engram)
        return engrams

    def _parse_wire_file(self, wire_file: Path, installation: Path) -> Optional[Engram]:
        messages = []
        try:
            with open(wire_file, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    msg = data.get("message", {})
                    msg_type = msg.get("type")
                    payload = msg.get("payload", {})
                    ts = msg.get("timestamp") or data.get("timestamp")

                    if msg_type == "TurnBegin":
                        user_input = payload.get("user_input", [])
                        text = "\n".join(
                            p.get("text", "") for p in user_input if isinstance(p, dict)
                        )
                        if text:
                            messages.append(Message(
                                role="user",
                                content=str(text),
                                timestamp=str(datetime.fromtimestamp(ts)) if isinstance(ts, (int, float)) else None,
                            ))
                    elif msg_type == "TurnEnd":
                        messages.append(Message(
                            role="assistant",
                            content="(response stored server-side)",
                            timestamp=str(datetime.fromtimestamp(ts)) if isinstance(ts, (int, float)) else None,
                            metadata={"kimi_turn_end": True},
                        ))
        except Exception as e:
            logger.error(f"Error parsing Kimi wire file {wire_file}: {e}")
            return None

        if not messages:
            return None

        return Engram(
            id=str(uuid.uuid4()),
            source=self.ide_name,
            source_file=str(wire_file),
            messages=messages,
            metadata={"artifact_type": "kimi_chat"},
            ide_info=self._build_ide_info(ide_type="cli", installation_path=installation),
        )
