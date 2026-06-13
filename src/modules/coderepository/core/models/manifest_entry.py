"""
Manifest Entry.

:project: CodeCortex
:package: Modules.Coderepository.Core.Models.Manifest_entry
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.orm import BaseModel, TimestampMixin, UUIDMixin


class ManifestEntry(BaseModel, UUIDMixin, TimestampMixin):
    __tablename__ = "manifest_entries"
    __allow_unmapped__ = True
    __table_args__ = (
        UniqueConstraint("repository_id", "file_path", name="uq_manifest_repo_path"),
    )

    repository_id: Mapped[str] = mapped_column(default="", index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(default="")
    last_size_bytes: Mapped[int] = mapped_column(default=0)
    mtime: Mapped[Optional[str]] = mapped_column(default=None)
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["ManifestEntry"]:
        if data is None:
            return None
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
