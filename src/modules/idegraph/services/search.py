"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.services
:standard: CODDY-IdeGraph-v1.0

Search — Keyword and project-based search for ingested engrams.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.modules.idegraph.domain.engram import Engram, IDEInfo, Message
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)


class Search:
    def __init__(self, data_dir: Optional[Path] = None, db=None):
        self._db = db
        self.data_dir = data_dir or Path("outputs")
        self.cache: List[Engram] = []
        self._cache_lock = threading.Lock()
        self._last_cache_mtime: float = 0.0
        if db is None:
            from src.core.config.database import get_db_path
            self.db_path = Path(os.environ.get("CODECORTEX_DB_PATH", get_db_path())).resolve()
        else:
            self.db_path = Path(db._db_path) if hasattr(db, '_db_path') else Path(":memory:")

    def _sqlite_available(self) -> bool:
        return self._db is not None or self.db_path.exists()

    def _connect_db(self) -> sqlite3.Connection:
        if self._db is not None:
            return self._db.conn
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _session(self) -> sqlite3.Connection:
        conn = self._connect_db()
        try:
            yield conn
        finally:
            if self._db is None:
                conn.close()

    def _hydrate_engram_from_db(self, conversation_id: str) -> Optional[Engram]:
        with self._session() as conn:
            conv = conn.execute(
                "SELECT c.*, w.project_name AS ws_project_name, w.project_path AS ws_project_path, wi.ide_workspace_id AS ide_workspace_id, i.name AS ide_name, i.type AS ide_type, i.installation_path AS ide_installation_path, i.ide_version AS ide_version, i.detected_at AS ide_detected_at "
                "FROM conversations c "
                "JOIN workspaces w ON w.id = c.workspace_id "
                "LEFT JOIN workspace_instances wi ON wi.id = c.workspace_instance_id "
                "LEFT JOIN ides i ON i.id = c.ide_id "
                "WHERE c.id=?",
                (conversation_id,),
            ).fetchone()
            if conv is None:
                return None
            rows = conn.execute(
                "SELECT idx, role, content, timestamp, metadata_json, code_context_json, tool_use_json, diffs_json "
                "FROM messages WHERE conversation_id=? ORDER BY idx ASC",
                (conversation_id,),
            ).fetchall()

        messages = []
        for r in rows:
            messages.append(Message(
                role=r["role"], content=r["content"], timestamp=r["timestamp"],
                metadata=json.loads(r["metadata_json"]) if r["metadata_json"] else {},
                code_context=json.loads(r["code_context_json"]) if r["code_context_json"] else [],
                tool_use=json.loads(r["tool_use_json"]) if r["tool_use_json"] else [],
                diffs=json.loads(r["diffs_json"]) if r["diffs_json"] else [],
            ))

        ide_info = None
        if conv["ide_name"]:
            ide_info = IDEInfo(
                name=conv["ide_name"], type=conv["ide_type"] or "unknown",
                installation_path=conv["ide_installation_path"], version=conv["ide_version"],
                detected_at=conv["ide_detected_at"] or "",
            )
        created_at = datetime.now()
        raw_created_at = conv["created_at"]
        if isinstance(raw_created_at, str) and raw_created_at:
            try:
                created_at = datetime.fromisoformat(raw_created_at.replace("Z", "+00:00"))
            except Exception:
                pass
        metadata = json.loads(conv["metadata_json"]) if conv["metadata_json"] else {}
        return Engram(
            id=conv["id"], source=conv["source"], source_file=conv["source_file"],
            messages=messages, created_at=created_at, workspace_id=conv["ide_workspace_id"],
            project_path=conv["ws_project_path"], project_name=conv["ws_project_name"],
            title=conv["title"], model=conv["model"],
            metadata=metadata if isinstance(metadata, dict) else {}, ide_info=ide_info,
        )

    def _needs_reload(self) -> bool:
        jsonl_files = list(self.data_dir.glob("*.jsonl"))
        if not jsonl_files:
            return bool(self.cache)
        latest_mtime = max(f.stat().st_mtime for f in jsonl_files)
        return latest_mtime > self._last_cache_mtime

    def _load_data(self):
        with self._cache_lock:
            if self.cache and not self._needs_reload():
                return
            jsonl_files = list(self.data_dir.glob("*.jsonl"))
            if not jsonl_files:
                return
            jsonl_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            loaded = []
            seen_ids = set()
            for file_path in jsonl_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            data = json.loads(line)
                            engram = Engram.from_dict(data)
                            if engram.id not in seen_ids:
                                loaded.append(engram)
                                seen_ids.add(engram.id)
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
            self.cache = loaded
            if jsonl_files:
                self._last_cache_mtime = max(f.stat().st_mtime for f in jsonl_files)
            logger.info(f"Search cache: {len(self.cache)} engrams")

    def get_by_id(self, engram_id: str) -> Optional[Engram]:
        if self._sqlite_available():
            return self._hydrate_engram_from_db(engram_id)
        self._load_data()
        with self._cache_lock:
            return next((e for e in self.cache if e.id == engram_id), None)

    def search(self, query: str, project_name: Optional[str] = None, ide_name: Optional[str] = None, limit: int = 10) -> List[Engram]:
        if self._sqlite_available():
            query_lower = query.lower()
            like = f"%{query_lower}%"
            with self._session() as conn:
                sql = (
                    "SELECT DISTINCT c.id "
                    "FROM messages m "
                    "JOIN conversations c ON c.id = m.conversation_id "
                    "JOIN workspaces w ON w.id = c.workspace_id "
                    "LEFT JOIN ides i ON i.id = c.ide_id "
                    "WHERE LOWER(m.content) LIKE ?"
                )
                params: List[Any] = [like]
                if project_name:
                    sql += " AND LOWER(w.project_name) LIKE ?"
                    params.append(f"%{project_name.lower()}%")
                if ide_name:
                    sql += " AND LOWER(COALESCE(i.name, c.source)) = ?"
                    params.append(ide_name.lower())
                sql += " LIMIT 100"
                ids = [row["id"] for row in conn.execute(sql, params).fetchall()]

            scored: List[tuple[Engram, int]] = []
            for cid in ids:
                e = self._hydrate_engram_from_db(cid)
                if e is None:
                    continue
                texts = []
                if e.title:
                    texts.append(e.title.lower())
                for m in e.messages:
                    texts.append((m.content or "").lower())
                full_text = " ".join(texts)
                if query_lower in full_text:
                    scored.append((e, full_text.count(query_lower)))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [x[0] for x in scored[:limit]]

        self._load_data()
        with self._cache_lock:
            cache_snapshot = list(self.cache)

        results = []
        query_lower = query.lower()
        for engram in cache_snapshot:
            if project_name and project_name.lower() not in (engram.project_name or "").lower():
                continue
            if ide_name:
                actual_ide = (engram.ide_info.name if engram.ide_info else engram.source)
                if ide_name.lower() != actual_ide.lower():
                    continue
            match_score = 0
            content_to_search = []
            if engram.title:
                content_to_search.append(engram.title.lower())
            for msg in engram.messages:
                content_to_search.append((msg.content or "").lower())
            full_text = " ".join(content_to_search)
            if query_lower in full_text:
                match_score = full_text.count(query_lower)
                results.append((engram, match_score))
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:limit]]

    def list_projects(self) -> List[str]:
        if self._sqlite_available():
            with self._session() as conn:
                rows = conn.execute("SELECT DISTINCT project_name FROM workspaces WHERE project_name IS NOT NULL AND project_name != '' ORDER BY project_name ASC").fetchall()
                return [r["project_name"] for r in rows]
        self._load_data()
        with self._cache_lock:
            projects = {engram.project_name for engram in self.cache if engram.project_name}
            return sorted(list(projects))
