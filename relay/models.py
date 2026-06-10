"""
Relay Server — cloud sync relay + tunnel proxy for CodeCortex.

Zero-cost infrastructure: SQLite-backed, single binary, deploy anywhere.
Paid tier adds API key auth, rate limits, and priority queues.

Architecture:
  - Tunnel: SSE polling (no WebSocket dep), 24h TTL auto-cleanup
  - Cloud Sync: Git-style push/pull with E2E encryption
  - Auth: API key for paid tier, open for self-hosted

:project: CodeCortex Relay
:package: Relay.Models
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework (Paid) / MIT (Open Source)
:standard: Aegis-CrossStack-v1.0
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class TunnelRegistration(BaseModel):
    local_base: str = "http://127.0.0.1:8001"
    api_key: str = ""
    device_id: str = ""
    public_key: str = ""


class TunnelInfo(BaseModel):
    tunnel_id: str
    device_id: str
    local_base: str
    api_key: str
    public_key: str
    created_at: str
    expires_at: str
    request_count: int = 0


class ProxyRequest(BaseModel):
    id: str
    method: str = "GET"
    path: str = "/"
    headers: Dict[str, str] = {}
    body: Optional[Any] = None
    created_at: str = ""


class ProxyResponse(BaseModel):
    id: str
    status: int = 200
    body: Any = None


class CloudPushRequest(BaseModel):
    device_id: str
    data_key: str
    encrypted_payload: str
    version: int = 1


class CloudPullRequest(BaseModel):
    device_id: str
    data_keys: Optional[List[str]] = None


class CloudData(BaseModel):
    device_id: str
    data_key: str
    encrypted_payload: str
    version: int
    updated_at: str


class ApiKeyRegistration(BaseModel):
    key: str
    plan: str = "free"
    rate_limit: int = 60
    expires_at: Optional[str] = None


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def default_expiry(hours: int = 24) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
