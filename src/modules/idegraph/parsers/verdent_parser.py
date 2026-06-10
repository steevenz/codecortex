"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.parsers
:standard: Aegis-IdeGraph-v1.0
@fileoverview VerdentParser - Parser for Verdent AI interaction data.
"""

import json
import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class VerdentParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "verdent"

    def find_installations(self) -> List[Path]:
        verdent_dir = Path.home() / ".verdent"
        if verdent_dir.exists():
            return [verdent_dir]
        return []

    def parse_all(self) -> List[Engram]:
        all_engrams = []
        for inst in self.find_installations():
            all_engrams.extend(self._parse_sqlite(inst))
        return all_engrams

    def _parse_sqlite(self, installation: Path) -> List[Engram]:
        db_path = installation / "projects" / "agent_sessions.db"
        if not db_path.exists():
            return self._artifact_fallback(
                source_file=str(installation), installation=installation,
                artifact_type="verdent_unparsed",
            )

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
        except Exception as e:
            logger.error(f"Error connecting to Verdent DB: {e}")
            return self._artifact_fallback(
                source_file=str(db_path), installation=installation,
                artifact_type="verdent_db_error",
                details={"error": str(e)},
            )

        try:
            return self._extract_sessions(conn, installation, db_path)
        finally:
            conn.close()

    def _extract_sessions(self, conn: sqlite3.Connection, installation: Path, db_path: Path) -> List[Engram]:
        sessions = conn.execute("SELECT id, state, create_time, update_time FROM sessions ORDER BY create_time").fetchall()
        engrams = []

        for s in sessions:
            sid = s["id"]
            state_str = s["state"]
            state = {}
            if state_str:
                try:
                    state = json.loads(state_str) if isinstance(state_str, str) else {}
                except Exception as e:
                    logger.debug(f"Verdent parse warning: {e}")

            events = conn.execute(
                "SELECT author, content, timestamp FROM events WHERE session_id=? ORDER BY timestamp",
                (sid,),
            ).fetchall()

            messages = []
            project_path = state.get("cwd") or state.get("project_path")
            for e in events:
                author = e["author"]
                content_raw = e["content"]
                timestamp = e["timestamp"]

                content = self._extract_verdent_content(content_raw)
                if not content:
                    continue

                role = "user" if author == "user" else "assistant"
                messages.append(Message(
                    role=role,
                    content=content,
                    timestamp=str(timestamp) if timestamp else None,
                ))

            if not messages:
                continue

            resolved = self._detect_project_root(Path(project_path)) if project_path else None
            project_root = str(resolved) if resolved else project_path

            engrams.append(Engram(
                id=sid,
                source=self.ide_name,
                source_file=str(db_path),
                messages=messages,
                title=f"Verdent session {sid[:8]}",
                workspace_id=project_root,
                project_path=project_root,
                model=state.get("agent_model"),
                metadata={"project_hash": state.get("project_hash")},
                ide_info=self._build_ide_info(ide_type="cli", installation_path=installation),
            ))

        return engrams

    @staticmethod
    def _extract_verdent_content(content_raw: Any) -> str:
        if not content_raw:
            return ""
        if isinstance(content_raw, str):
            try:
                obj = json.loads(content_raw)
                if isinstance(obj, dict):
                    parts = obj.get("parts", [])
                    if isinstance(parts, list):
                        texts = []
                        for p in parts:
                            if isinstance(p, dict) and "text" in p:
                                texts.append(p["text"])
                        return "\n".join(texts)
                return content_raw
            except json.JSONDecodeError:
                return content_raw
        if isinstance(content_raw, dict):
            parts = content_raw.get("parts", [])
            if isinstance(parts, list):
                texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
                return "\n".join(texts)
        return str(content_raw) if content_raw else ""
