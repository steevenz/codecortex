"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.parsers
:standard: CODDY-IdeGraph-v1.0
@fileoverview OpenCodeParser - Parser for OpenCode interaction data.
"""

import json
import struct
import platform
import os
import re
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class OpenCodeParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "opencode"

    def find_installations(self) -> List[Path]:
        system = platform.system()
        home = Path.home()
        locations = []

        if system == "Darwin":
            cli_dirs = [home / "Library/Application Support/opencode", Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')) / 'opencode']
        elif system == "Linux":
            cli_dirs = [Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')) / 'opencode']
        elif system == "Windows":
            cli_dirs = [Path(os.environ.get('APPDATA', home / 'AppData/Roaming')) / 'opencode']
        else:
            cli_dirs = [home / '.local/share/opencode']

        for cli_dir in cli_dirs:
            if cli_dir.exists():
                locations.append(cli_dir)

        if system == "Darwin":
            desktop_dirs = [home / "Library/Application Support/ai.opencode.app"]
        elif system == "Linux":
            desktop_dirs = [home / ".local/share/ai.opencode.app"]
        elif system == "Windows":
            apd = Path(os.environ.get('APPDATA', home / 'AppData/Roaming'))
            desktop_dirs = [
                apd / 'ai.opencode.desktop',
                apd / 'ai.opencode.app',
                apd / 'OpenCode',
            ]
        else:
            desktop_dirs = []

        for desktop_dir in desktop_dirs:
            if desktop_dir.exists():
                locations.append(desktop_dir)

        return locations

    def _installation_type(self, path: Path) -> str:
        name = path.name.lower()
        if 'desktop' in name or name == 'opencode':
            return 'desktop'
        return 'cli'

    def parse_all(self) -> List[Engram]:
        installations = self.find_installations()
        all_engrams = []
        for inst_path in installations:
            install_type = self._installation_type(inst_path)
            if install_type == 'cli':
                all_engrams.extend(self._parse_cli_installation(inst_path))
            elif install_type == 'desktop':
                all_engrams.extend(self._parse_desktop_installation(inst_path))
            if not all_engrams:
                all_engrams.extend(self._artifact_fallback(
                    source_file=str(inst_path), installation=inst_path,
                    artifact_type=f"opencode_{install_type}_unparsed",
                ))
        return all_engrams

    def _read_tauri_store(self, dat_file: Path) -> Dict[str, Any]:
        try:
            with open(dat_file, 'rb') as f:
                data = f.read()

            store = {}
            offset = 0
            while offset < len(data):
                if offset + 4 > len(data): break
                key_len = struct.unpack('<I', data[offset:offset+4])[0]
                offset += 4
                if key_len > 10000 or offset + key_len > len(data): break
                key = data[offset:offset+key_len].decode('utf-8', errors='ignore')
                offset += key_len
                if offset + 4 > len(data): break
                value_len = struct.unpack('<I', data[offset:offset+4])[0]
                offset += 4
                if value_len > 1000000 or offset + value_len > len(data): break
                try:
                    value_bytes = data[offset:offset+value_len]
                    value = json.loads(value_bytes.decode('utf-8'))
                    store[key] = value
                except Exception as e:
                    logger.debug(f"OpenCode parse warning: {e}")
                offset += value_len
            return store
        except Exception as e:
            logger.error(f"Error reading Tauri store {dat_file}: {e}")
            return {}

    def _parse_cli_installation(self, installation: Path) -> List[Engram]:
        engrams = []
        message_dir = installation / 'storage' / 'message'
        part_dir = installation / 'storage' / 'part'

        if not message_dir.exists():
            return []

        session_dirs = [d for d in message_dir.iterdir() if d.is_dir() and d.name.startswith('ses_')]

        for session_dir in session_dirs:
            try:
                session_id = session_dir.name
                messages = []
                project_path = None

                session_file = installation / 'storage' / 'session' / 'global' / f'{session_id}.json'
                metadata = {}
                if session_file.exists():
                    session_data = self._safe_json_loads(session_file.read_text(encoding='utf-8'))
                    if session_data:
                        metadata.update(session_data)
                        cwd = session_data.get('cwd') or session_data.get('projectPath') or session_data.get('workspace')
                        if isinstance(cwd, str) and not project_path:
                            project_path = cwd

                message_files = sorted(session_dir.glob('msg_*.json'))
                for msg_file in message_files:
                    msg_data = self._safe_json_loads(msg_file.read_text(encoding='utf-8'))
                    if not msg_data: continue

                    msg_id = msg_data.get('id')
                    role = msg_data.get('role', 'assistant')
                    timestamp = msg_data.get('time', {}).get('created')

                    msg_metadata = {
                        'model': msg_data.get('modelID'),
                        'provider': msg_data.get('providerID'),
                        'agent': msg_data.get('agent'),
                        'mode': msg_data.get('mode'),
                        'tokens': msg_data.get('tokens'),
                        'cost': msg_data.get('cost')
                    }

                    content_parts = []
                    tool_use = []
                    msg_part_dir = part_dir / msg_id
                    if msg_part_dir.exists():
                        part_files = sorted(msg_part_dir.glob('prt_*.json'))
                        for part_file in part_files:
                            part_data = self._safe_json_loads(part_file.read_text(encoding='utf-8'))
                            if not part_data: continue

                            ptype = part_data.get('type')
                            ptext = part_data.get('text', '')

                            if ptype == 'text':
                                content_parts.append(ptext)
                            elif ptype == 'code':
                                lang = part_data.get('language', '')
                                content_parts.append(f"```{lang}\n{ptext}\n```")
                            elif ptype in ('tool', 'tool-call'):
                                state = part_data.get('state', {})
                                tool_use.append(part_data)
                                if 'input' in state:
                                    content_parts.append(f"[Tool Call: {part_data.get('name')}] {state.get('input')}")
                                if 'output' in state:
                                    content_parts.append(f"[Tool Output] {state.get('output')}")

                    cwd = msg_data.get('cwd') or msg_data.get('projectPath')
                    if isinstance(cwd, str) and not project_path:
                        project_path = cwd

                    messages.append(Message(
                        role=role,
                        content='\n'.join(content_parts),
                        timestamp=timestamp,
                        tool_use=tool_use,
                        metadata=msg_metadata
                    ))

                if messages:
                    resolved = self._detect_project_root(Path(project_path)) if project_path else None
                    project_root = str(resolved) if resolved else project_path
                    model = metadata.get('model') or next((m.metadata.get('model') for m in messages if m.metadata.get('model')), None)
                    engrams.append(Engram(
                        id=session_id,
                        source=self.ide_name,
                        source_file=str(session_dir),
                        messages=messages,
                        workspace_id=project_root,
                        project_path=project_root,
                        model=model,
                        metadata=metadata,
                        ide_info=self._build_ide_info(ide_type="cli", installation_path=installation)
                    ))
            except Exception as e:
                logger.error(f"Error parsing OpenCode CLI session {session_dir}: {e}")

        return engrams

    def _parse_desktop_installation(self, installation: Path) -> List[Engram]:
        engrams = []
        dat_files = list(installation.rglob('*.dat'))

        for dat_file in dat_files:
            store = self._read_tauri_store(dat_file)
            for key, value in store.items():
                if not isinstance(value, dict): continue

                messages_raw = value.get('messages', value.get('history', []))
                if not messages_raw: continue

                messages = []
                project_path = None
                for m in messages_raw:
                    content = m.get('content', '')
                    if not content:
                        continue
                    messages.append(Message(
                        role=m.get('role', 'unknown'),
                        content=content,
                        timestamp=m.get('timestamp') or m.get('created_at'),
                        tool_use=m.get('tool_use', m.get('toolUse', [])),
                        code_context=m.get('context', m.get('files', [])),
                    ))
                    cwd = m.get('cwd') or m.get('projectPath') or m.get('workspace')
                    if isinstance(cwd, str) and not project_path:
                        project_path = cwd

                if messages:
                    resolved = self._detect_project_root(Path(project_path)) if project_path else None
                    project_root = str(resolved) if resolved else project_path
                    engrams.append(Engram(
                        id=value.get('session_id', str(uuid.uuid4())),
                        source=self.ide_name,
                        source_file=str(dat_file),
                        messages=messages,
                        workspace_id=project_root,
                        project_path=project_root,
                        title=value.get('title'),
                        metadata={
                            'workspace': value.get('workspace'),
                            'store_key': key
                        },
                        ide_info=self._build_ide_info(ide_type="desktop", installation_path=installation)
                    ))
        return engrams
