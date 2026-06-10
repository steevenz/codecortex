"""
@project   CodeCortex
@package   modules.idegraph.domain
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.domain
:standard: Aegis-IdeGraph-v1.0

Engram — Unified domain model for AI interaction memories across all IDEs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import hashlib

@dataclass
class IDEInfo:
    """Canonical metadata describing the IDE source of an Engram."""
    name: str                      # e.g. 'cursor', 'trae', 'gemini'
    type: str                      # e.g. 'vscode-extension', 'cli', 'desktop', 'web'
    installation_path: Optional[str] = None
    version: Optional[str] = None
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "installation_path": self.installation_path,
            "version": self.version,
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IDEInfo':
        return cls(
            name=data.get('name', 'unknown'),
            type=data.get('type', 'unknown'),
            installation_path=data.get('installation_path'),
            version=data.get('version'),
            detected_at=data.get('detected_at', datetime.now().isoformat()),
        )

@dataclass
class Message:
    role: str
    content: str
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    code_context: List[Dict[str, Any]] = field(default_factory=list)
    tool_use: List[Dict[str, Any]] = field(default_factory=list)
    diffs: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.content, str):
            if isinstance(self.content, list):
                self.content = "\n".join(str(v) for v in self.content if v is not None)
            else:
                self.content = str(self.content) if self.content is not None else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "code_context": self.code_context,
            "tool_use": self.tool_use,
            "diffs": self.diffs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        raw_content = data.get('content', '')
        if isinstance(raw_content, list):
            content = "\n".join([str(i) for i in raw_content])
        else:
            content = str(raw_content or "")
        return cls(
            role=data.get('role', 'unknown'),
            content=content,
            timestamp=data.get('timestamp'),
            metadata=data.get('metadata', {}) if isinstance(data.get('metadata'), dict) else {},
            code_context=data.get('code_context', []),
            tool_use=data.get('tool_use', []),
            diffs=data.get('diffs', []),
        )

@dataclass
class Engram:
    """A semantic memory trace from an AI interaction."""
    id: str
    source: str  # 'trae', 'cursor', 'gemini', etc.
    source_file: str
    messages: List[Message]
    created_at: datetime = field(default_factory=datetime.now)
    workspace_id: Optional[str] = None
    project_path: Optional[str] = None
    project_name: Optional[str] = None
    title: Optional[str] = None
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    ide_info: Optional[IDEInfo] = None

    @staticmethod
    def _normalize_workspace_value(value: str) -> str:
        v = (value or "").strip().lower()
        v = v.replace("\\", "/")
        while "//" in v:
            v = v.replace("//", "/")
        if v.endswith("/"):
            v = v[:-1]
        return v

    @classmethod
    def compute_workspace_key(
        cls,
        *,
        project_path: Optional[str],
        project_name: Optional[str],
        workspace_id: Optional[str],
        source_file: str,
    ) -> str:
        if project_path:
            return hashlib.sha256(cls._normalize_workspace_value(project_path).encode("utf-8", errors="ignore")).hexdigest()
        if project_name and not cls._normalize_workspace_value(project_name).startswith("unknown-"):
            return hashlib.sha256(cls._normalize_workspace_value(project_name).encode("utf-8", errors="ignore")).hexdigest()
        if workspace_id:
            return hashlib.sha256(cls._normalize_workspace_value(workspace_id).encode("utf-8", errors="ignore")).hexdigest()
        return hashlib.sha256(cls._normalize_workspace_value(source_file).encode("utf-8", errors="ignore")).hexdigest()

    def to_summary_record(
        self,
        *,
        request_id: str,
        version: str,
        api_version: str = "v1",
    ) -> Dict[str, Any]:
        """Return summary record without full message content (for token efficiency)."""
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        workspace_key = self.compute_workspace_key(
            project_path=self.project_path,
            project_name=self.project_name,
            workspace_id=self.workspace_id,
            source_file=self.source_file,
        )
        # Summary: message count only, first 100 chars of first message
        first_snippet = ""
        if self.messages:
            first_content = self.messages[0].content or ""
            first_snippet = first_content[:100] + ("..." if len(first_content) > 100 else "")
        attrs: Dict[str, Any] = {
            "source": self.source,
            "source_file": self.source_file,
            "created_at": self.created_at.isoformat(),
            "workspace_id": self.workspace_id,
            "workspace_key": workspace_key,
            "project_path": self.project_path,
            "project_name": self.project_name,
            "title": self.title,
            "model": self.model,
            "ide_info": self.ide_info.to_dict() if self.ide_info else None,
            "message_count": len(self.messages),
            "first_message_snippet": first_snippet,
            "metadata": self.metadata,
        }
        return {
            "success": True,
            "status_code": 200,
            "message": "engram_summary_record",
            "data": {
                "type": "engram_summary",
                "id": self.id,
                "attributes": attrs,
            },
            "meta": {
                "user_id": None,
                "tenant_id": None,
                "organization_id": None,
                "workspace_id": self.workspace_id,
                "request_id": request_id,
                "timestamp": ts,
                "version": version,
                "api_version": api_version,
                "error_code": None,
            },
        }

    def to_export_record(
        self,
        *,
        request_id: str,
        version: str,
        api_version: str = "v1",
    ) -> Dict[str, Any]:
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        workspace_key = self.compute_workspace_key(
            project_path=self.project_path,
            project_name=self.project_name,
            workspace_id=self.workspace_id,
            source_file=self.source_file,
        )
        attrs: Dict[str, Any] = {
            "source": self.source,
            "source_file": self.source_file,
            "created_at": self.created_at.isoformat(),
            "workspace_id": self.workspace_id,
            "workspace_key": workspace_key,
            "project_path": self.project_path,
            "project_name": self.project_name,
            "title": self.title,
            "model": self.model,
            "ide_info": self.ide_info.to_dict() if self.ide_info else None,
            "messages": [m.to_dict() for m in self.messages],
            "conversations": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }
        return {
            "success": True,
            "status_code": 200,
            "message": "engram_export_record",
            "data": {
                "type": "engram",
                "id": self.id,
                "attributes": attrs,
            },
            "meta": {
                "user_id": None,
                "tenant_id": None,
                "organization_id": None,
                "workspace_id": self.workspace_id,
                "request_id": request_id,
                "timestamp": ts,
                "version": version,
                "api_version": api_version,
                "error_code": None,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "source_file": self.source_file,
            "created_at": self.created_at.isoformat(),
            "workspace_id": self.workspace_id,
            "project_path": self.project_path,
            "project_name": self.project_name,
            "title": self.title,
            "model": self.model,
            "ide_info": self.ide_info.to_dict() if self.ide_info else None,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Engram':
        if isinstance(data.get("data"), dict) and isinstance(data["data"].get("attributes"), dict):
            attributes = data["data"]["attributes"]
            hydrated = dict(attributes)
            hydrated["id"] = data["data"].get("id") or attributes.get("id")
            data = hydrated

        raw_messages = data.get("messages", [])
        if not raw_messages and isinstance(data.get("conversations"), list):
            raw_messages = data.get("conversations", [])
        messages = [Message.from_dict(m) for m in raw_messages]

        # Backward-compatible IDEInfo parsing
        ide_info = None
        raw_ide = data.get('ide_info')
        if raw_ide and isinstance(raw_ide, dict):
            ide_info = IDEInfo.from_dict(raw_ide)
        elif raw_ide is None and data.get('source'):
            # Graceful fallback: reconstruct from legacy `source` field
            ide_info = IDEInfo(
                name=data.get('source', 'unknown'),
                type='unknown',
            )

        # Validate required fields with safe fallbacks
        engram_id = data.get('id', '')
        if not engram_id or not isinstance(engram_id, str):
            engram_id = f"engram-{datetime.now().isoformat()}"

        source = data.get('source', 'unknown')
        if not isinstance(source, str):
            source = 'unknown'

        source_file = data.get('source_file', '')
        if not isinstance(source_file, str):
            source_file = ''

        # Safe datetime parsing with fallback
        created_at = datetime.now()
        raw_created = data.get('created_at')
        if raw_created and isinstance(raw_created, str):
            try:
                created_at = datetime.fromisoformat(raw_created)
            except (ValueError, TypeError):
                pass

        return cls(
            id=engram_id,
            source=source,
            source_file=source_file,
            messages=messages,
            created_at=created_at,
            workspace_id=data.get('workspace_id'),
            project_path=data.get('project_path'),
            project_name=data.get('project_name'),
            title=data.get('title'),
            model=data.get('model'),
            metadata=data.get('metadata', {}) if isinstance(data.get('metadata'), dict) else {},
            ide_info=ide_info,
        )
