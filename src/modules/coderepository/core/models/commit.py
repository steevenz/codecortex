"""
Commit.

:project: CodeCortex
:package: Modules.Coderepository.Core.Models.Commit
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.orm import BaseModel, TimestampMixin, UUIDMixin


class Commit(BaseModel, UUIDMixin, TimestampMixin):
    __tablename__ = "commits"
    __allow_unmapped__ = True
    __table_args__ = (
        UniqueConstraint("repository_id", "commit_hash", name="uq_commits_repo_hash"),
    )

    repository_id: Mapped[str] = mapped_column(default="", index=True)
    commit_hash: Mapped[str] = mapped_column(default="", index=True)
    author_name: Mapped[Optional[str]] = mapped_column(default=None)
    author_email: Mapped[Optional[str]] = mapped_column(default=None)
    message: Mapped[Optional[str]] = mapped_column(Text, default=None)
    committed_at: Mapped[Optional[str]] = mapped_column(default=None)
    parent_hash: Mapped[Optional[str]] = mapped_column(Text, default=None)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["Commit"]:
        if data is None:
            return None
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
