"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.parsers
:standard: CODDY-IdeGraph-v1.0
@fileoverview CodexParser - Parser for Codex AI interaction data.
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

class CodexParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "codex"

    def find_installations(self) -> List[Path]:
        system = platform.system()
        home = Path.home()
        locations = []

        dot_codex = home / ".codex"
        if dot_codex.exists():
            locations.append(dot_codex)

        codex_patterns = ['codex', 'codex-local', '.codex', '.codex-local']

        if system == "Darwin":
            base_dirs = [home / "Library/Application Support", home / ".config", home]
        elif system == "Linux":
            base_dirs = [home / ".config", home / ".local/share", home]
        elif system == "Windows":
            base_dirs = [
                Path(os.environ.get('APPDATA', home / 'AppData/Roaming')),
                Path(os.environ.get('LOCALAPPDATA', home / 'AppData/Local')),
                home
            ]
        else:
            base_dirs = [home / ".config", home]

        for base_dir in base_dirs:
            if not base_dir.exists(): continue
            for pattern in codex_patterns:
                codex_dir = base_dir / pattern
                if codex_dir.exists():
                    locations.append(codex_dir)

        return list(set(locations))

    def parse_all(self) -> List[Engram]:
        installations = self.find_installations()
        all_engrams = []
        for inst in installations:
            all_engrams.extend(self._parse_installation(inst))
        return all_engrams

    def _parse_installation(self, installation: Path) -> List[Engram]:
        engrams = []
        session_files = []

        sessions_dir = installation / 'sessions'
        if sessions_dir.exists():
            session_files.extend(list(sessions_dir.rglob('rollout-*.jsonl')))

        projects_dir = installation / 'projects'
        if projects_dir.exists():
            session_files.extend(list(projects_dir.rglob('*.jsonl')))

        for session_file in session_files:
            try:
                messages = []
                metadata = {}
                tool_results = []
                project_path = None

                with open(session_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip(): continue
                        obj = self._safe_json_loads(line)
                        if not obj: continue

                        event_type = obj.get('type')
                        if event_type == 'session_meta':
                            metadata.update(obj.get('payload', {}))
                            cwd = obj.get('payload', {}).get('cwd') or obj.get('payload', {}).get('projectPath')
                            if isinstance(cwd, str) and not project_path:
                                project_path = cwd
                        elif event_type == 'event_msg':
                            payload = obj.get('payload', {})
                            payload_type = payload.get('type')

                            if payload_type == 'user_message':
                                message_text = payload.get('message', '').strip()
                                if message_text:
                                    messages.append(Message(
                                        role='user',
                                        content=message_text,
                                        timestamp=obj.get('timestamp'),
                                        code_context=payload.get('context', [])
                                    ))
                                    cwd = payload.get('cwd') or obj.get('cwd')
                                    if isinstance(cwd, str) and not project_path:
                                        project_path = cwd
                            elif payload_type == 'agent_message':
                                message_text = payload.get('message', '').strip()
                                if message_text:
                                    msg = Message(
                                        role='assistant',
                                        content=message_text,
                                        timestamp=obj.get('timestamp'),
                                        metadata={'model': payload.get('model')}
                                    )
                                    messages.append(msg)
                            elif payload_type in ('tool_use', 'tool_result', 'diff'):
                                if messages:
                                    messages[-1].tool_use.append(payload)
                                tool_results.append(payload)

                if messages:
                    resolved = self._detect_project_root(Path(project_path)) if project_path else None
                    project_root = str(resolved) if resolved else project_path
                    model = metadata.get('model') or next((m.metadata.get('model') for m in messages if m.metadata.get('model')), None)
                    engrams.append(Engram(
                        id=str(uuid.uuid4()),
                        source=self.ide_name,
                        source_file=str(session_file),
                        messages=messages,
                        workspace_id=project_root,
                        project_path=project_root,
                        model=model,
                        metadata=metadata,
                        ide_info=self._build_ide_info(ide_type="cli", installation_path=installation)
                    ))
            except Exception as e:
                logger.error(f"Error parsing Codex session {session_file}: {e}")

        return engrams
