"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.parsers
:standard: CODDY-IdeGraph-v1.0
@fileoverview WindsurfParser - Parser for Windsurf IDE AI interaction data.
"""

import json
import platform
import os
import uuid
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterable, Tuple
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class WindsurfParser(BaseIDEParser):
    """Parser for Windsurf IDE data (Chat and Agent/Flow)."""

    @property
    def ide_name(self) -> str:
        return "windsurf"

    def find_installations(self) -> List[Path]:
        system = platform.system()
        home = Path.home()
        locations = []

        patterns = ['Windsurf', 'windsurf', '.windsurf']

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
            workspace_storage = inst / "User/workspaceStorage"
            if workspace_storage.exists():
                for workspace in workspace_storage.iterdir():
                    if not workspace.is_dir():
                        continue
                    if workspace.name == "ext-dev":
                        continue

                    db_file = workspace / "state.vscdb"
                    if db_file.exists():
                        ws_engrams = self._parse_chat_db(db_file, workspace.name, inst)
                        if not ws_engrams:
                            ws_engrams.extend(self._artifact_db_summary(db_file=db_file, installation=inst, workspace_id=workspace.name))
                        all_engrams.extend(ws_engrams)

                    for extra_db in self._iter_db_files(workspace):
                        if extra_db.name == "state.vscdb":
                            continue
                        all_engrams.extend(self._artifact_any_db_file(db_file=extra_db, installation=inst, workspace_id=workspace.name))

            global_db = inst / "User/globalStorage/state.vscdb"
            if global_db.exists():
                global_engrams = self._parse_global_db(global_db, inst)
                if not global_engrams:
                    global_engrams.extend(self._artifact_db_summary(db_file=global_db, installation=inst, workspace_id="global"))
                all_engrams.extend(global_engrams)

            if not workspace_storage.exists() and not global_db.exists():
                for db_file in self._iter_db_files(inst):
                    all_engrams.extend(self._artifact_any_db_file(db_file=db_file, installation=inst, workspace_id="installation"))

        return all_engrams

    def _parse_chat_db(self, db_path: Path, workspace_id: str, installation: Path) -> List[Engram]:
        engrams = []
        keys_to_try = [
            'workbench.panel.aichat.view.aichat.chatdata',
            'aiChat.chatdata',
            'chat.data',
            'cascade.chatdata'
        ]

        ws_path = self._extract_workspace_path(db_path=db_path, workspace_id=workspace_id)

        for _, value in self._iter_chatdata_records(db_path, keys_to_try):
            data = self._safe_json_loads(value)
            if not data or not isinstance(data, dict) or "tabs" not in data:
                continue

            for tab in data.get("tabs") or []:
                if not isinstance(tab, dict):
                    continue
                bubbles = tab.get("bubbles") or []
                if not bubbles or not isinstance(bubbles, list):
                    continue

                messages: List[Message] = []
                inferred_path: Optional[str] = None
                for bubble in bubbles:
                    if not isinstance(bubble, dict):
                        continue

                    role = "user" if bubble.get("type") == "user" else "assistant"
                    content = bubble.get("rawText") or bubble.get("text") or ""
                    msg = Message(role=role, content=str(content))

                    selections = bubble.get("selections") or []
                    if isinstance(selections, list) and selections:
                        for sel in selections:
                            if not isinstance(sel, dict):
                                continue
                            uri = sel.get("uri")
                            if isinstance(uri, dict) and isinstance(uri.get("fsPath"), str):
                                fp = uri["fsPath"]
                                msg.code_context.append(
                                    {
                                        "file": fp,
                                        "code": sel.get("text", sel.get("rawText", "")),
                                        "range": sel.get("range"),
                                    }
                                )
                                if inferred_path is None:
                                    inferred_path = self._normalize_project_path(Path(fp).parent)

                    if isinstance(bubble.get("suggestedDiffs"), list):
                        msg.diffs = bubble.get("suggestedDiffs") or []

                    messages.append(msg)

                project_path = ws_path or inferred_path
                if messages:
                    engrams.append(
                        Engram(
                            id=str(tab.get("tabId") or uuid.uuid4()),
                            source=self.ide_name,
                            source_file=str(db_path),
                            messages=messages,
                            workspace_id=workspace_id,
                            project_path=project_path,
                            project_name=Path(project_path).name if project_path else None,
                            title=tab.get("chatTitle"),
                            metadata={"windsurf_type": "chat", "tab_id": tab.get("tabId")},
                            ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
                        )
                    )
        return engrams

    def _parse_global_db(self, db_path: Path, installation: Path) -> List[Engram]:
        engrams = []

        engrams.extend(self._extract_windsurf_modern_sessions(db_path, installation))

        query = "SELECT key, value FROM ItemTable WHERE key LIKE '%agent%' OR key LIKE '%flow%' OR key LIKE '%cascade%'"
        results = self._read_sqlite(db_path, query)

        for key, value in results:
            data = self._safe_json_loads(value)
            if not data or not isinstance(data, dict):
                continue

            engram = self._extract_agent_conversation(data, key, db_path, installation, workspace_id="global")
            if engram:
                engrams.append(engram)

        kv_query = "SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%' OR key LIKE 'agentData:%' OR key LIKE 'flowData:%'"
        kv_results = self._read_sqlite(db_path, kv_query)
        for key, value in kv_results:
            data = self._safe_json_loads(value)
            if data:
                engram = self._extract_agent_conversation(data, key, db_path, installation, workspace_id="global")
                if engram:
                    engrams.append(engram)

        return engrams

    def _extract_windsurf_modern_sessions(self, db_path: Path, installation: Path) -> List[Engram]:
        engrams = []
        summaries = self._read_sqlite(db_path, "SELECT key, value FROM ItemTable WHERE key LIKE 'windsurf.acp.session/summaryState/%'")
        for key, value in summaries:
            data = self._safe_json_loads(value)
            if not isinstance(data, dict):
                continue
            msg_count = data.get("messageCount", 0)
            session_id = data.get("prefixedSessionId", key.split("/")[-1])
            if msg_count == 0:
                continue
            msg = Message(
                role="system",
                content=f"Windsurf session with {msg_count} messages (stored server-side)",
                metadata={"message_count": msg_count, "session_id": session_id},
            )
            engrams.append(Engram(
                id=f"windsurf_summary_{session_id}",
                source=self.ide_name,
                source_file=str(db_path),
                messages=[msg],
                title=f"Windsurf session ({msg_count} msgs)",
                metadata={"windsurf_type": "session_summary", "message_count": msg_count},
                ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
            ))
        return engrams

    def _extract_agent_conversation(
        self,
        data: Dict[str, Any],
        key: str,
        db_path: Path,
        installation: Path,
        workspace_id: str,
    ) -> Optional[Engram]:
        if 'conversation' not in data or not isinstance(data['conversation'], list):
            return None

        messages = []
        inferred_path: Optional[str] = None
        for bubble in data['conversation']:
            bubble_type = bubble.get('type')
            role = 'user' if (bubble_type == 1 or bubble.get('role') == 'user') else 'assistant'
            text = bubble.get('text') or bubble.get('rawText') or bubble.get('markdownText') or ''

            msg = Message(role=role, content=text)

            # Context
            if 'context' in bubble and 'selections' in bubble['context']:
                for sel in bubble['context']['selections']:
                    if 'uri' in sel and 'fsPath' in sel['uri']:
                        fp = sel['uri']['fsPath']
                        msg.code_context.append({
                            'file': fp,
                            'code': sel.get('text', sel.get('rawText', '')),
                            'range': sel.get('range')
                        })
                        if inferred_path is None:
                            inferred_path = self._normalize_project_path(Path(fp).parent)

            # Tool Calls and Results
            if 'toolCalls' in bubble:
                msg.tool_use.extend(bubble['toolCalls'])
            if 'toolResults' in bubble:
                msg.metadata['tool_results'] = bubble['toolResults']

            # Code Blocks / Diffs
            if 'suggestedCodeBlocks' in bubble:
                msg.metadata['suggested_code_blocks'] = bubble['suggestedCodeBlocks']
            if 'diffHistories' in bubble:
                msg.diffs = bubble['diffHistories']

            # Plan / Step Info
            if 'step' in bubble:
                msg.metadata['step'] = bubble['step']
            if 'checkpoint' in bubble:
                msg.metadata['checkpoint'] = bubble['checkpoint']

            messages.append(msg)

        if not messages:
            return None

        project_path = self._extract_project_path_from_messages(messages) or inferred_path
        return Engram(
            id=key.split(':')[-1] if ':' in key else str(uuid.uuid4()),
            source=self.ide_name,
            source_file=str(db_path),
            messages=messages,
            workspace_id=workspace_id,
            project_path=project_path,
            project_name=Path(project_path).name if project_path else None,
            title=data.get('name', 'Untitled Agent Session'),
            metadata={
                'windsurf_type': 'agent',
                'status': data.get('status'),
                'original_key': key
            },
            ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation)
        )

    def _iter_db_files(self, directory: Path) -> Iterable[Path]:
        try:
            for p in directory.glob("*.db"):
                if p.is_file():
                    yield p
            for p in directory.glob("*.vscdb"):
                if p.is_file():
                    yield p
            for p in directory.glob("*.sqlite"):
                if p.is_file():
                    yield p
        except Exception:
            return

    def _iter_chatdata_records(self, db_path: Path, keys_to_try: List[str]) -> Iterable[Tuple[str, Any]]:
        for key in keys_to_try:
            for (value,) in self._read_sqlite(db_path, "SELECT value FROM ItemTable WHERE key = ?", (key,)):
                yield key, value
            for _, value in self._read_sqlite(db_path, "SELECT key, value FROM cursorDiskKV WHERE key = ?", (key,)):
                yield key, value

    def _extract_workspace_path(self, *, db_path: Path, workspace_id: str) -> Optional[str]:
        results = self._read_sqlite(db_path, "SELECT value FROM ItemTable WHERE key = 'history.recentlyOpenedPathsList'")
        if results:
            data = self._safe_json_loads(results[0][0])
            if isinstance(data, dict) and isinstance(data.get("entries"), list):
                for entry in data.get("entries") or []:
                    if not isinstance(entry, dict):
                        continue
                    folder_uri = entry.get("folderUri") or (entry.get("workspace") or {}).get("configPath")
                    if not folder_uri or not isinstance(folder_uri, str):
                        continue
                    if folder_uri.startswith("file:///"):
                        raw = folder_uri[8:]
                        p = Path(raw.replace("/", "\\") if platform.system() == "Windows" else raw)
                        return self._normalize_project_path(p)
                    if folder_uri.startswith("file://"):
                        raw = folder_uri[7:]
                        p = Path(raw.replace("/", "\\") if platform.system() == "Windows" else raw)
                        return self._normalize_project_path(p)
                    return self._normalize_project_path(Path(folder_uri))

        ws_dir = db_path.parent
        if ws_dir.name == workspace_id:
            ws_json = ws_dir / "workspace.json"
            if ws_json.exists():
                try:
                    with open(ws_json, "r", encoding="utf-8") as f:
                        ws_data = json.load(f)
                    if isinstance(ws_data, dict):
                        folder = ws_data.get("folder") or ws_data.get("folderUri") or ws_data.get("configPath")
                        if folder and isinstance(folder, str):
                            return self._normalize_project_path(Path(folder))
                except Exception as e:
                    logger.debug(f"Windsurf parse warning: {e}")
        return None

    def _extract_project_path_from_messages(self, messages: List[Message]) -> Optional[str]:
        for msg in messages:
            for ctx in msg.code_context:
                fp = ctx.get("file")
                if fp and isinstance(fp, str):
                    return self._normalize_project_path(Path(fp).parent)
        return None

    def _artifact_db_summary(self, *, db_file: Path, installation: Path, workspace_id: str) -> List[Engram]:
        return self._artifact_any_db_file(db_file=db_file, installation=installation, workspace_id=workspace_id, artifact_type="windsurf_sqlite_unparsed")

    def _artifact_any_db_file(
        self,
        *,
        db_file: Path,
        installation: Path,
        workspace_id: str,
        artifact_type: Optional[str] = None,
    ) -> List[Engram]:
        header = b""
        try:
            header = db_file.read_bytes()[:16]
        except Exception:
            header = b""

        is_sqlite = header == b"SQLite format 3\x00"
        details: Dict[str, Any] = {
            "file_name": db_file.name,
            "suffix": db_file.suffix,
            "size_bytes": self._safe_stat_size(db_file),
            "header_hex": header.hex() if header else None,
            "tables": self._sqlite_list_tables(db_file) if is_sqlite else [],
        }

        final_type = artifact_type or ("windsurf_sqlite" if is_sqlite else "windsurf_db_unknown_format")
        stable_seed = f"windsurf|artifact|{db_file}|{final_type}".encode("utf-8", errors="ignore")
        engram_id = hashlib.sha256(stable_seed).hexdigest()
        created_at = datetime.fromtimestamp(db_file.stat().st_mtime) if db_file.exists() else datetime.now()
        msg = Message(
            role="assistant",
            content="artifact_captured",
            timestamp=created_at.isoformat(),
            metadata={"artifact_type": final_type},
        )

        return [
            Engram(
                id=engram_id,
                source=self.ide_name,
                source_file=str(db_file),
                messages=[msg],
                created_at=created_at,
                workspace_id=workspace_id,
                metadata={"artifact_type": final_type, "details": details},
                ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
            )
        ]
