"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.parsers
:standard: Aegis-IdeGraph-v1.0
@fileoverview ContinueParser - Parser for Continue AI interaction data.
"""

import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class ContinueParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "continue"

    def find_installations(self) -> List[Path]:
        home = Path.home()
        continue_dir = home / ".continue"
        if continue_dir.exists():
            return [continue_dir]
        return []

    def parse_all(self) -> List[Engram]:
        installations = self.find_installations()
        all_engrams = []
        for inst in installations:
            all_engrams.extend(self._parse_installation(inst))
        return all_engrams

    def _parse_installation(self, installation: Path) -> List[Engram]:
        engrams = []
        sessions_dir = installation / "sessions"

        if not sessions_dir.exists():
            return []

        for session_file in sessions_dir.glob("*.json"):
            if session_file.name == "sessions.json":
                continue

            try:
                content = session_file.read_text(encoding='utf-8')
                data = self._safe_json_loads(content)
                if not data or 'history' not in data:
                    continue

                messages = []
                for item in data['history']:
                    if 'message' not in item:
                        continue

                    msg_data = item['message']
                    role = msg_data.get('role')

                    content_parts = msg_data.get('content', [])
                    if isinstance(content_parts, str):
                        content_text = content_parts
                    elif isinstance(content_parts, list):
                        texts = []
                        for c in content_parts:
                            if isinstance(c, dict):
                                t = c.get('text', '')
                                if c.get('type') == 'code' and t:
                                    t = f"```\n{t}\n```"
                                texts.append(t)
                        content_text = '\n'.join(texts)
                    else:
                        content_text = ''

                    metadata = {}
                    if 'toolCalls' in msg_data:
                        metadata['tool_calls'] = msg_data['toolCalls']
                    if 'reasoning' in item and item['reasoning']:
                        metadata['reasoning'] = item['reasoning'].get('text', '')
                    if 'contextItems' in item and item['contextItems']:
                        metadata['context_items'] = item['contextItems']

                    messages.append(Message(
                        role=role,
                        content=content_text,
                        timestamp=None,
                        metadata=metadata
                    ))

                if messages:
                    workspace_dir = data.get('workspaceDirectory')
                    resolved = self._detect_project_root(Path(workspace_dir)) if workspace_dir else None
                    project_root = str(resolved) if resolved else workspace_dir
                    engrams.append(Engram(
                        id=data.get('sessionId', str(uuid.uuid4())),
                        source=self.ide_name,
                        source_file=str(session_file),
                        messages=messages,
                        workspace_id=project_root,
                        project_path=project_root,
                        title=data.get('title'),
                        metadata={
                            'workspace': workspace_dir
                        },
                        ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation)
                    ))

            except Exception as e:
                logger.error(f"Error parsing Continue session {session_file}: {e}")

        if not engrams:
            engrams.extend(self._artifact_fallback(
                source_file=str(sessions_dir), installation=installation,
                artifact_type="continue_unparsed",
            ))

        return engrams
