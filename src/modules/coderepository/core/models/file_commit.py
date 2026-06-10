"""
File Commit.

:project: CodeCortex
:package: Modules.Coderepository.Core.Models.File_commit
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.orm import BaseModel, UUIDMixin


class FileCommit(BaseModel, UUIDMixin):
    __tablename__ = "file_commits"
    __allow_unmapped__ = True
    __table_args__ = (
        UniqueConstraint("file_id", "commit_id", name="uq_file_commits_file_commit"),
    )

    repository_id: Mapped[str] = mapped_column(default="", index=True)
    file_id: Mapped[str] = mapped_column(default="", index=True)
    commit_id: Mapped[str] = mapped_column(default="", index=True)
    change_type: Mapped[str] = mapped_column(default="modified")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["FileCommit"]:
        if data is None:
            return None
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
