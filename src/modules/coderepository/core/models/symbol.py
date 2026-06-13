"""
Symbol.

:project: CodeCortex
:package: Modules.Coderepository.Core.Models.Symbol
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.orm import BaseModel, TimestampMixin, UUIDMixin


class Symbol(BaseModel, UUIDMixin, TimestampMixin):
    __tablename__ = "symbols"
    __allow_unmapped__ = True

    repository_id: Mapped[str] = mapped_column(default="", index=True)
    file_id: Mapped[str] = mapped_column(default="", index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(default=None, index=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(default="")
    symbol_type: Mapped[str] = mapped_column(default="")
    start_line: Mapped[int] = mapped_column(default=0)
    end_line: Mapped[int] = mapped_column(default=0)
    signature: Mapped[Optional[str]] = mapped_column(default=None)
    docstring: Mapped[Optional[str]] = mapped_column(default=None)
    metadata_json: Mapped[Optional[str]] = mapped_column("metadata", Text, default=None)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["Symbol"]:
        if data is None:
            return None
        instance = cls()
        for key, value in data.items():
            if key == "metadata":
                key = "metadata_json"
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def to_dict(self) -> Dict[str, Any]:
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if "metadata_json" in result:
            result["metadata"] = result.pop("metadata_json")
        return result
