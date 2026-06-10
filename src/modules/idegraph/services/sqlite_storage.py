"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.services
:standard: Aegis-IdeGraph-v1.0

Storage — SQLite persistence layer for cross-IDE memories, settings, and configurations.
"""

import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.modules.idegraph.core.logging_service import get_logger
from src.modules.idegraph.domain.engram import Engram, IDEInfo, Message

logger = get_logger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def _json_dumps_stable(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _normalize_workspace_path(value: str) -> str:
    v = (value or "").strip().lower()
    v = v.replace("\\", "/")
    while "//" in v:
        v = v.replace("//", "/")
    if v.endswith("/"):
        v = v[:-1]
    return v


class Storage:
    def __init__(
        self,
        db=None,
        db_path: Optional[Path] = None,
    ):
        self._db = db
        if db is not None:
            # Shared DB mode — tables already created by orchestrator
            self.db_path = Path(db._db_path) if hasattr(db, '_db_path') else Path(":memory:")
            return
        # Standalone mode (legacy)
        root = Path(__file__).resolve().parents[4]
        self.db_path = db_path or Path(os.environ.get("CODECORTEX_DB_PATH", str(root / "database" / "codecortex.db")))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._db is not None:
            return self._db.conn
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _session(self) -> sqlite3.Connection:
        conn = self._connect()
        try:
            yield conn
            if self._db is None:
                conn.commit()
        except Exception:
            if self._db is None:
                conn.rollback()
            raise
        finally:
            if self._db is None:
                conn.close()

    def _init_db(self) -> None:
        root = Path(__file__).resolve().parents[4]
        migrations_dir = root / "database" / "migrations"
        if not migrations_dir.exists():
            logger.warning(f"Migrations directory missing: {migrations_dir}. Creating tables directly.")
            from src.core.database.sidecortex_schema import ensure_sidecortex_tables
            with self._session() as conn:
                ensure_sidecortex_tables(conn)
            return
        with self._session() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
            )
            applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}
            migrations = self._list_migrations(migrations_dir)
            for version, name, sql in migrations:
                if version in applied:
                    continue
                try:
                    conn.execute("BEGIN")
                    conn.executescript(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations(version, name, applied_at) VALUES(?, ?, ?)",
                        (version, name, _utc_now_iso()),
                    )
                except Exception:
                    raise

    def _list_migrations(self, migrations_dir: Path) -> List[Tuple[int, str, str]]:
        items: List[Tuple[int, str, str]] = []
        for p in sorted(migrations_dir.glob("*.sql")):
            stem = p.stem
            prefix = stem.split("_", 1)[0]
            try:
                version = int(prefix)
            except ValueError:
                continue
            items.append((version, p.name, p.read_text(encoding="utf-8")))
        items.sort(key=lambda x: x[0])
        return items

    def begin_sync_run(self, *, request_id: Optional[str] = None) -> str:
        run_id = f"sync_{uuid.uuid4()}"
        with self._session() as conn:
            conn.execute(
                "INSERT INTO sync_runs(id, started_at, status, request_id) VALUES(?, ?, ?, ?)",
                (run_id, _utc_now_iso(), "in_progress", request_id),
            )
        return run_id

    def end_sync_run(self, run_id: str, *, status: str, summary: Optional[Dict[str, Any]] = None, error: Optional[Dict[str, Any]] = None) -> None:
        with self._session() as conn:
            conn.execute(
                "UPDATE sync_runs SET finished_at=?, status=?, summary_json=?, error_json=? WHERE id=?",
                (
                    _utc_now_iso(),
                    status,
                    _json_dumps_stable(summary) if summary is not None else None,
                    _json_dumps_stable(error) if error is not None else None,
                    run_id,
                ),
            )

    def persist_engrams(self, engrams: Iterable[Engram], *, request_id: Optional[str] = None) -> Dict[str, Any]:
        run_id = self.begin_sync_run(request_id=request_id)
        started = datetime.now(timezone.utc)

        counts = {
            "ides_upserted": 0,
            "workspaces_upserted": 0,
            "workspace_instances_upserted": 0,
            "projects_upserted": 0,
            "conversations_upserted": 0,
            "messages_upserted": 0,
            "contexts_upserted": 0,
        }

        try:
            for engram in engrams:
                ide_id, ide_changed = self._upsert_ide(engram.ide_info, source=engram.source)
                if ide_changed:
                    counts["ides_upserted"] += 1

                workspace_id, ws_changed = self._upsert_workspace(engram)
                if ws_changed:
                    counts["workspaces_upserted"] += 1

                ws_instance_id, ws_inst_changed = self._upsert_workspace_instance(
                    workspace_id=workspace_id,
                    ide_id=ide_id,
                    ide_workspace_id=engram.workspace_id,
                    source_file=engram.source_file,
                )
                if ws_inst_changed:
                    counts["workspace_instances_upserted"] += 1

                project_changed = self._upsert_project(workspace_id=workspace_id, name=engram.project_name, path=engram.project_path)
                if project_changed:
                    counts["projects_upserted"] += 1

                conv_changed, msg_count, ctx_count = self._upsert_conversation_and_children(
                    run_id=run_id,
                    engram=engram,
                    workspace_id=workspace_id,
                    workspace_instance_id=ws_instance_id,
                    ide_id=ide_id,
                )
                if conv_changed:
                    counts["conversations_upserted"] += 1
                counts["messages_upserted"] += msg_count
                counts["contexts_upserted"] += ctx_count

            duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
            summary = {"duration_ms": duration_ms, **counts}
            self.end_sync_run(run_id, status="completed", summary=summary)
            logger.info(
                "SQLite persist completed",
                extra={
                    "request_id": request_id,
                    "extra_data": {"event": "sqlite_persist_completed", "sync_run_id": run_id, **summary},
                },
            )
            return {"sync_run_id": run_id, **summary}
        except Exception as e:
            error = {"message": str(e)}
            self.end_sync_run(run_id, status="failed", error=error)
            logger.error(
                "SQLite persist failed",
                extra={
                    "request_id": request_id,
                    "extra_data": {"event": "sqlite_persist_failed", "sync_run_id": run_id, "error": error},
                },
            )
            raise

    def _upsert_ide(self, ide_info: Optional[IDEInfo], *, source: str) -> Tuple[str, bool]:
        if ide_info is None:
            ide_info = IDEInfo(name=source or "unknown", type="unknown")

        installation_path = ide_info.installation_path or ""
        identity = f"{ide_info.name}|{ide_info.type}|{installation_path}"
        ide_id = _sha256_hex(identity)

        payload = {
            "name": ide_info.name,
            "type": ide_info.type,
            "installation_path": ide_info.installation_path,
            "ide_version": ide_info.version,
            "detected_at": ide_info.detected_at,
        }
        new_hash = _sha256_hex(_json_dumps_stable(payload))
        now = _utc_now_iso()

        with self._session() as conn:
            row = conn.execute("SELECT content_hash, version FROM ides WHERE id=?", (ide_id,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO ides(id, name, type, installation_path, ide_version, detected_at, created_at, updated_at, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        ide_id,
                        ide_info.name,
                        ide_info.type,
                        ide_info.installation_path,
                        ide_info.version,
                        ide_info.detected_at,
                        now,
                        now,
                        new_hash,
                        1,
                    ),
                )
                return ide_id, True

            old_hash = row["content_hash"]
            if old_hash == new_hash:
                conn.execute("UPDATE ides SET updated_at=? WHERE id=?", (now, ide_id))
                return ide_id, False

            next_version = int(row["version"]) + 1
            conn.execute(
                "UPDATE ides SET name=?, type=?, installation_path=?, ide_version=?, detected_at=?, updated_at=?, content_hash=?, version=? WHERE id=?",
                (
                    ide_info.name,
                    ide_info.type,
                    ide_info.installation_path,
                    ide_info.version,
                    ide_info.detected_at,
                    now,
                    new_hash,
                    next_version,
                    ide_id,
                ),
            )

        return ide_id, True

    def ensure_ide(self, ide_info: IDEInfo, *, source: str) -> str:
        ide_id, _ = self._upsert_ide(ide_info, source=source)
        return ide_id

    def get_any_workspace_instance_id(self, *, workspace_id: str, ide_id: str) -> Optional[int]:
        with self._session() as conn:
            row = conn.execute(
                "SELECT id FROM workspace_instances WHERE workspace_id=? AND ide_id=? ORDER BY last_seen_at DESC LIMIT 1",
                (workspace_id, ide_id),
            ).fetchone()
            if row is None:
                return None
            return int(row["id"])

    def ensure_workspace_instance(
        self,
        *,
        workspace_id: str,
        ide_id: str,
        ide_workspace_id: Optional[str] = None,
        source_file: Optional[str] = None,
    ) -> int:
        ws_instance_id, _ = self._upsert_workspace_instance(
            workspace_id=workspace_id,
            ide_id=ide_id,
            ide_workspace_id=ide_workspace_id,
            source_file=source_file,
        )
        return int(ws_instance_id) if ws_instance_id is not None else 0

    def _workspace_key_from_engram(self, engram: Engram) -> str:
        if engram.project_path:
            return _sha256_hex(_normalize_workspace_path(engram.project_path))
        if engram.project_name:
            return _sha256_hex(engram.project_name.strip().lower())
        if engram.workspace_id:
            return _sha256_hex(engram.workspace_id.strip().lower())
        return _sha256_hex(engram.source_file.strip().lower())

    def _upsert_workspace(self, engram: Engram) -> Tuple[str, bool]:
        workspace_id = self._workspace_key_from_engram(engram)
        payload = {
            "project_name": engram.project_name,
            "project_path": engram.project_path,
        }
        new_hash = _sha256_hex(_json_dumps_stable(payload))
        now = _utc_now_iso()

        with self._session() as conn:
            row = conn.execute("SELECT content_hash, version FROM workspaces WHERE id=?", (workspace_id,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO workspaces(id, project_name, project_path, created_at, updated_at, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?)",
                    (workspace_id, engram.project_name, engram.project_path, now, now, new_hash, 1),
                )
                return workspace_id, True

            old_hash = row["content_hash"]
            if old_hash == new_hash:
                conn.execute("UPDATE workspaces SET updated_at=? WHERE id=?", (now, workspace_id))
                return workspace_id, False

            next_version = int(row["version"]) + 1
            conn.execute(
                "UPDATE workspaces SET project_name=?, project_path=?, updated_at=?, content_hash=?, version=? WHERE id=?",
                (engram.project_name, engram.project_path, now, new_hash, next_version, workspace_id),
            )

        return workspace_id, True

    def _upsert_workspace_instance(
        self,
        *,
        workspace_id: str,
        ide_id: str,
        ide_workspace_id: Optional[str],
        source_file: Optional[str],
    ) -> Tuple[Optional[int], bool]:
        payload = {
            "ide_workspace_id": ide_workspace_id,
            "source_file": source_file,
        }
        new_hash = _sha256_hex(_json_dumps_stable(payload))
        now = _utc_now_iso()

        with self._session() as conn:
            row = conn.execute(
                "SELECT id, content_hash, version FROM workspace_instances WHERE workspace_id=? AND ide_id=? AND COALESCE(ide_workspace_id,'')=? AND COALESCE(source_file,'')=?",
                (workspace_id, ide_id, ide_workspace_id or "", source_file or ""),
            ).fetchone()

            if row is None:
                conn.execute(
                    "INSERT INTO workspace_instances(workspace_id, ide_id, ide_workspace_id, source_file, first_seen_at, last_seen_at, created_at, updated_at, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (workspace_id, ide_id, ide_workspace_id, source_file, now, now, now, now, new_hash, 1),
                )
                new_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                return int(new_id), True

            ws_instance_id = int(row["id"])
            old_hash = row["content_hash"]
            if old_hash == new_hash:
                conn.execute(
                    "UPDATE workspace_instances SET last_seen_at=?, updated_at=? WHERE id=?",
                    (now, now, ws_instance_id),
                )
                return ws_instance_id, False

            next_version = int(row["version"]) + 1
            conn.execute(
                "UPDATE workspace_instances SET ide_workspace_id=?, source_file=?, last_seen_at=?, updated_at=?, content_hash=?, version=? WHERE id=?",
                (ide_workspace_id, source_file, now, now, new_hash, next_version, ws_instance_id),
            )

        return ws_instance_id, True

    def _upsert_project(self, *, workspace_id: str, name: Optional[str], path: Optional[str]) -> bool:
        if not name:
            return False

        project_id = _sha256_hex(f"{workspace_id}|{name.strip().lower()}")
        payload = {"workspace_id": workspace_id, "name": name, "path": path}
        new_hash = _sha256_hex(_json_dumps_stable(payload))
        now = _utc_now_iso()

        with self._session() as conn:
            row = conn.execute("SELECT content_hash, version FROM projects WHERE id=?", (project_id,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO projects(id, workspace_id, name, path, created_at, updated_at, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                    (project_id, workspace_id, name, path, now, now, new_hash, 1),
                )
                return True

            old_hash = row["content_hash"]
            if old_hash == new_hash:
                conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
                return False

            next_version = int(row["version"]) + 1
            conn.execute(
                "UPDATE projects SET name=?, path=?, updated_at=?, content_hash=?, version=? WHERE id=?",
                (name, path, now, new_hash, next_version, project_id),
            )

        return True

    def _upsert_conversation_and_children(
        self,
        *,
        run_id: str,
        engram: Engram,
        workspace_id: str,
        workspace_instance_id: Optional[int],
        ide_id: str,
    ) -> Tuple[bool, int, int]:
        metadata_json = _json_dumps_stable(engram.metadata or {})

        msg_hashes: List[str] = []
        for msg in engram.messages:
            msg_hashes.append(self._hash_message(msg))
        conv_hash_payload = {
            "id": engram.id,
            "source": engram.source,
            "source_file": engram.source_file,
            "title": engram.title,
            "model": engram.model,
            "metadata": engram.metadata,
            "messages": msg_hashes,
        }
        new_hash = _sha256_hex(_json_dumps_stable(conv_hash_payload))

        now = _utc_now_iso()
        created_at = engram.created_at.isoformat() if hasattr(engram.created_at, "isoformat") else now

        started_at, ended_at = self._infer_conversation_bounds(engram.messages)
        message_count = len(engram.messages)

        conv_changed = False

        with self._session() as conn:
            row = conn.execute("SELECT content_hash, version FROM conversations WHERE id=?", (engram.id,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO conversations(id, workspace_id, workspace_instance_id, ide_id, source, source_file, title, model, created_at, updated_at, started_at, ended_at, message_count, metadata_json, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        engram.id,
                        workspace_id,
                        workspace_instance_id,
                        ide_id,
                        engram.source,
                        engram.source_file,
                        engram.title,
                        engram.model,
                        created_at,
                        now,
                        started_at,
                        ended_at,
                        message_count,
                        metadata_json,
                        new_hash,
                        1,
                    ),
                )
                self._log_change(
                    conn,
                    run_id,
                    "conversation",
                    engram.id,
                    "insert",
                    None,
                    new_hash,
                    {"engram_id": engram.id, "workspace_id": workspace_id, "message_count": message_count},
                    ide_name=engram.source,
                    source_file=engram.source_file,
                )
                conv_changed = True
            else:
                old_hash = row["content_hash"]
                if old_hash == new_hash:
                    conn.execute(
                        "UPDATE conversations SET updated_at=?, message_count=? WHERE id=?",
                        (now, message_count, engram.id),
                    )
                else:
                    next_version = int(row["version"]) + 1
                    conn.execute(
                        "UPDATE conversations SET workspace_id=?, workspace_instance_id=?, ide_id=?, source=?, source_file=?, title=?, model=?, updated_at=?, started_at=?, ended_at=?, message_count=?, metadata_json=?, content_hash=?, version=? WHERE id=?",
                        (
                            workspace_id,
                            workspace_instance_id,
                            ide_id,
                            engram.source,
                            engram.source_file,
                            engram.title,
                            engram.model,
                            now,
                            started_at,
                            ended_at,
                            message_count,
                            metadata_json,
                            new_hash,
                            next_version,
                            engram.id,
                        ),
                    )
                    self._log_change(
                        conn,
                        run_id,
                        "conversation",
                        engram.id,
                        "update",
                        old_hash,
                        new_hash,
                        {"engram_id": engram.id, "workspace_id": workspace_id, "message_count": message_count},
                        ide_name=engram.source,
                        source_file=engram.source_file,
                    )
                    conv_changed = True

            messages_upserted = 0
            contexts_upserted = 0
            for idx, msg in enumerate(engram.messages):
                if self._upsert_message(conn, run_id, engram_id=engram.id, idx=idx, msg=msg, ide_name=engram.source, source_file=engram.source_file):
                    messages_upserted += 1
                contexts_upserted += self._upsert_message_contexts(conn, run_id, workspace_id=workspace_id, conversation_id=engram.id, ide_id=ide_id, msg=msg)

        return conv_changed, messages_upserted, contexts_upserted

    def _infer_conversation_bounds(self, messages: List[Message]) -> Tuple[Optional[str], Optional[str]]:
        ts: List[str] = []
        for m in messages:
            if isinstance(m.timestamp, str) and m.timestamp:
                ts.append(m.timestamp)
        if not ts:
            return None, None
        ts_sorted = sorted(ts)
        return ts_sorted[0], ts_sorted[-1]

    def _hash_message(self, msg: Message) -> str:
        payload = {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp,
            "metadata": msg.metadata,
            "code_context": msg.code_context,
            "tool_use": msg.tool_use,
            "diffs": msg.diffs,
        }
        return _sha256_hex(_json_dumps_stable(payload))

    def _upsert_message(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        *,
        engram_id: str,
        idx: int,
        msg: Message,
        ide_name: str,
        source_file: str,
    ) -> bool:
        now = _utc_now_iso()
        payload = msg.to_dict() if hasattr(msg, "to_dict") else asdict(msg)
        new_hash = _sha256_hex(_json_dumps_stable(payload))

        row = conn.execute(
            "SELECT id, content_hash, version FROM messages WHERE conversation_id=? AND idx=?",
            (engram_id, idx),
        ).fetchone()

        metadata_json = _json_dumps_stable(msg.metadata or {})
        code_context_json = _json_dumps_stable(msg.code_context or [])
        tool_use_json = _json_dumps_stable(msg.tool_use or [])
        diffs_json = _json_dumps_stable(msg.diffs or [])

        if row is None:
            conn.execute(
                "INSERT INTO messages(conversation_id, idx, role, content, timestamp, metadata_json, code_context_json, tool_use_json, diffs_json, created_at, updated_at, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    engram_id,
                    idx,
                    msg.role,
                    msg.content,
                    msg.timestamp,
                    metadata_json,
                    code_context_json,
                    tool_use_json,
                    diffs_json,
                    now,
                    now,
                    new_hash,
                    1,
                ),
            )
            self._log_change(
                conn,
                run_id,
                "message",
                f"{engram_id}:{idx}",
                "insert",
                None,
                new_hash,
                {"conversation_id": engram_id, "idx": idx},
                ide_name=ide_name,
                source_file=source_file,
            )
            return True

        old_hash = row["content_hash"]
        if old_hash == new_hash:
            conn.execute(
                "UPDATE messages SET updated_at=? WHERE id=?",
                (now, int(row["id"])),
            )
            return False

        next_version = int(row["version"]) + 1
        conn.execute(
            "UPDATE messages SET role=?, content=?, timestamp=?, metadata_json=?, code_context_json=?, tool_use_json=?, diffs_json=?, updated_at=?, content_hash=?, version=? WHERE id=?",
            (
                msg.role,
                msg.content,
                msg.timestamp,
                metadata_json,
                code_context_json,
                tool_use_json,
                diffs_json,
                now,
                new_hash,
                next_version,
                int(row["id"]),
            ),
        )
        self._log_change(
            conn,
            run_id,
            "message",
            f"{engram_id}:{idx}",
            "update",
            old_hash,
            new_hash,
            {"conversation_id": engram_id, "idx": idx},
            ide_name=ide_name,
            source_file=source_file,
        )
        return True

    def _upsert_message_contexts(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        *,
        workspace_id: str,
        conversation_id: str,
        ide_id: str,
        msg: Message,
    ) -> int:
        if not isinstance(msg.code_context, list) or not msg.code_context:
            return 0

        inserted = 0
        now = _utc_now_iso()
        for item in msg.code_context:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("type") or "unknown")
            payload_json = _json_dumps_stable(item)
            h = _sha256_hex(payload_json)

            row = conn.execute(
                "SELECT id FROM contexts WHERE workspace_id=? AND conversation_id=? AND ide_id=? AND kind=? AND content_hash=? LIMIT 1",
                (workspace_id, conversation_id, ide_id, kind, h),
            ).fetchone()
            if row is not None:
                continue

            conn.execute(
                "INSERT INTO contexts(workspace_id, conversation_id, ide_id, kind, payload_json, captured_at, created_at, updated_at, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (workspace_id, conversation_id, ide_id, kind, payload_json, now, now, now, h, 1),
            )
            inserted += 1

        if inserted:
            self._log_change(
                conn,
                run_id,
                "contexts",
                conversation_id,
                "insert",
                None,
                None,
                {"inserted": inserted},
            )

        return inserted

    def _log_change(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        entity_type: str,
        entity_id: str,
        change_kind: str,
        old_hash: Optional[str],
        new_hash: Optional[str],
        details: Any,
        *,
        ide_name: Optional[str] = None,
        source_file: Optional[str] = None,
    ) -> None:
        now = _utc_now_iso()
        try:
            details_json = _json_dumps_stable(details)
        except Exception:
            details_json = None

        conn.execute(
            "INSERT INTO change_log(sync_run_id, entity_type, entity_id, change_kind, old_hash, new_hash, detected_at, ide_name, source_file, details_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, entity_type, entity_id, change_kind, old_hash, new_hash, now, ide_name, source_file, details_json),
        )

    def upsert_configuration(self, *, scope: str, key: str, value: Any, source_file: Optional[str] = None) -> bool:
        payload = {"scope": scope, "key": key, "value": value, "source_file": source_file}
        new_hash = _sha256_hex(_json_dumps_stable(payload))
        now = _utc_now_iso()

        value_json = None if isinstance(value, str) else _json_dumps_stable(value)
        value_text = value if isinstance(value, str) else None

        with self._session() as conn:
            row = conn.execute(
                "SELECT id, content_hash, version FROM configurations WHERE scope=? AND key=?",
                (scope, key),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO configurations(scope, key, value_json, value_text, source_file, captured_at, created_at, updated_at, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (scope, key, value_json, value_text, source_file, now, now, now, new_hash, 1),
                )
                return True

            old_hash = row["content_hash"]
            if old_hash == new_hash:
                conn.execute("UPDATE configurations SET updated_at=?, captured_at=? WHERE id=?", (now, now, int(row["id"])))
                return False

            next_version = int(row["version"]) + 1
            conn.execute(
                "UPDATE configurations SET value_json=?, value_text=?, source_file=?, captured_at=?, updated_at=?, content_hash=?, version=? WHERE id=?",
                (value_json, value_text, source_file, now, now, new_hash, next_version, int(row["id"])),
            )
            return True

    def upsert_ide_setting(
        self,
        *,
        ide_id: str,
        key: str,
        value: Any,
        source_file: Optional[str] = None,
        workspace_instance_id: Optional[int] = None,
    ) -> bool:
        payload = {
            "ide_id": ide_id,
            "workspace_instance_id": workspace_instance_id,
            "key": key,
            "value": value,
            "source_file": source_file,
        }
        new_hash = _sha256_hex(_json_dumps_stable(payload))
        now = _utc_now_iso()

        value_json = None if isinstance(value, str) else _json_dumps_stable(value)
        value_text = value if isinstance(value, str) else None

        with self._session() as conn:
            row = conn.execute(
                "SELECT id, content_hash, version FROM ide_settings WHERE ide_id=? AND COALESCE(workspace_instance_id,0)=COALESCE(?,0) AND key=?",
                (ide_id, workspace_instance_id, key),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO ide_settings(ide_id, workspace_instance_id, key, value_json, value_text, source_file, captured_at, created_at, updated_at, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (ide_id, workspace_instance_id, key, value_json, value_text, source_file, now, now, now, new_hash, 1),
                )
                return True

            old_hash = row["content_hash"]
            if old_hash == new_hash:
                conn.execute("UPDATE ide_settings SET updated_at=?, captured_at=? WHERE id=?", (now, now, int(row["id"])))
                return False

            next_version = int(row["version"]) + 1
            conn.execute(
                "UPDATE ide_settings SET value_json=?, value_text=?, source_file=?, captured_at=?, updated_at=?, content_hash=?, version=? WHERE id=?",
                (value_json, value_text, source_file, now, now, new_hash, next_version, int(row["id"])),
            )
            return True

    def upsert_ide_extension(
        self,
        *,
        ide_id: str,
        name: str,
        publisher: Optional[str] = None,
        extension_version: Optional[str] = None,
        enabled: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        payload = {
            "ide_id": ide_id,
            "name": name,
            "publisher": publisher,
            "extension_version": extension_version,
            "enabled": enabled,
            "metadata": metadata or {},
        }
        new_hash = _sha256_hex(_json_dumps_stable(payload))
        now = _utc_now_iso()
        enabled_int = None if enabled is None else (1 if enabled else 0)
        metadata_json = _json_dumps_stable(metadata or {})

        with self._session() as conn:
            row = conn.execute(
                "SELECT id, content_hash, version FROM ide_extensions WHERE ide_id=? AND name=? AND COALESCE(publisher,'')=?",
                (ide_id, name, publisher or ""),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO ide_extensions(ide_id, name, publisher, extension_version, enabled, metadata_json, captured_at, created_at, updated_at, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (ide_id, name, publisher, extension_version, enabled_int, metadata_json, now, now, now, new_hash, 1),
                )
                return True

            old_hash = row["content_hash"]
            if old_hash == new_hash:
                conn.execute("UPDATE ide_extensions SET updated_at=?, captured_at=? WHERE id=?", (now, now, int(row["id"])))
                return False

            next_version = int(row["version"]) + 1
            conn.execute(
                "UPDATE ide_extensions SET publisher=?, extension_version=?, enabled=?, metadata_json=?, captured_at=?, updated_at=?, content_hash=?, version=? WHERE id=?",
                (publisher, extension_version, enabled_int, metadata_json, now, now, new_hash, next_version, int(row["id"])),
            )
            return True

    def upsert_mcp_settings(
        self,
        *,
        scope: str,
        settings: Dict[str, Any],
        ide_id: Optional[str] = None,
        source_file: Optional[str] = None,
    ) -> bool:
        payload = {"scope": scope, "settings": settings, "ide_id": ide_id, "source_file": source_file}
        new_hash = _sha256_hex(_json_dumps_stable(payload))
        now = _utc_now_iso()
        settings_json = _json_dumps_stable(settings)

        with self._session() as conn:
            row = conn.execute(
                "SELECT id, content_hash, version FROM mcp_settings WHERE scope=? AND COALESCE(ide_id,'')=? ORDER BY id DESC LIMIT 1",
                (scope, ide_id or ""),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO mcp_settings(ide_id, scope, settings_json, source_file, captured_at, created_at, updated_at, content_hash, version) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (ide_id, scope, settings_json, source_file, now, now, now, new_hash, 1),
                )
                return True

            old_hash = row["content_hash"]
            if old_hash == new_hash:
                conn.execute("UPDATE mcp_settings SET updated_at=?, captured_at=? WHERE id=?", (now, now, int(row["id"])))
                return False

            next_version = int(row["version"]) + 1
            conn.execute(
                "UPDATE mcp_settings SET settings_json=?, source_file=?, captured_at=?, updated_at=?, content_hash=?, version=? WHERE id=?",
                (settings_json, source_file, now, now, new_hash, next_version, int(row["id"])),
            )
            return True

    def list_memories(
        self,
        *,
        project_name: Optional[str] = None,
        workspace_key: Optional[str] = None,
        ide_name: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        with self._session() as conn:
            sql = (
                "SELECT c.id, c.title, c.created_at, c.updated_at, c.source, c.source_file, "
                "w.id AS workspace_key, w.project_name, w.project_path, "
                "COALESCE(i.name, c.source) AS ide_name "
                "FROM conversations c "
                "JOIN workspaces w ON w.id = c.workspace_id "
                "LEFT JOIN ides i ON i.id = c.ide_id "
                "WHERE 1=1"
            )
            params: List[Any] = []
            if project_name:
                sql += " AND LOWER(w.project_name) LIKE ?"
                params.append(f"%{project_name.lower()}%")
            if workspace_key:
                sql += " AND w.id = ?"
                params.append(workspace_key)
            if ide_name:
                sql += " AND LOWER(COALESCE(i.name, c.source)) = ?"
                params.append(ide_name.lower())
            sql += " ORDER BY c.updated_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(sql, params).fetchall()

        return [
            {
                "id": r["id"],
                "title": r["title"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "source": r["source"],
                "source_file": r["source_file"],
                "workspace_key": r["workspace_key"],
                "project_name": r["project_name"],
                "project_path": r["project_path"],
                "ide_name": r["ide_name"],
            }
            for r in rows
        ]

    def list_workspaces(self, *, include_engram_count: bool = True) -> List[Dict[str, Any]]:
        with self._session() as conn:
            rows = conn.execute(
                "SELECT w.id AS workspace_key, w.project_name, w.project_path, "
                "MAX(c.updated_at) AS last_activity, "
                "COUNT(c.id) AS engram_count "
                "FROM workspaces w "
                "LEFT JOIN conversations c ON c.workspace_id = w.id "
                "GROUP BY w.id "
                "ORDER BY last_activity DESC"
            ).fetchall()
        items: List[Dict[str, Any]] = []
        for r in rows:
            item = {
                "workspace_key": r["workspace_key"],
                "project_name": r["project_name"],
                "project_path": r["project_path"],
                "last_activity": r["last_activity"],
            }
            if include_engram_count:
                item["engram_count"] = int(r["engram_count"] or 0)
            items.append(item)
        return items

    def get_workspace(self, *, workspace_key: str) -> Optional[Dict[str, Any]]:
        with self._session() as conn:
            ws = conn.execute(
                "SELECT id AS workspace_key, project_name, project_path FROM workspaces WHERE id=?",
                (workspace_key,),
            ).fetchone()
            if ws is None:
                return None
            rows = conn.execute(
                "SELECT id, source, updated_at FROM conversations WHERE workspace_id=? ORDER BY updated_at DESC",
                (workspace_key,),
            ).fetchall()
        return {
            "workspace_key": ws["workspace_key"],
            "project_name": ws["project_name"],
            "project_path": ws["project_path"],
            "engram_ids": [r["id"] for r in rows],
        }

    def list_projects(self, *, include_engram_count: bool = True) -> List[Dict[str, Any]]:
        return self.list_workspaces(include_engram_count=include_engram_count)

    def get_project(self, *, workspace_key: str) -> Optional[Dict[str, Any]]:
        return self.get_workspace(workspace_key=workspace_key)

    def search_conversations(
        self,
        *,
        keyword: str,
        project_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        kw = (keyword or "").strip().lower()
        if not kw:
            return []
        limit = max(1, min(int(limit), 200))
        like = f"%{kw}%"
        with self._session() as conn:
            sql = (
                "SELECT c.id AS conversation_id, c.title, w.project_name, "
                "SUBSTR(m.content, 1, 200) AS snippet "
                "FROM messages m "
                "JOIN conversations c ON c.id = m.conversation_id "
                "JOIN workspaces w ON w.id = c.workspace_id "
                "WHERE LOWER(m.content) LIKE ?"
            )
            params: List[Any] = [like]
            if project_name:
                sql += " AND LOWER(w.project_name) LIKE ?"
                params.append(f"%{project_name.lower()}%")
            sql += " ORDER BY c.updated_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
        return [
            {
                "id": r["conversation_id"],
                "title": r["title"],
                "project_name": r["project_name"],
                "snippet": r["snippet"],
            }
            for r in rows
        ]

    def health_snapshot(self) -> Dict[str, Any]:
        with self._session() as conn:
            last_run = conn.execute("SELECT * FROM sync_runs ORDER BY started_at DESC LIMIT 1").fetchone()
            conv_count = conn.execute("SELECT COUNT(1) AS n FROM conversations").fetchone()["n"]
            msg_count = conn.execute("SELECT COUNT(1) AS n FROM messages").fetchone()["n"]
            ws_count = conn.execute("SELECT COUNT(1) AS n FROM workspaces").fetchone()["n"]
            failed_runs = conn.execute("SELECT COUNT(1) AS n FROM sync_runs WHERE status='failed'").fetchone()["n"]
        return {
            "db_path": str(self.db_path),
            "workspaces": int(ws_count or 0),
            "conversations": int(conv_count or 0),
            "messages": int(msg_count or 0),
            "last_sync_run": dict(last_run) if last_run is not None else None,
            "failed_runs": int(failed_runs or 0),
        }

    def ingestion_stats(self, *, ide_name: Optional[str] = None, since_iso: Optional[str] = None) -> Dict[str, Any]:
        with self._session() as conn:
            sql_runs = "SELECT status, started_at FROM sync_runs"
            params_runs: List[Any] = []
            if since_iso:
                sql_runs += " WHERE started_at >= ?"
                params_runs.append(since_iso)
            runs = conn.execute(sql_runs, params_runs).fetchall()
            total_runs = len(runs)
            ok_runs = len([r for r in runs if r["status"] == "completed"])
            failed_runs = len([r for r in runs if r["status"] == "failed"])

            sql = (
                "SELECT COALESCE(i.name, c.source) AS ide_name, COUNT(c.id) AS engrams, SUM(c.message_count) AS messages "
                "FROM conversations c "
                "LEFT JOIN ides i ON i.id = c.ide_id "
                "WHERE 1=1"
            )
            params: List[Any] = []
            if since_iso:
                sql += " AND c.updated_at >= ?"
                params.append(since_iso)
            if ide_name:
                sql += " AND LOWER(COALESCE(i.name, c.source)) = ?"
                params.append(ide_name.lower())
            sql += " GROUP BY COALESCE(i.name, c.source) ORDER BY engrams DESC"
            rows = conn.execute(sql, params).fetchall()

        return {
            "sync_runs": {"total": total_runs, "completed": ok_runs, "failed": failed_runs},
            "by_ide": [
                {
                    "ide_name": r["ide_name"],
                    "engrams": int(r["engrams"] or 0),
                    "messages": int(r["messages"] or 0),
                }
                for r in rows
            ],
        }
