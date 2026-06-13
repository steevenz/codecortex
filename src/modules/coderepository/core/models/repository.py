"""
Repository.

:project: CodeCortex
:package: Modules.Coderepository.Core.Models.Repository
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.orm import BaseModel, TimestampMixin, UUIDMixin


class Repository(BaseModel, UUIDMixin, TimestampMixin):
    __tablename__ = "repositories"
    __allow_unmapped__ = True

    name: Mapped[str] = mapped_column(default="")
    root_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    vcs_type: Mapped[str] = mapped_column(default="git")
    vcs_url: Mapped[Optional[str]] = mapped_column(default=None)
    sync_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    total_files: Mapped[int] = mapped_column(default=0)
    total_symbols: Mapped[int] = mapped_column(default=0)
    total_edges: Mapped[int] = mapped_column(default=0)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["Repository"]:
        if data is None:
            return None
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
