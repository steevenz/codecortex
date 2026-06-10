"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.parsers
:standard: Aegis-IdeGraph-v1.0
@fileoverview GeminiParser - Parser for Google Gemini CLI chat data.
"""

import json
import platform
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class GeminiParser(BaseIDEParser):
    """Parser for Google Gemini CLI chat sessions."""

    @property
    def ide_name(self) -> str:
        return "gemini"

    def find_installations(self) -> List[Path]:
        system = platform.system()
        home = Path.home()
        locations = []

        patterns = ['gemini', '.gemini']

        if system == "Darwin":
            base_dirs = [home, home / ".config"]
        elif system == "Linux":
            base_dirs = [home / ".gemini", home / ".config/gemini", home / ".local/share/gemini", home]
        elif system == "Windows":
            base_dirs = [
                Path(os.environ.get('USERPROFILE', home)) / ".gemini",
                Path(os.environ.get('LOCALAPPDATA', home / 'AppData/Local')) / "gemini",
                home
            ]
        else:
            base_dirs = [home / ".gemini", home / ".config", home]

        for base_dir in base_dirs:
            if not base_dir.exists():
                continue
            for pattern in patterns:
                path = base_dir / pattern
                if path.exists():
                    locations.append(path)

        return list(set(locations))

    def parse_all(self) -> List[Engram]:
        all_engrams = []
        installations = self.find_installations()

        for inst in installations:
            session_dirs = [
                inst / 'tmp' / 'chats',
                inst / 'tmp',
                inst / 'chats',
                inst / 'chat',
            ]
            for sd in session_dirs:
                if sd.exists():
                    session_files = list(sd.glob('session-*.json')) + list(sd.glob('*.jsonl'))
                    for session_file in session_files:
                        engram = self._parse_session_file(session_file, inst)
                        if engram:
                            all_engrams.append(engram)

            tmp_dir = inst / 'tmp'
            if tmp_dir.exists():
                for profile_dir in tmp_dir.iterdir():
                    if profile_dir.is_dir():
                        chats_dir = profile_dir / 'chats'
                        if chats_dir.exists():
                            session_files = list(chats_dir.glob('session-*.json')) + list(chats_dir.glob('*.jsonl'))
                            for session_file in session_files:
                                engram = self._parse_session_file(session_file, inst)
                                if engram:
                                    all_engrams.append(engram)

            if not all_engrams:
                for db_file in inst.rglob('*.db'):
                    if self._is_sqlite(db_file):
                        all_engrams.extend(self._artifact_fallback(
                            source_file=str(db_file), installation=inst,
                            artifact_type="gemini_sqlite_unparsed",
                            details={"tables": self._sqlite_list_tables(db_file)},
                        ))

        return all_engrams

    def _parse_session_file(self, session_file: Path, installation: Path) -> Optional[Engram]:
        try:
            if session_file.suffix == '.jsonl':
                return self._parse_jsonl(session_file, installation)

            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'messages' not in data or not data['messages']:
                return None

            messages = []
            project_path = None
            for msg in data['messages']:
                msg_type = msg.get('type')
                role = 'user' if msg_type == 'user' else 'assistant'
                content = msg.get('content', '')

                normalized_msg = Message(
                    role=role,
                    content=content,
                    timestamp=msg.get('timestamp')
                )

                if role == 'assistant':
                    if 'thoughts' in msg and msg['thoughts']:
                        normalized_msg.metadata['gemini_thoughts'] = msg['thoughts']
                    if 'tokens' in msg and msg['tokens']:
                        normalized_msg.metadata['gemini_tokens'] = msg['tokens']
                    if 'model' in msg:
                        normalized_msg.metadata['gemini_model'] = msg['model']

                messages.append(normalized_msg)

                cwd = msg.get('cwd') or msg.get('projectPath')
                if isinstance(cwd, str) and not project_path:
                    project_path = cwd

            if not messages:
                return None

            resolved = self._detect_project_root(Path(project_path)) if project_path else None
            project_root = str(resolved) if resolved else project_path

            return Engram(
                id=data.get('sessionId', str(uuid.uuid4())),
                source=self.ide_name,
                source_file=str(session_file),
                messages=messages,
                created_at=datetime.fromisoformat(data['startTime'].replace('Z', '+00:00')) if 'startTime' in data else datetime.now(),
                workspace_id=project_root,
                project_path=project_root,
                metadata={
                    'project_hash': data.get('projectHash'),
                    'last_updated': data.get('lastUpdated'),
                },
                ide_info=self._build_ide_info(ide_type="cli", installation_path=installation)
            )

        except Exception as e:
            logger.error(f"Error parsing Gemini session {session_file}: {e}")
            return None

    def _parse_jsonl(self, jsonl_file: Path, installation: Path) -> Optional[Engram]:
        try:
            messages = []
            project_path = None
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    obj = self._safe_json_loads(line)
                    if not obj:
                        continue
                    msg_type = obj.get('type', obj.get('role'))
                    role = 'user' if msg_type in ('user', 'user_message') else 'assistant'
                    content = obj.get('message', obj.get('content', ''))
                    if content:
                        messages.append(Message(
                            role=role, content=content,
                            timestamp=obj.get('timestamp'),
                        ))
                    cwd = obj.get('cwd') or obj.get('projectPath')
                    if isinstance(cwd, str) and not project_path:
                        project_path = cwd
            if not messages:
                return None
            resolved = self._detect_project_root(Path(project_path)) if project_path else None
            project_root = str(resolved) if resolved else project_path
            return Engram(
                id=str(uuid.uuid4()), source=self.ide_name,
                source_file=str(jsonl_file), messages=messages,
                workspace_id=project_root, project_path=project_root,
                ide_info=self._build_ide_info(ide_type="cli", installation_path=installation),
            )
        except Exception as e:
            logger.error(f"Error parsing Gemini JSONL {jsonl_file}: {e}")
            return None
