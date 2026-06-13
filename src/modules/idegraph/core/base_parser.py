"""
@project   CodeCortex
@package   modules.idegraph.core
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.core
:standard: CODDY-IdeGraph-v1.0

BaseIDEParser — Abstract base class for all IDE data parsers.
"""

import sqlite3
import json
import uuid
import base64
import hashlib
import gzip
import io
from datetime import datetime
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class BaseIDEParser(ABC):
    """Abstract base class for all IDE data parsers."""

    @property
    @abstractmethod
    def ide_name(self) -> str:
        """The name of the IDE (e.g., 'trae', 'cursor')."""
        pass

    @abstractmethod
    def find_installations(self) -> List[Path]:
        """Find all installation directories for this IDE."""
        pass

    @abstractmethod
    def parse_all(self) -> List[Engram]:
        """Parse all data from all detected installations."""
        pass

    def _build_ide_info(
        self,
        ide_type: str,
        installation_path: Optional[Path] = None,
        version: Optional[str] = None,
    ) -> IDEInfo:
        """Build a canonical IDEInfo for this parser."""
        return IDEInfo(
            name=self.ide_name,
            type=ide_type,
            installation_path=str(installation_path) if installation_path else None,
            version=version,
        )

    def _read_sqlite(self, db_path: Path, query: str, params: tuple = ()) -> List[tuple]:
        """Utility to read from a SQLite database safely."""
        if not db_path.exists():
            return []

        try:
            header = db_path.read_bytes()[:16]
            if header != b"SQLite format 3\x00":
                return []
            # Use read-only mode and URI to avoid locking issues
            conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                results = cursor.fetchall()
                return results
            finally:
                conn.close()
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if "no such table" in msg:
                return []
            logger.error(f"Error reading SQLite {db_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error reading SQLite {db_path}: {e}")
            return []

    def _safe_json_loads(self, value: Any) -> Optional[Any]:
        if value is None:
            return None

        raw: Optional[str] = None
        if isinstance(value, str):
            raw = value
        elif isinstance(value, (bytes, bytearray)):
            try:
                raw = bytes(value).decode("utf-8", errors="ignore")
            except Exception:
                raw = None

        if not raw:
            return None

        raw_stripped = raw.lstrip()

        try:
            return json.loads(raw_stripped)
        except Exception:
            pass

        try:
            if raw_stripped.startswith("H4sI") or raw_stripped.startswith("H4sIA"):
                decoded = base64.b64decode(raw_stripped)
                with gzip.GzipFile(fileobj=io.BytesIO(decoded)) as gz:
                    text = gz.read().decode("utf-8", errors="ignore")
                return json.loads(text)
        except Exception as e:
            logger.debug(f"_safe_json_loads gzip fallback failed for {raw_stripped[:32]}...: {type(e).__name__}: {e}")
            return None

        return None

    _PROJECT_ROOT_MARKERS = [
        "/.agents/contexts/working.md",
        ".git",
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
        "Cargo.toml",
        "go.mod",
        "composer.json",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    ]

    def _detect_project_root(self, path: Path) -> Optional[Path]:
        try:
            p = path.resolve()
        except Exception:
            p = path

        current = p
        parts = [part.lower() for part in current.parts]
        if ".aicoders" in parts:
            idx = max(i for i, part in enumerate(parts) if part == ".aicoders")
            try:
                return Path(*current.parts[: idx + 1])
            except Exception:
                pass

        for _ in range(10):
            try:
                for m in self._PROJECT_ROOT_MARKERS:
                    if (current / m).exists():
                        return current
            except Exception:
                pass

            if current.parent == current:
                break
            current = current.parent

        return None

    def _normalize_project_path(self, path: Path) -> str:
        try:
            p = path
            if p.suffix:
                p = p.parent
            root = self._detect_project_root(p)
            return str(root) if root is not None else str(p)
        except Exception:
            return str(path)

    def _is_sqlite(self, db_file: Path) -> bool:
        try:
            return db_file.read_bytes()[:16] == b"SQLite format 3\x00"
        except Exception:
            return False

    def _safe_stat_size(self, path: Path) -> Optional[int]:
        try:
            return int(path.stat().st_size)
        except Exception:
            return None

    def _sqlite_list_tables(self, db_file: Path) -> List[str]:
        rows = self._read_sqlite(db_file, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [r[0] for r in rows if r and isinstance(r[0], str)]

    def _artifact_fallback(
        self,
        *,
        source_file: str,
        installation: Path,
        artifact_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> List[Engram]:
        stable_seed = f"{self.ide_name}|artifact|{source_file}|{artifact_type}".encode("utf-8", errors="ignore")
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
                metadata={"artifact_type": artifact_type, "details": details or {}},
                ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
            )
        ]

    def _parse_vscode_extension_sessions(
        self,
        installation: Path,
        glob_pattern: str = "*.json",
        workspace_id: Optional[str] = None,
        project_path: Optional[str] = None,
    ) -> List[Engram]:
        engrams = []
        session_dir = installation / "sessions"
        if not session_dir.exists():
            return engrams

        for session_file in sorted(session_dir.glob(glob_pattern)):
            try:
                content = session_file.read_text(encoding="utf-8")
                data = self._safe_json_loads(content)
                if not data or not isinstance(data, dict):
                    continue

                messages = []
                history = data.get("history") or data.get("messages") or []
                for item in history:
                    if not isinstance(item, dict):
                        continue
                    role = item.get("role") or item.get("type")
                    text = item.get("text") or item.get("content") or item.get("message") or ""
                    if role and text:
                        messages.append(Message(
                            role=str(role).lower(),
                            content=str(text),
                            timestamp=item.get("timestamp"),
                        ))

                if messages:
                    engrams.append(Engram(
                        id=str(uuid.uuid4()),
                        source=self.ide_name,
                        source_file=str(session_file),
                        messages=messages,
                        metadata={"title": data.get("title")},
                        workspace_id=workspace_id,
                        project_path=project_path,
                        ide_info=self._build_ide_info(
                            ide_type="vscode-extension", installation_path=installation
                        ),
                    ))
            except Exception as e:
                logger.error(f"Error parsing {self.ide_name} session {session_file}: {e}")

        return engrams

    def _scan_vscode_sqlite_storage(
        self,
        installation: Path,
        known_keys: List[str],
        installation_path: Optional[Path] = None,
    ) -> List[Engram]:
        engrams = []
        inst_path = installation_path or installation
        for db_file in installation.rglob("*.db"):
            if not db_file.is_file() or not self._is_sqlite(db_file):
                continue
            for key in known_keys:
                rows = self._read_sqlite(db_file, "SELECT value FROM ItemTable WHERE [key] = ? LIMIT 1", (key,))
                if not rows:
                    continue
                raw_value = rows[0][0]
                store = self._safe_json_loads(raw_value)
                if not isinstance(store, (dict, list)):
                    continue
                messages = []
                history = store.get("history") or store.get("messages") or (store if isinstance(store, list) else [])
                if isinstance(history, list):
                    for item in history:
                        if not isinstance(item, dict):
                            continue
                        role = item.get("role") or item.get("type")
                        text = item.get("text") or item.get("content") or item.get("message") or ""
                        if role and text:
                            messages.append(Message(
                                role=str(role).lower(),
                                content=str(text),
                                timestamp=item.get("timestamp"),
                            ))
                if messages:
                    engrams.append(Engram(
                        id=str(uuid.uuid4()),
                        source=self.ide_name,
                        source_file=str(db_file),
                        messages=messages,
                        metadata={"source_key": key, "title": store.get("title")},
                        ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=inst_path),
                    ))
        return engrams
