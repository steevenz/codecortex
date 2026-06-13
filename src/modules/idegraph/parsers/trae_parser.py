"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.parsers
:standard: CODDY-IdeGraph-v1.0
@fileoverview TraeParser - Parser for Trae IDE AI interaction data.
"""

import json
import platform
import os
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Any, Dict, Tuple
import sqlite3
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class TraeParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "trae"

    def find_installations(self) -> List[Path]:
        system = platform.system()
        home = Path.home()
        locations = []
        trae_patterns = ['trae', '.trae', 'Trae']

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
            for pattern in trae_patterns:
                trae_dir = base_dir / pattern
                if trae_dir.exists():
                    locations.append(trae_dir)

        dot_trae_dir = self._detect_dot_trae_dir(system=system, home=home)
        if dot_trae_dir is not None:
            locations.append(dot_trae_dir)

        return list(set(locations))

    def find_dot_trae_support_files(
        self,
        *,
        max_depth: int = 4,
        max_files: int = 200,
        max_bytes_per_file: int = 1024 * 1024,
    ) -> Dict[str, str]:
        """
        Discover and read Trae-related support/config files from the user's .trae directory.

        Path rules:
        - Unix/macOS: ~/.trae
        - Windows: %USERPROFILE%\\.trae (fallback to Path.home()\\.trae if USERPROFILE is missing)

        Behaviour:
        - Returns a mapping of absolute file path -> decoded text content for successfully read files.
        - Traverses the directory tree up to max_depth and stops after max_files successfully read files.
        - Skips likely-binary files and truncates reads to max_bytes_per_file to avoid huge artifacts.
        - Handles missing directories (returns empty dict) and permission errors (logs warning and continues).
        - Never logs file contents.
        """
        system = platform.system()
        home = Path.home()
        dot_trae_dir = self._detect_dot_trae_dir(system=system, home=home)
        if dot_trae_dir is None:
            return {}

        candidates = self._discover_files_under_dir(
            root_dir=dot_trae_dir,
            max_depth=max_depth,
            max_files=max_files,
        )

        results: Dict[str, str] = {}
        for p in candidates:
            content = self._read_text_file_gracefully(p, max_bytes=max_bytes_per_file)
            if content is None:
                continue
            results[str(p)] = content

            if len(results) >= max_files:
                break

        return results

    def _detect_dot_trae_dir(self, *, system: str, home: Path) -> Optional[Path]:
        if system == "Windows":
            userprofile = os.environ.get("USERPROFILE")
            base = Path(userprofile) if userprofile else home
            candidate = base / ".trae"
        else:
            candidate = home / ".trae"

        try:
            if candidate.exists() and candidate.is_dir():
                return candidate
        except PermissionError as e:
            logger.warning(f"Permission denied accessing Trae support directory: {candidate} ({e})")
            return None
        except OSError as e:
            logger.warning(f"Error accessing Trae support directory: {candidate} ({e})")
            return None

        return None

    def _discover_files_under_dir(
        self,
        *,
        root_dir: Path,
        max_depth: int,
        max_files: int,
    ) -> List[Path]:
        allow_ext = {".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".txt", ".md", ".log"}

        discovered: List[Path] = []
        queue: List[Tuple[Path, int]] = [(root_dir, 0)]

        while queue and len(discovered) < max_files:
            current, depth = queue.pop(0)
            if depth > max_depth:
                continue

            try:
                entries = list(current.iterdir())
            except PermissionError as e:
                logger.warning(f"Permission denied traversing: {current} ({e})")
                continue
            except OSError as e:
                logger.warning(f"Error traversing: {current} ({e})")
                continue

            for entry in entries:
                if len(discovered) >= max_files:
                    break

                try:
                    if entry.is_dir():
                        queue.append((entry, depth + 1))
                        continue

                    if not entry.is_file():
                        continue
                except PermissionError as e:
                    logger.warning(f"Permission denied accessing: {entry} ({e})")
                    continue
                except OSError as e:
                    logger.warning(f"Error accessing: {entry} ({e})")
                    continue

                if entry.suffix.lower() not in allow_ext:
                    continue

                discovered.append(entry)

        return discovered

    def _read_text_file_gracefully(self, path: Path, *, max_bytes: int) -> Optional[str]:
        try:
            data = path.read_bytes()
        except PermissionError as e:
            logger.warning(f"Permission denied reading: {path} ({e})")
            return None
        except OSError as e:
            logger.warning(f"Error reading: {path} ({e})")
            return None

        if not data:
            return ""

        if len(data) > max_bytes:
            data = data[:max_bytes]

        if b"\x00" in data[:1024]:
            return None

        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")

    def parse_all(self) -> List[Engram]:
        all_engrams: List[Engram] = []

        all_engrams.extend(self._parse_local_outputs())

        installations = self.find_installations()
        for inst in installations:
            all_engrams.extend(self._parse_installation(inst))

        if installations:
            support_files = self.find_dot_trae_support_files(max_depth=3, max_files=500)
            if support_files:
                artifact_msgs = []
                for filepath, content in support_files.items():
                    if content and len(content) > 20:
                        artifact_msgs.append(Message(
                            role="system",
                            content=f"trae_support_file:{filepath}",
                            timestamp=datetime.now().isoformat(),
                            metadata={"support_file": filepath, "size": len(content)},
                        ))
                if artifact_msgs:
                    for batch_start in range(0, len(artifact_msgs), 100):
                        batch = artifact_msgs[batch_start:batch_start + 100]
                        stable_seed = f"trae|support_files|{batch_start}".encode("utf-8", errors="ignore")
                        all_engrams.append(Engram(
                            id=hashlib.sha256(stable_seed).hexdigest(),
                            source=self.ide_name,
                            source_file=".trae",
                            messages=batch,
                            title=f"Trae support files ({batch_start}-{batch_start + len(batch)})",
                            metadata={"artifact_type": "trae_support_files", "count": len(batch)},
                            ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installations[0]),
                        ))

        return all_engrams

    def _parse_local_outputs(self) -> List[Engram]:
        """
        Parse Trae artifacts written to the SideCortex workspace itself.

        Primary source on Trae: outputs/history.json (prompt history with file/folder references).
        This is treated as first-class ingestion so IDE exports can include Trae sessions even when
        Trae internal storage uses non-SQLite formats.
        """
        cwd_root: Optional[Path] = None
        try:
            cwd_root = Path.cwd()
        except Exception:
            cwd_root = None

        if cwd_root:
            cwd_outputs = cwd_root / "outputs"
            history_path = cwd_outputs / "history.json"
            if history_path.exists():
                return self._parse_history_json(history_path, cwd_outputs)

        try:
            repo_root = Path(__file__).resolve().parents[2]
        except Exception:
            return []

        repo_outputs = repo_root / "outputs"
        history_path = repo_outputs / "history.json"
        if history_path.exists():
            return self._parse_history_json(history_path, repo_outputs)

        return []

    def _parse_history_json(self, history_path: Path, installation: Path) -> List[Engram]:
        try:
            raw = history_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception as e:
            logger.error(f"Error parsing Trae history.json {history_path}: {e}")
            return []

        if not isinstance(data, list) or not data:
            return []

        base_time = datetime.fromtimestamp(history_path.stat().st_mtime)
        engrams: List[Engram] = []

        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                continue

            input_text = item.get("inputText")
            if not isinstance(input_text, str) or not input_text.strip():
                continue

            parsed_query = item.get("parsedQuery", [])
            multimedia = item.get("multiMedia", [])

            code_context = self._extract_code_context_from_parsed_query(parsed_query)
            project_path = self._infer_project_path_from_code_context(code_context)

            stable_seed = f"trae-history|{history_path}|{idx}|{input_text}".encode("utf-8", errors="ignore")
            engram_id = hashlib.sha256(stable_seed).hexdigest()

            created_at = base_time + timedelta(seconds=idx)

            title = input_text.strip().replace("\n", " ")
            if len(title) > 120:
                title = title[:117] + "..."

            messages = [
                Message(
                    role="user",
                    content=input_text,
                    timestamp=created_at.isoformat(),
                    code_context=code_context,
                    metadata={
                        "parsed_query": self._sanitize_parsed_query(parsed_query),
                        "multi_media": multimedia if isinstance(multimedia, list) else [],
                        "history_index": idx,
                    },
                )
            ]

            engrams.append(
                Engram(
                    id=engram_id,
                    source=self.ide_name,
                    source_file=str(history_path),
                    messages=messages,
                    created_at=created_at,
                    workspace_id=project_path,
                    project_path=project_path,
                    title=title,
                    metadata={
                        "artifact_type": "trae_history",
                        "outputs_dir": str(installation),
                    },
                    ide_info=self._build_ide_info(ide_type="ide", installation_path=installation),
                )
            )

        return engrams

    def _infer_project_path_from_code_context(self, code_context: List[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(code_context, list) or not code_context:
            return None

        candidate: Optional[str] = None
        for item in code_context:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if isinstance(path, str) and path and "\x00" not in path:
                candidate = path
                break

        if not candidate:
            return None

        try:
            p = Path(candidate)
            if p.suffix:
                p = p.parent
            root = self._detect_project_root(p)
            return str(root) if root is not None else str(p)
        except Exception:
            return None

    def _extract_code_context_from_parsed_query(self, parsed_query: Any) -> List[Dict[str, Any]]:
        if not isinstance(parsed_query, list):
            return []

        ctx: List[Dict[str, Any]] = []
        for part in parsed_query:
            if not isinstance(part, dict):
                continue

            file_path = part.get("filePath")
            folder_path = part.get("folderPath")

            if isinstance(file_path, str) and file_path:
                ctx.append(
                    {
                        "type": "file",
                        "path": file_path,
                        "name": part.get("name"),
                        "relate_path": part.get("relatePath"),
                    }
                )
            elif isinstance(folder_path, str) and folder_path:
                ctx.append(
                    {
                        "type": "folder",
                        "path": folder_path,
                        "name": part.get("name"),
                        "relate_path": part.get("relatePath"),
                    }
                )

        return ctx

    def _sanitize_parsed_query(self, parsed_query: Any) -> List[Dict[str, Any]]:
        if not isinstance(parsed_query, list):
            return []

        sanitized: List[Dict[str, Any]] = []
        for part in parsed_query:
            if not isinstance(part, dict):
                continue

            entry: Dict[str, Any] = {
                "type": part.get("type"),
                "name": part.get("name"),
                "relatePath": part.get("relatePath"),
            }

            if isinstance(part.get("filePath"), str):
                entry["filePath"] = part.get("filePath")
            if isinstance(part.get("folderPath"), str):
                entry["folderPath"] = part.get("folderPath")

            sanitized.append(entry)

        return sanitized

    def _parse_installation(self, installation: Path) -> List[Engram]:
        engrams = []

        # 1. Check for JSONL files in projects directory
        projects_dir = installation / 'projects'
        if projects_dir.exists():
            for project in projects_dir.iterdir():
                if project.is_dir():
                    for jsonl_file in project.glob('*.jsonl'):
                        engrams.extend(self._parse_jsonl(jsonl_file, installation))

        # 2. Check for SQLite databases
        for db_file in installation.rglob('*.db'):
            engrams.extend(self._parse_db_like(db_file, installation))

        for vscdb_file in installation.rglob('*.vscdb'):
            engrams.extend(self._parse_db_like(vscdb_file, installation))

        # 3. Check for sessions directory
        sessions_dir = installation / 'sessions'
        if sessions_dir.exists():
            for jsonl_file in sessions_dir.rglob('*.jsonl'):
                engrams.extend(self._parse_jsonl(jsonl_file, installation))

        return engrams

    def _parse_db_like(self, db_file: Path, installation: Path) -> List[Engram]:
        header = b""
        try:
            header = db_file.read_bytes()[:16]
        except Exception:
            header = b""

        if header == b"SQLite format 3\x00":
            return self._parse_sqlite(db_file, installation)

        return self._artifact_engram(
            source_file=str(db_file),
            installation=installation,
            artifact_type="trae_db_unknown_format",
            details={
                "file_name": db_file.name,
                "suffix": db_file.suffix,
                "size_bytes": self._safe_stat_size(db_file),
                "header_hex": header.hex() if header else None,
            },
        )

    def _artifact_engram(self, *, source_file: str, installation: Path, artifact_type: str, details: Dict[str, Any]) -> List[Engram]:
        stable_seed = f"trae|artifact|{source_file}|{artifact_type}".encode("utf-8", errors="ignore")
        engram_id = hashlib.sha256(stable_seed).hexdigest()
        created_at = datetime.now()
        msg = Message(role="assistant", content="artifact_captured", timestamp=created_at.isoformat(), metadata={"artifact_type": artifact_type})
        return [
            Engram(
                id=engram_id,
                source=self.ide_name,
                source_file=source_file,
                messages=[msg],
                created_at=created_at,
                metadata={"artifact_type": artifact_type, "details": details},
                ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
            )
        ]

    def _parse_jsonl(self, jsonl_file: Path, installation: Path) -> List[Engram]:
        messages = []
        metadata = {}
        project_path: Optional[str] = None
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    obj = self._safe_json_loads(line)
                    if not obj: continue

                    msg_type = obj.get('type', obj.get('role'))
                    role = 'user' if msg_type in ['user', 'user_message'] else 'assistant'

                    if msg_type in ['user', 'user_message', 'assistant', 'agent', 'agent_message']:
                        content = self._normalize_message_content(obj.get('message') or obj.get('content') or '')
                        messages.append(Message(
                            role=role,
                            content=content,
                            timestamp=obj.get('timestamp'),
                            code_context=obj.get('context', obj.get('files', [])),
                            tool_use=obj.get('tool_use', []),
                            diffs=obj.get('diffs', obj.get('edits', []))
                        ))
                        cwd = obj.get('cwd') or obj.get('projectPath') or obj.get('workspace')
                        if isinstance(cwd, str) and not project_path:
                            project_path = cwd
                    elif msg_type == 'metadata':
                        metadata.update(obj.get('data', {}))
                        if not project_path:
                            cwd = obj.get('data', {}).get('cwd') or obj.get('data', {}).get('projectPath')
                            if isinstance(cwd, str):
                                project_path = cwd
                    elif msg_type in ['plan', 'task', 'implementation']:
                        metadata[msg_type] = obj.get('content', obj.get('data', obj))

            if messages:
                resolved = self._detect_project_root(Path(project_path)) if project_path else None
                project_root = str(resolved) if resolved else project_path
                return [Engram(
                    id=str(uuid.uuid4()),
                    source=self.ide_name,
                    source_file=str(jsonl_file),
                    messages=messages,
                    project_path=project_root,
                    workspace_id=project_root,
                    metadata=metadata,
                    ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation)
                )]
        except Exception as e:
            logger.error(f"Error parsing JSONL {jsonl_file}: {e}")
        return []

    def _parse_sqlite(self, db_file: Path, installation: Path) -> List[Engram]:
        known_keys = [
            "memento/icube-ai-agent-storage",
            "chat.ChatSessionStore.index",
            "ChatStore",
            "memento/icube-ai-chat-storage-7467774676505887760",
            "memento/icube-ai-ng-chat-storage-7467774676505887760",
        ]

        workspace_id = db_file.parent.name
        workspace_folder = self._read_workspace_folder(db_file.parent / "workspace.json")

        out: List[Engram] = []

        out.extend(
            self._parse_state_vscdb_chat_store(
            db_file=db_file,
            installation=installation,
            workspace_id=workspace_id,
            workspace_folder=workspace_folder,
            known_keys=known_keys,
        )
        )

        out.extend(
            self._parse_vscdb_input_history(
                db_file=db_file,
                installation=installation,
                workspace_id=workspace_id,
                workspace_folder=workspace_folder,
            )
        )

        out.extend(
            self._parse_vscdb_agent_state(
                db_file=db_file,
                installation=installation,
                workspace_id=workspace_id,
                workspace_folder=workspace_folder,
            )
        )

        best_effort = self._parse_sqlite_any_kv(
            db_file=db_file,
            installation=installation,
            workspace_id=workspace_id,
            workspace_folder=workspace_folder,
        )
        out.extend(best_effort)

        if out:
            return out

        return self._artifact_engram(
            source_file=str(db_file),
            installation=installation,
            artifact_type="trae_sqlite_unparsed",
            details={
                "workspace_id": workspace_id,
                "workspace_folder": workspace_folder,
                "tables": self._sqlite_list_tables(db_file),
            },
        )

    def _parse_vscdb_input_history(
        self,
        *,
        db_file: Path,
        installation: Path,
        workspace_id: str,
        workspace_folder: Optional[str],
    ) -> List[Engram]:
        rows = self._read_sqlite(db_file, "SELECT value FROM ItemTable WHERE [key] = ? LIMIT 1", ("icube-ai-agent-storage-input-history",))
        if not rows:
            return []

        raw_value = rows[0][0]
        data = self._safe_json_loads(raw_value)
        if not isinstance(data, list) or not data:
            return []

        base_time = datetime.fromtimestamp(db_file.stat().st_mtime)
        engrams: List[Engram] = []

        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            input_text = item.get("inputText")
            if not isinstance(input_text, str) or not input_text.strip():
                continue

            parsed_query_raw = item.get("parsedQuery", [])
            parsed_query = [p for p in parsed_query_raw if isinstance(p, dict)] if isinstance(parsed_query_raw, list) else []
            code_context = self._extract_code_context_from_parsed_query(parsed_query)
            project_path = self._infer_project_path_from_code_context(code_context) or workspace_folder

            stable_seed = f"trae|input_history|{db_file}|{idx}|{input_text}".encode("utf-8", errors="ignore")
            engram_id = hashlib.sha256(stable_seed).hexdigest()
            created_at = base_time + timedelta(seconds=idx)

            title = input_text.strip().replace("\n", " ")
            if len(title) > 120:
                title = title[:117] + "..."

            messages = [
                Message(
                    role="user",
                    content=input_text,
                    timestamp=created_at.isoformat(),
                    code_context=code_context,
                    metadata={
                        "parsed_query": self._sanitize_parsed_query(parsed_query_raw),
                        "multi_media": item.get("multiMedia", []) if isinstance(item.get("multiMedia"), list) else [],
                        "history_index": idx,
                        "artifact_type": "trae_input_history",
                        "source_key": "icube-ai-agent-storage-input-history",
                    },
                )
            ]

            engrams.append(
                Engram(
                    id=engram_id,
                    source=self.ide_name,
                    source_file=str(db_file),
                    messages=messages,
                    created_at=created_at,
                    workspace_id=project_path or workspace_id,
                    project_path=project_path,
                    title=title,
                    metadata={
                        "artifact_type": "trae_input_history",
                        "workspace_storage_id": workspace_id,
                    },
                    ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
                )
            )

        return engrams

    def _parse_vscdb_agent_state(
        self,
        *,
        db_file: Path,
        installation: Path,
        workspace_id: str,
        workspace_folder: Optional[str],
    ) -> List[Engram]:
        rows = self._read_sqlite(
            db_file,
            "SELECT [key], value FROM ItemTable WHERE [key] = ? OR [key] = ? OR [key] LIKE ? LIMIT 50",
            ("memento/icube-ai-agent-storage", "icube_session_agent_map", "currentAgentData_%"),
        )
        if not rows:
            return []

        details: Dict[str, Any] = {"keys": []}
        session_ids: List[str] = []
        current_session_id: Optional[str] = None

        for k, v in rows:
            if not isinstance(k, str):
                continue
            details["keys"].append(k)
            obj = self._safe_json_loads(v)
            if k == "memento/icube-ai-agent-storage" and isinstance(obj, dict):
                current_session_id = obj.get("currentSessionId") if isinstance(obj.get("currentSessionId"), str) else None
                lst = obj.get("list")
                if isinstance(lst, list):
                    for it in lst:
                        if isinstance(it, dict) and isinstance(it.get("sessionId"), str):
                            session_ids.append(it["sessionId"])
            if k.startswith("currentAgentData_") and isinstance(obj, dict):
                details["current_agent"] = {
                    "agent_id": obj.get("agent_id"),
                    "user_id": obj.get("user_id"),
                    "name": obj.get("name"),
                    "unique_name": obj.get("unique_name"),
                    "description": obj.get("description"),
                    "type": obj.get("type"),
                    "mcp_list_count": len(obj.get("mcp_list")) if isinstance(obj.get("mcp_list"), list) else 0,
                    "built_in_tool_list_count": len(obj.get("built_in_tool_list")) if isinstance(obj.get("built_in_tool_list"), list) else 0,
                    "prompt_sha256": hashlib.sha256((obj.get("prompt") or "").encode("utf-8", errors="ignore")).hexdigest()
                    if isinstance(obj.get("prompt"), str)
                    else None,
                }

        stable_seed = f"trae|agent_state|{db_file}".encode("utf-8", errors="ignore")
        engram_id = hashlib.sha256(stable_seed).hexdigest()
        created_at = datetime.fromtimestamp(db_file.stat().st_mtime)

        msg = Message(
            role="assistant",
            content="artifact_agent_state_captured",
            timestamp=created_at.isoformat(),
            metadata={
                "artifact_type": "trae_agent_state",
                "workspace_storage_id": workspace_id,
                "current_session_id": current_session_id,
                "session_ids_count": len(set(session_ids)),
            },
        )

        return [
            Engram(
                id=engram_id,
                source=self.ide_name,
                source_file=str(db_file),
                messages=[msg],
                created_at=created_at,
                workspace_id=workspace_folder or workspace_id,
                project_path=workspace_folder,
                title="Trae agent state",
                metadata={"artifact_type": "trae_agent_state", "details": details},
                ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
            )
        ]

    @staticmethod
    def _quote_sqlite_identifier(name: str) -> str:
        return '"' + name.replace('"', '""') + '"'

    def _sqlite_table_columns(self, conn: sqlite3.Connection, table: str) -> List[str]:
        try:
            rows = conn.execute(f"PRAGMA table_info({self._quote_sqlite_identifier(table)})").fetchall()
            cols = []
            for r in rows:
                if len(r) >= 2 and isinstance(r[1], str):
                    cols.append(r[1])
            return cols
        except Exception:
            return []

    def _parse_sqlite_any_kv(
        self,
        *,
        db_file: Path,
        installation: Path,
        workspace_id: str,
        workspace_folder: Optional[str],
    ) -> List[Engram]:
        try:
            conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
            try:
                conn.row_factory = sqlite3.Row
                tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                if not tables:
                    return []

                candidates: List[Tuple[str, str, str]] = []
                for t in tables:
                    if isinstance(t, str) and t.lower() == "itemtable":
                        continue
                    cols = self._sqlite_table_columns(conn, t)
                    lower = {c.lower(): c for c in cols}
                    key_col = lower.get("key") or lower.get("k") or lower.get("name")
                    value_col = lower.get("value") or lower.get("v") or lower.get("data") or lower.get("json")
                    if key_col and value_col:
                        candidates.append((t, key_col, value_col))

                if not candidates:
                    return []

                out: List[Engram] = []
                for table, key_col, value_col in candidates:
                    try:
                        qt = self._quote_sqlite_identifier(table)
                        qk = self._quote_sqlite_identifier(key_col)
                        qv = self._quote_sqlite_identifier(value_col)
                        rows = conn.execute(f"SELECT {qk} AS k, {qv} AS v FROM {qt} LIMIT 5000").fetchall()
                    except Exception:
                        continue

                    for r in rows:
                        key = r["k"] if isinstance(r, sqlite3.Row) else (r[0] if r else None)
                        value = r["v"] if isinstance(r, sqlite3.Row) else (r[1] if len(r) > 1 else None)
                        if key is None:
                            continue
                        if not isinstance(value, str):
                            continue
                        data = self._safe_json_loads(value)
                        if data is None:
                            continue

                        if isinstance(data, dict) and self._looks_like_chat_store(data):
                            out.extend(
                                self._engrams_from_chat_store(
                                    db_file=db_file,
                                    installation=installation,
                                    workspace_id=workspace_id,
                                    workspace_folder=workspace_folder,
                                    used_key=f"{table}.{key}",
                                    store=data,
                                )
                            )
                            continue

                        if isinstance(data, dict):
                            messages_data = data.get("messages", data.get("conversation", []))
                            if isinstance(messages_data, list) and messages_data:
                                messages: List[Message] = []
                                for m in messages_data:
                                    if isinstance(m, dict) and "role" in m:
                                        messages.append(
                                            Message(
                                                role=str(m.get("role", "unknown")),
                                                content=self._normalize_message_content(m.get("content", m.get("text", ""))),
                                                timestamp=m.get("timestamp"),
                                                metadata={kk: vv for kk, vv in m.items() if kk not in ["role", "content", "text", "timestamp"]},
                                            )
                                        )
                                if messages:
                                    stable_seed = f"trae|kv|{db_file}|{table}|{key}".encode("utf-8", errors="ignore")
                                    engram_id = hashlib.sha256(stable_seed).hexdigest()
                                    out.append(
                                        Engram(
                                            id=engram_id,
                                            source=self.ide_name,
                                            source_file=str(db_file),
                                            messages=messages,
                                            workspace_id=workspace_id,
                                            project_path=workspace_folder,
                                            title=data.get("title", data.get("name")),
                                            metadata={"artifact_type": "trae_kv_blob", "kv_table": table, "kv_key": str(key)},
                                            ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
                                        )
                                    )
                return out
            finally:
                conn.close()
        except Exception:
            return []

    def _parse_state_vscdb_chat_store(
        self,
        *,
        db_file: Path,
        installation: Path,
        workspace_id: str,
        workspace_folder: Optional[str],
        known_keys: List[str],
    ) -> List[Engram]:
        for k in known_keys:
            rows = self._read_sqlite(db_file, "SELECT value FROM ItemTable WHERE [key] = ? LIMIT 1", (k,))
            if not rows:
                continue

            raw_value = rows[0][0]
            store = self._safe_json_loads(raw_value)
            if not store:
                continue

            if not isinstance(store, (dict, list)):
                continue

            return self._engrams_from_chat_store(
                db_file=db_file,
                installation=installation,
                workspace_id=workspace_id,
                workspace_folder=workspace_folder,
                used_key=k,
                store=store,
            )

        return []

    def _looks_like_chat_store(self, store: Dict[str, Any]) -> bool:
        if "sessions" in store or "conversations" in store or "entries" in store:
            return True
        if "list" in store and isinstance(store.get("list"), list):
            return True
        return False

    def _engrams_from_chat_store(
        self,
        *,
        db_file: Path,
        installation: Path,
        workspace_id: str,
        workspace_folder: Optional[str],
        used_key: str,
        store: Any,
    ) -> List[Engram]:
        sessions = self._extract_sessions_from_store(used_key=used_key, store=store)
        if not sessions:
            return []

        engrams: List[Engram] = []
        for idx, session in enumerate(sessions):
            if not isinstance(session, dict):
                continue

            session_id = session.get("sessionId") or session.get("id") or f"idx-{idx}"
            title = session.get("title") or session.get("name") or f"Chat {str(session_id)[:8]}"

            created_at = self._parse_session_timestamp(session.get("createdAt") or session.get("timestamp"))
            updated_at = self._parse_session_timestamp(session.get("updatedAt"))
            engram_time = updated_at or created_at or datetime.now()

            messages = self._messages_from_session(session)
            if not messages:
                continue

            stable_seed = f"trae|{db_file}|{used_key}|{session_id}".encode("utf-8", errors="ignore")
            engram_id = hashlib.sha256(stable_seed).hexdigest()

            engrams.append(
                Engram(
                    id=engram_id,
                    source=self.ide_name,
                    source_file=str(db_file),
                    messages=messages,
                    created_at=engram_time,
                    workspace_id=workspace_id,
                    project_path=workspace_folder,
                    title=str(title) if title is not None else None,
                    metadata={
                        "artifact_type": "trae_chat_store",
                        "store_key": used_key,
                        "session_id": str(session_id),
                        "created_at_raw": session.get("createdAt") or session.get("timestamp"),
                        "updated_at_raw": session.get("updatedAt"),
                        "type": session.get("type"),
                    },
                    ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
                )
            )

        return engrams

    def _extract_sessions_from_store(self, *, used_key: str, store: Any) -> List[Any]:
        if used_key == "memento/icube-ai-agent-storage":
            if isinstance(store, dict) and isinstance(store.get("list"), list):
                return store["list"]
            return []

        if isinstance(store, dict):
            if isinstance(store.get("sessions"), dict):
                return list(store["sessions"].values())
            if isinstance(store.get("conversations"), dict):
                return list(store["conversations"].values())
            if isinstance(store.get("entries"), dict):
                return list(store["entries"].values())
            if isinstance(store.get("list"), list):
                return store["list"]

        if isinstance(store, list):
            return store

        return []

    def _messages_from_session(self, session: Dict[str, Any]) -> List[Message]:
        raw_messages = session.get("messages")
        if not isinstance(raw_messages, list) or not raw_messages:
            return []

        out: List[Message] = []
        for m in raw_messages:
            if not isinstance(m, dict):
                continue

            role = m.get("role") or m.get("type") or "unknown"
            content = self._normalize_message_content(m.get("content", m.get("text", m.get("message", ""))))
            if not content:
                continue

            out.append(
                Message(
                    role=str(role),
                    content=content,
                    timestamp=m.get("timestamp"),
                    metadata={k: v for k, v in m.items() if k not in ["role", "type", "content", "text", "message", "timestamp"]},
                    code_context=m.get("context", m.get("files", [])) if isinstance(m.get("context", m.get("files", [])), list) else [],
                    tool_use=m.get("toolUse", m.get("tool_use", [])) if isinstance(m.get("toolUse", m.get("tool_use", [])), list) else [],
                    diffs=m.get("diffs", m.get("edits", [])) if isinstance(m.get("diffs", m.get("edits", [])), list) else [],
                )
            )

        return out

    def _normalize_message_content(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, dict):
            for k in ("data", "summary", "content", "text", "message"):
                v = value.get(k) if isinstance(value.get(k), (str, int, float, bool)) else None
                if v is not None:
                    return str(v)
            try:
                return json.dumps(value, ensure_ascii=False)
            except Exception:
                return str(value)
        if isinstance(value, list):
            try:
                return "\n".join([self._normalize_message_content(v) for v in value if v is not None])
            except Exception:
                return str(value)
        return str(value)

    def _parse_session_timestamp(self, raw: Any) -> Optional[datetime]:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            ts = float(raw)
            if ts > 1e12:
                ts = ts / 1000.0
            try:
                return datetime.fromtimestamp(ts)
            except Exception:
                return None
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw)
            except Exception:
                return None
        return None

    def _read_workspace_folder(self, workspace_json_path: Path) -> Optional[str]:
        try:
            if not workspace_json_path.exists():
                return None
        except Exception:
            return None

        try:
            data = json.loads(workspace_json_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        folder = data.get("folder")
        if not isinstance(folder, str):
            return None
        try:
            p = Path(folder)
            root = self._detect_project_root(p) if p else None
            return str(root) if root is not None else folder
        except Exception:
            return folder
