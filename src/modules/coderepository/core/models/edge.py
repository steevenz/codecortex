"""
Edge.

:project: CodeCortex
:package: Modules.Coderepository.Core.Models.Edge
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.orm import BaseModel, UUIDMixin


class Edge(BaseModel, UUIDMixin):
    __tablename__ = "edges"
    __allow_unmapped__ = True

    repository_id: Mapped[str] = mapped_column(default="", index=True)
    source_id: Mapped[str] = mapped_column(default="")
    target_id: Mapped[str] = mapped_column(default="")
    relation_type: Mapped[str] = mapped_column(default="")
    weight: Mapped[float] = mapped_column(default=1.0)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["Edge"]:
        if data is None:
            return None
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
