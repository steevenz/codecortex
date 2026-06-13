"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.parsers
:standard: CODDY-IdeGraph-v1.0
@fileoverview QwenParser - Parser for Qwen CLI chat data.
"""

import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class QwenParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "qwen"

    def find_installations(self) -> List[Path]:
        qwen_dir = Path.home() / ".qwen"
        if qwen_dir.exists():
            return [qwen_dir]
        return []

    def parse_all(self) -> List[Engram]:
        all_engrams = []
        for inst in self.find_installations():
            all_engrams.extend(self._parse_jsonl_chats(inst))
        return all_engrams

    def _parse_jsonl_chats(self, installation: Path) -> List[Engram]:
        engrams = []
        projects_dir = installation / "projects"
        if not projects_dir.exists():
            return engrams

        for project_dir in projects_dir.iterdir():
            chats_dir = project_dir / "chats"
            if not chats_dir.exists():
                continue
            for jsonl_file in chats_dir.glob("*.jsonl"):
                try:
                    engram = self._parse_jsonl_file(jsonl_file, installation)
                    if engram:
                        engrams.append(engram)
                except Exception as e:
                    logger.error(f"Error parsing Qwen JSONL {jsonl_file}: {e}")

        return engrams

    def _parse_jsonl_file(self, jsonl_file: Path, installation: Path) -> Optional[Engram]:
        messages = []
        project_path = None
        session_id = None

        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                data = self._safe_json_loads(line)
                if not data:
                    continue

                if not session_id:
                    session_id = data.get("sessionId")
                msg_type = data.get("type", "")
                msg_data = data.get("message") or {}
                role = msg_data.get("role", "unknown")
                parts = msg_data.get("parts", [])
                content = "\n".join(
                    p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")
                )
                if not content:
                    continue

                messages.append(Message(
                    role=str(role),
                    content=str(content),
                    timestamp=data.get("timestamp"),
                ))

                cwd = data.get("cwd")
                if isinstance(cwd, str) and not project_path:
                    project_path = cwd

        if not messages:
            return None

        resolved = self._detect_project_root(Path(project_path)) if project_path else None
        project_root = str(resolved) if resolved else project_path

        return Engram(
            id=session_id or str(uuid.uuid4()),
            source=self.ide_name,
            source_file=str(jsonl_file),
            messages=messages,
            workspace_id=project_root,
            project_path=project_root,
            metadata={"artifact_type": "qwen_chat"},
            ide_info=self._build_ide_info(ide_type="cli", installation_path=installation),
        )
