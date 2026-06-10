"""
Directory.

:project: CodeCortex
:package: Modules.Coderepository.Core.Models.Directory
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.orm import BaseModel, TimestampMixin, UUIDMixin


class Directory(BaseModel, UUIDMixin, TimestampMixin):
    __tablename__ = "directories"
    __allow_unmapped__ = True
    __table_args__ = (
        UniqueConstraint("repository_id", "relative_path", name="uq_directories_repo_path"),
    )

    repository_id: Mapped[str] = mapped_column(default="", index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(default=None)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["Directory"]:
        if data is None:
            return None
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
