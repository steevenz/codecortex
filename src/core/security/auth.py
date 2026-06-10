"""
CodeCortex Auth Service
Zero-Trust Handshake & API Key Validation

:project: CodeCortex
:package: Core.Security.Auth
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
"""

import json
import secrets
import sqlite3
import threading
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()

@dataclass(slots=True)
class AuthResult:
    ok: bool
    code: int
    message: str
    principal: Optional[Dict[str, Any]] = None

class AuthService:
    """Authentication service for CodeCortex MCP clients.

    - Validates static API keys (CLIENT_API_KEY).
    - Validates operational keys generated via Handshake.
    - Persists audit logs in SQLite.
    """

    def __init__(self, conn: sqlite3.Connection, client_api_key: str) -> None:
        self.conn = conn
        self.client_api_key = client_api_key
        self._write_lock = threading.Lock()
        self._init_tables()

    def _init_tables(self) -> None:
        with self._write_lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_audit_logs (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    request_id TEXT,
                    llm_instance_id TEXT,
                    key_id TEXT,
                    ip TEXT,
                    result TEXT NOT NULL,
                    reason_code TEXT,
                    created_at TEXT NOT NULL,
                    data_json TEXT
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_api_keys (
                    key_id TEXT PRIMARY KEY,
                    api_key_hash TEXT NOT NULL,
                    llm_instance_id TEXT NOT NULL,
                    scopes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    is_active INTEGER DEFAULT 1
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_handshakes (
                    handshake_id TEXT PRIMARY KEY,
                    llm_instance_id TEXT NOT NULL,
                    challenge TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
            self.conn.commit()

    def _audit(
        self,
        event_type: str,
        *,
        result: str,
        request_id: str = "",
        llm_instance_id: str = "",
        key_id: str = "",
        ip: str = "",
        reason_code: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._write_lock:
            self.conn.execute(
                """
                INSERT INTO auth_audit_logs (
                    event_id, event_type, request_id, llm_instance_id, key_id,
                    ip, result, reason_code, created_at, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"evt_{secrets.token_hex(8)}",
                    event_type,
                    request_id or None,
                    llm_instance_id or None,
                    key_id or None,
                    ip or None,
                    result,
                    reason_code or None,
                    _iso(_utc_now()),
                    json.dumps(data or {}, ensure_ascii=True),
                ),
            )
            self.conn.commit()

    def validate_api_key(
        self, presented_key: str, required_scope: Optional[str] = None, *, request_id: str = "", ip: str = ""
    ) -> AuthResult:
        if not presented_key:
            return AuthResult(False, 403, "missing_api_key")

        # Fallback / Static Root Key Validation
        is_root = False
        if self.client_api_key and secrets.compare_digest(presented_key, self.client_api_key):
            is_root = True

        principal = None
        if is_root:
            principal = {
                "auth_type": "root_api_key",
                "llm_instance_id": "root-client",
                "scopes": ["mcp:sync", "mcp:sse", "admin:revoke", "handshake"],
            }
        else:
            # Check issued keys in database
            key_hash = hashlib.sha256(presented_key.encode("utf-8")).hexdigest()
            row = self.conn.execute(
                "SELECT key_id, llm_instance_id, scopes, expires_at FROM llm_api_keys WHERE api_key_hash = ? AND is_active = 1",
                (key_hash,)
            ).fetchone()
            if row:
                if row["expires_at"] and _iso(_utc_now()) > row["expires_at"]:
                    self._audit("AUTH_VALIDATE", result="denied", request_id=request_id, ip=ip, reason_code="expired_key")
                    return AuthResult(False, 403, "expired_key")
                
                scopes = json.loads(row["scopes"])
                principal = {
                    "auth_type": "issued_api_key",
                    "llm_instance_id": row["llm_instance_id"],
                    "scopes": scopes,
                    "key_id": row["key_id"]
                }
            else:
                self._audit("AUTH_VALIDATE", result="denied", request_id=request_id, ip=ip, reason_code="invalid_key")
                return AuthResult(False, 403, "invalid_api_key")

        if required_scope and required_scope not in principal["scopes"]:
            self._audit(
                "AUTH_VALIDATE",
                result="denied",
                request_id=request_id,
                ip=ip,
                reason_code="insufficient_scope",
            )
            return AuthResult(False, 403, "insufficient_scope")

        return AuthResult(True, 200, "ok", principal)

    def handshake_init(self, llm_instance_id: str, client_nonce: str) -> Dict[str, str]:
        """Generates handshake initiation parameters."""
        handshake_id = f"hs_{secrets.token_hex(12)}"
        challenge = secrets.token_hex(16)
        server_nonce = secrets.token_hex(8)
        
        with self._write_lock:
            self.conn.execute(
                "INSERT INTO auth_handshakes (handshake_id, llm_instance_id, challenge, created_at, status) VALUES (?, ?, ?, ?, ?)",
                (handshake_id, llm_instance_id, challenge, _iso(_utc_now()), "pending")
            )
            self.conn.commit()

        return {
            "handshake_id": handshake_id,
            "challenge": challenge,
            "server_nonce": server_nonce
        }

    def handshake_complete(self, handshake_id: str, client_proof: str) -> AuthResult:
        """Verifies proof and issues a new operational API key."""
        row = self.conn.execute(
            "SELECT llm_instance_id, challenge, status FROM auth_handshakes WHERE handshake_id = ?",
            (handshake_id,)
        ).fetchone()

        if not row or row["status"] != "pending":
            return AuthResult(False, 400, "invalid_or_expired_handshake")

        llm_instance_id = row["llm_instance_id"]
        challenge = row["challenge"]

        # Expected proof: HMAC-SHA256(CLIENT_API_KEY, "handshake_id:ide:challenge")
        material = f"{handshake_id}:{llm_instance_id}:{challenge}".encode("utf-8")
        expected_proof = hmac.new(self.client_api_key.encode("utf-8"), material, hashlib.sha256).hexdigest()

        if not secrets.compare_digest(client_proof, expected_proof):
            self._audit("HANDSHAKE", result="denied", llm_instance_id=llm_instance_id, reason_code="invalid_proof")
            return AuthResult(False, 403, "invalid_proof")

        # Mark handshake as complete
        with self._write_lock:
            self.conn.execute("UPDATE auth_handshakes SET status = 'completed' WHERE handshake_id = ?", (handshake_id,))

        # Issue new key
        new_api_key = f"cog_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(new_api_key.encode("utf-8")).hexdigest()
        key_id = f"key_{secrets.token_hex(8)}"
        scopes = json.dumps(["mcp:sync", "mcp:sse"])
        
        with self._write_lock:
            self.conn.execute(
                """
                INSERT INTO llm_api_keys (key_id, api_key_hash, llm_instance_id, scopes, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (key_id, key_hash, llm_instance_id, scopes, _iso(_utc_now()))
            )
            self.conn.commit()

        self._audit("HANDSHAKE", result="success", llm_instance_id=llm_instance_id, key_id=key_id)
        
        return AuthResult(True, 200, "ok", {
            "api_key": new_api_key,
            "key_id": key_id,
            "llm_instance_id": llm_instance_id
        })
