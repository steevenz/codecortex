"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.parsers
:standard: Aegis-IdeGraph-v1.0
@fileoverview ClaudeParser - Parser for Claude Code AI interaction data.
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

SESSIONS_DB_KEYS = [
    "session",
    "sessions",
    "conversation",
    "conversations",
    "claude-session",
]

class ClaudeParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "claude"

    def find_installations(self) -> List[Path]:
        system = platform.system()
        home = Path.home()
        locations = []

        if system == "Darwin":
            base_dirs = [home / "Library/Application Support", home / ".config"]
        elif system == "Linux":
            base_dirs = [home / ".config", home / ".local/share"]
        elif system == "Windows":
            base_dirs = [
                Path(os.environ.get('APPDATA', home / 'AppData/Roaming')),
                Path(os.environ.get('LOCALAPPDATA', home / 'AppData/Local'))
            ]
        else:
            base_dirs = [home / ".config"]

        claude_patterns = [
            'claude', 'claude-code', 'claude-local', 'claude-m2', 'claude-zai',
            '.claude', '.claude-code', '.claude-local', '.claude-m2', '.claude-zai'
        ]

        for base_dir in base_dirs:
            if not base_dir.exists(): continue
            for pattern in claude_patterns:
                claude_dir = base_dir / pattern
                if claude_dir.exists():
                    locations.append(claude_dir)

        for pattern in claude_patterns:
            home_dir = home / pattern
            if home_dir.exists():
                locations.append(home_dir)

        return list(set(locations))

    def parse_all(self) -> List[Engram]:
        installations = self.find_installations()
        all_engrams = []
        for inst in installations:
            all_engrams.extend(self._parse_installation(inst))
        return all_engrams

    def _parse_installation(self, installation: Path) -> List[Engram]:
        engrams = []
        jsonl_files = []
        found_any = False

        if (installation / 'projects').exists():
            for proj in (installation / 'projects').iterdir():
                if proj.is_dir():
                    jsonl_files.extend(list(proj.glob('*.jsonl')))
        else:
            jsonl_files = list(installation.glob('*.jsonl'))

        jsonl_files = [f for f in jsonl_files if not f.name.startswith('agent-')]

        for jsonl_file in jsonl_files:
            found_any = True
            try:
                messages = []
                metadata = {}
                project_path = None

                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip(): continue
                        obj = self._safe_json_loads(line)
                        if not obj: continue

                        msg_type = obj.get('type')
                        if msg_type == 'user':
                            message = obj.get('message', {})
                            content = message.get('content', '')
                            if content:
                                messages.append(Message(
                                    role='user',
                                    content=content,
                                    timestamp=obj.get('timestamp'),
                                    tool_use=obj.get('toolUse', [])
                                ))
                            if 'cwd' in obj:
                                project_path = obj['cwd']
                        elif msg_type == 'assistant':
                            message = obj.get('message', {})
                            content = message.get('content', [])
                            text_parts = []
                            tool_uses = []

                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict):
                                        if item.get('type') == 'text':
                                            text_parts.append(item.get('text', ''))
                                        elif item.get('type') == 'tool_use':
                                            tool_uses.append(item)
                            elif isinstance(content, str):
                                text_parts.append(content)

                            full_text = '\n'.join(text_parts)
                            if full_text or tool_uses:
                                messages.append(Message(
                                    role='assistant',
                                    content=full_text,
                                    timestamp=obj.get('timestamp'),
                                    tool_use=tool_uses
                                ))

                if messages:
                    resolved = self._detect_project_root(Path(project_path)) if project_path else None
                    project_root = str(resolved) if resolved else project_path
                    engrams.append(Engram(
                        id=str(uuid.uuid4()),
                        source=self.ide_name,
                        source_file=str(jsonl_file),
                        messages=messages,
                        workspace_id=project_root,
                        project_path=project_root,
                        metadata={'project_path': project_root} if project_root else {},
                        ide_info=self._build_ide_info(ide_type="cli", installation_path=installation)
                    ))
            except Exception as e:
                logger.error(f"Error parsing Claude JSONL {jsonl_file}: {e}")

        if not found_any:
            engrams.extend(self._scan_claude_sqlite_sessions(installation))

        if not engrams:
            engrams.extend(self._artifact_fallback(
                source_file=str(installation), installation=installation,
                artifact_type="claude_unparsed",
                details={"path": str(installation)},
            ))

        return engrams

    def _scan_claude_sqlite_sessions(self, installation: Path) -> List[Engram]:
        engrams = []
        for db_file in installation.rglob('*.db'):
            if not db_file.is_file() or not self._is_sqlite(db_file):
                continue
            tables = self._sqlite_list_tables(db_file)

            for key in SESSIONS_DB_KEYS:
                rows = self._read_sqlite(db_file, "SELECT value FROM ItemTable WHERE [key] = ? LIMIT 1", (key,))
                if not rows:
                    rows = self._read_sqlite(db_file, "SELECT value FROM ItemTable WHERE [key] LIKE ? LIMIT 1", (f"%{key}%",))
                if not rows:
                    for t in tables:
                        rows = self._read_sqlite(db_file, f"SELECT * FROM \"{t}\" LIMIT 1")
                        if rows:
                            break
                    if not rows:
                        continue

                raw_value = rows[0][0]
                store = self._safe_json_loads(raw_value)
                if not isinstance(store, (dict, list)):
                    continue

                messages = []
                history = store if isinstance(store, list) else store.get('messages', store.get('history', store.get('conversations', [])))
                if isinstance(history, list):
                    for item in history:
                        if not isinstance(item, dict):
                            continue
                        role = item.get('role') or item.get('type')
                        content = item.get('content') or item.get('text') or item.get('message') or ''
                        if role and content:
                            messages.append(Message(role=str(role), content=content, timestamp=item.get('timestamp')))
                if messages:
                    engrams.append(Engram(
                        id=str(uuid.uuid4()), source=self.ide_name, source_file=str(db_file),
                        messages=messages,
                        metadata={"source_key": key, "artifact_type": "claude_sqlite_session"},
                        ide_info=self._build_ide_info(ide_type="cli", installation_path=installation),
                    ))

        return engrams
