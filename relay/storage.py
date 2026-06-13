"""
SQLite storage layer for relay server.

:project: CodeCortex Relay
:package: Relay.Storage
:standard: CODDY-CrossStack-v1.0
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    CloudData, ProxyRequest, ProxyResponse, TunnelInfo, utcnow, generate_id, default_expiry,
)

DB_PATH = Path(__file__).parent / "relay.db"


class RelayStore:
    """Thread-safe SQLite storage for relay data."""

    def __init__(self, db_path: str = ""):
        self._db_path = db_path or str(DB_PATH)
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tunnels (
                tunnel_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL DEFAULT '',
                local_base TEXT NOT NULL DEFAULT 'http://127.0.0.1:8001',
                api_key TEXT NOT NULL DEFAULT '',
                public_key TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                request_count INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tunnels_device ON tunnels(device_id);
            CREATE INDEX IF NOT EXISTS idx_tunnels_expires ON tunnels(expires_at);

            CREATE TABLE IF NOT EXISTS tunnel_requests (
                id TEXT PRIMARY KEY,
                tunnel_id TEXT NOT NULL REFERENCES tunnels(tunnel_id),
                method TEXT NOT NULL DEFAULT 'GET',
                path TEXT NOT NULL DEFAULT '/',
                headers TEXT NOT NULL DEFAULT '{}',
                body TEXT,
                responded INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_req_tunnel ON tunnel_requests(tunnel_id);
            CREATE INDEX IF NOT EXISTS idx_req_unresponded ON tunnel_requests(tunnel_id, responded);

            CREATE TABLE IF NOT EXISTS tunnel_responses (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE REFERENCES tunnel_requests(id),
                status INTEGER NOT NULL DEFAULT 200,
                body TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cloud_data (
                device_id TEXT NOT NULL,
                data_key TEXT NOT NULL,
                encrypted_payload TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (device_id, data_key)
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                plan TEXT NOT NULL DEFAULT 'free',
                rate_limit INTEGER NOT NULL DEFAULT 60,
                created_at TEXT NOT NULL,
                expires_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_apikeys_plan ON api_keys(plan);
        """)
        conn.commit()

    # ── Tunnel operations ──

    def register_tunnel(
        self, local_base: str, api_key: str = "", device_id: str = "", public_key: str = "",
        ttl_hours: int = 24,
    ) -> TunnelInfo:
        conn = self._conn()
        tid = generate_id("tun_")
        now = utcnow()
        expires = default_expiry(ttl_hours)
        conn.execute(
            "INSERT INTO tunnels (tunnel_id, device_id, local_base, api_key, public_key, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tid, device_id, local_base, api_key, public_key, now, expires),
        )
        conn.commit()
        return TunnelInfo(
            tunnel_id=tid, device_id=device_id, local_base=local_base,
            api_key=api_key, public_key=public_key,
            created_at=now, expires_at=expires, request_count=0,
        )

    def get_tunnel(self, tunnel_id: str) -> Optional[TunnelInfo]:
        row = self._conn().execute(
            "SELECT * FROM tunnels WHERE tunnel_id = ? AND deleted_at IS NULL AND expires_at > ?",
            (tunnel_id, utcnow()),
        ).fetchone()
        if not row:
            return None
        return TunnelInfo(
            tunnel_id=row["tunnel_id"], device_id=row["device_id"],
            local_base=row["local_base"], api_key=row["api_key"],
            public_key=row["public_key"], created_at=row["created_at"],
            expires_at=row["expires_at"], request_count=row["request_count"],
        )

    def delete_tunnel(self, tunnel_id: str) -> None:
        self._conn().execute(
            "UPDATE tunnels SET deleted_at = ? WHERE tunnel_id = ?",
            (utcnow(), tunnel_id),
        )
        self._conn().commit()

    def cleanup_expired(self) -> int:
        conn = self._conn()
        now = utcnow()
        deleted = conn.execute(
            "UPDATE tunnels SET deleted_at = ? WHERE expires_at < ? AND deleted_at IS NULL",
            (now, now),
        ).rowcount
        conn.commit()
        return deleted

    # ── Request queue ──

    def enqueue_request(self, tunnel_id: str, method: str, path: str,
                        headers: Dict = None, body: Any = None) -> str:
        conn = self._conn()
        req_id = generate_id("req_")
        now = utcnow()
        conn.execute(
            "INSERT INTO tunnel_requests (id, tunnel_id, method, path, headers, body, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (req_id, tunnel_id, method, json.dumps(headers or {}),
             json.dumps(body) if body is not None else None, now),
        )
        conn.execute(
            "UPDATE tunnels SET request_count = request_count + 1 WHERE tunnel_id = ?",
            (tunnel_id,),
        )
        conn.commit()
        return req_id

    def poll_requests(self, tunnel_id: str, limit: int = 10) -> List[ProxyRequest]:
        rows = self._conn().execute(
            "SELECT * FROM tunnel_requests WHERE tunnel_id = ? AND responded = 0 ORDER BY created_at ASC LIMIT ?",
            (tunnel_id, limit),
        ).fetchall()
        results = []
        for row in rows:
            results.append(ProxyRequest(
                id=row["id"], method=row["method"], path=row["path"],
                headers=json.loads(row["headers"] or "{}"),
                body=json.loads(row["body"]) if row["body"] else None,
                created_at=row["created_at"],
            ))
        return results

    def mark_responded(self, request_id: str) -> None:
        self._conn().execute(
            "UPDATE tunnel_requests SET responded = 1 WHERE id = ?",
            (request_id,),
        )
        self._conn().commit()

    def save_response(self, request_id: str, status: int, body: Any) -> None:
        conn = self._conn()
        now = utcnow()
        conn.execute(
            "INSERT OR REPLACE INTO tunnel_responses (id, request_id, status, body, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (generate_id("rsp_"), request_id, status,
             json.dumps(body) if body is not None else None, now),
        )
        self.mark_responded(request_id)
        conn.commit()

    # ── Cloud sync ──

    def push_cloud_data(self, device_id: str, data_key: str,
                        encrypted_payload: str, version: int = 1) -> CloudData:
        conn = self._conn()
        now = utcnow()
        existing = conn.execute(
            "SELECT version FROM cloud_data WHERE device_id = ? AND data_key = ?",
            (device_id, data_key),
        ).fetchone()
        new_version = (existing["version"] if existing else 0) + 1
        if version > 0:
            new_version = version
        conn.execute(
            "INSERT OR REPLACE INTO cloud_data (device_id, data_key, encrypted_payload, version, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (device_id, data_key, encrypted_payload, new_version, now),
        )
        conn.commit()
        return CloudData(
            device_id=device_id, data_key=data_key,
            encrypted_payload=encrypted_payload, version=new_version, updated_at=now,
        )

    def pull_cloud_data(self, device_id: str, data_keys: List[str] = None) -> List[CloudData]:
        if data_keys:
            placeholders = ",".join("?" * len(data_keys))
            rows = self._conn().execute(
                f"SELECT * FROM cloud_data WHERE device_id = ? AND data_key IN ({placeholders})",
                [device_id] + data_keys,
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM cloud_data WHERE device_id = ?",
                (device_id,),
            ).fetchall()
        return [
            CloudData(
                device_id=r["device_id"], data_key=r["data_key"],
                encrypted_payload=r["encrypted_payload"], version=r["version"],
                updated_at=r["updated_at"],
            ) for r in rows
        ]

    def list_device_keys(self, device_id: str) -> List[str]:
        rows = self._conn().execute(
            "SELECT data_key FROM cloud_data WHERE device_id = ?",
            (device_id,),
        ).fetchall()
        return [r["data_key"] for r in rows]

    # ── API keys ──

    def register_api_key(self, key: str, plan: str = "free",
                         rate_limit: int = 60, expires_at: str = "") -> bool:
        try:
            self._conn().execute(
                "INSERT INTO api_keys (key, plan, rate_limit, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                (key, plan, rate_limit, utcnow(), expires_at or None),
            )
            self._conn().commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def validate_api_key(self, key: str) -> Optional[Dict]:
        row = self._conn().execute(
            "SELECT * FROM api_keys WHERE key = ?",
            (key,),
        ).fetchone()
        if not row:
            return None
        if row["expires_at"] and row["expires_at"] < utcnow():
            return None
        return {"key": row["key"], "plan": row["plan"], "rate_limit": row["rate_limit"]}
