"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.parsers
:standard: CODDY-IdeGraph-v1.0
@fileoverview AntigravityParser - Parser for Antigravity IDE interaction data.
"""

import json
import re
import platform
import os
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class AntigravityParser(BaseIDEParser):
    """Parser for Antigravity IDE (parses brain overview logs)."""

    @property
    def ide_name(self) -> str:
        return "antigravity"

    def find_installations(self) -> List[Path]:
        home = Path.home()
        antigravity_path = home / ".gemini" / "antigravity"
        if antigravity_path.exists():
            return [antigravity_path]
        return []

    def parse_all(self) -> List[Engram]:
        all_engrams = []
        installations = self.find_installations()

        for inst in installations:
            brain_dir = inst / 'brain'
            if not brain_dir.exists():
                continue

            for session_dir in brain_dir.iterdir():
                if not session_dir.is_dir() or session_dir.name == 'tempmediaStorage':
                    continue

                overview_file = session_dir / '.system_generated' / 'logs' / 'overview.txt'
                if overview_file.exists():
                    engram = self._parse_overview_file(overview_file, session_dir.name, session_dir)
                    if engram:
                        self._add_artifacts(engram, session_dir)
                        all_engrams.append(engram)
                else:
                    artifact_engram = self._parse_artifact_only_session(session_dir)
                    if artifact_engram:
                        all_engrams.append(artifact_engram)

        return all_engrams

    def _parse_artifact_only_session(self, session_dir: Path) -> Optional[Engram]:
        md_files = sorted(session_dir.glob("*.md"))
        if not md_files:
            return None

        messages = []
        for f in md_files:
            if f.name.endswith(".metadata.json"):
                continue
            try:
                content = f.read_text(encoding="utf-8")
                if content and len(content) > 20:
                    messages.append(Message(
                        role="system",
                        content=f"artifact:{f.name}",
                        timestamp=datetime.now().isoformat(),
                        metadata={"artifact_file": f.name, "size": len(content)},
                    ))
            except Exception:
                continue

        if not messages:
            return None

        stable_seed = f"antigravity|artifact_only|{session_dir.name}".encode("utf-8", errors="ignore")
        return Engram(
            id=hashlib.sha256(stable_seed).hexdigest(),
            source=self.ide_name,
            source_file=str(session_dir),
            messages=messages,
            title=f"Antigravity artifacts {session_dir.name[:8]}",
            metadata={"artifact_type": "antigravity_artifacts", "session_id": session_dir.name, "file_count": len(messages)},
            ide_info=self._build_ide_info(ide_type="web", installation_path=session_dir),
        )

    def _add_artifacts(self, engram: Engram, session_dir: Path):
        artifacts_dir = session_dir / 'artifacts'
        if not artifacts_dir.exists():
            return

        engram.metadata['artifacts'] = {}
        for artifact_file in artifacts_dir.glob("*.md"):
            try:
                content = artifact_file.read_text(encoding='utf-8')
                engram.metadata['artifacts'][artifact_file.name] = content
                if artifact_file.name == 'implementation_plan.md':
                    engram.metadata['implementation_plan'] = content
                elif artifact_file.name == 'task.md':
                    engram.metadata['tasks'] = content
                elif artifact_file.name == 'walkthrough.md':
                    engram.metadata['walkthrough'] = content
            except Exception as e:
                logger.error(f"Error reading artifact {artifact_file}: {e}")

    def _extract_project_path(self, content: str) -> Optional[str]:
        for match in re.finditer(r'@\[([^\]]+)\]', content):
            path_str = match.group(1).strip()
            if path_str.startswith("http"):
                continue
            try:
                p = Path(path_str)
                if p.exists() or p.parent.exists():
                    resolved = self._detect_project_root(p) if p.suffix else self._detect_project_root(p)
                    if resolved:
                        return str(resolved)
                    if p.suffix:
                        return str(p.parent) if p.parent else str(p)
                    return str(p)
            except Exception:
                continue
        return None

    def _parse_overview_file(self, file_path: Path, session_id: str, session_dir: Path) -> Optional[Engram]:
        try:
            messages = []
            project_path = None
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    data = self._safe_json_loads(line)
                    if not data:
                        continue

                    step_type = data.get('type')
                    content = data.get('content', '')

                    if step_type == 'USER_INPUT':
                        messages.append(Message(
                            role='user',
                            content=content,
                            timestamp=data.get('created_at')
                        ))
                        if not project_path:
                            project_path = self._extract_project_path(content)
                    elif step_type in ('PLANNER_RESPONSE', 'FINAL_RESPONSE'):
                        if content:
                            msg = Message(
                                role='assistant',
                                content=content,
                                timestamp=data.get('created_at'),
                            )
                            if 'tool_calls' in data:
                                msg.tool_use.extend(data['tool_calls'])
                            if 'tool_results' in data:
                                msg.metadata['tool_results'] = data['tool_results']
                            messages.append(msg)

            if not messages:
                return None

            resolved = self._detect_project_root(Path(project_path)) if project_path else None
            project_root = str(resolved) if resolved else project_path

            return Engram(
                id=session_id,
                source=self.ide_name,
                source_file=str(file_path),
                messages=messages,
                title=f"Session {session_id[:8]}",
                workspace_id=project_root,
                project_path=project_root,
                ide_info=self._build_ide_info(ide_type="web", installation_path=file_path.parent)
            )

        except Exception as e:
            logger.error(f"Error parsing Antigravity overview {file_path}: {e}")
            return None
