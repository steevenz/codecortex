"""
File.

:project: CodeCortex
:package: Modules.Coderepository.Core.Models.File
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import Integer, Text, Boolean, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.orm import BaseModel, TimestampMixin, UUIDMixin


class File(BaseModel, UUIDMixin, TimestampMixin):
    __tablename__ = "files"
    __allow_unmapped__ = True
    __table_args__ = (
        UniqueConstraint("repository_id", "directory_id", "name", name="uq_files_repo_dir_name"),
    )

    repository_id: Mapped[str] = mapped_column(default="", index=True)
    directory_id: Mapped[Optional[str]] = mapped_column(default=None, index=True)
    name: Mapped[str] = mapped_column(default="")
    relative_path: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(default=0)
    classification: Mapped[str] = mapped_column(default="code")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    content_hash: Mapped[Optional[str]] = mapped_column(default=None)
    mtime: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["File"]:
        if data is None:
            return None
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
