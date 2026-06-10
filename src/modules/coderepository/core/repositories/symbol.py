"""
Symbol.

:project: CodeCortex
:package: Modules.Coderepository.Core.Repositories.Symbol
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from src.core.database.orm import SessionManager
from src.modules.coderepository.core.models import Symbol


class SymbolRepository:
    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager

    def get_by_id(self, id: str) -> Optional[Symbol]:
        with self._session_manager.get_session() as session:
            return session.get(Symbol, id)

    def list_by_file(self, file_id: str) -> List[Symbol]:
        with self._session_manager.get_session() as session:
            return session.execute(
                select(Symbol).where(Symbol.file_id == file_id)
            ).scalars().all()

    def create(self, data: dict) -> Symbol:
        with self._session_manager.get_session() as session:
            instance = Symbol.from_dict(data)
            session.add(instance)
            session.flush()
            return instance

    def create_many(self, data_list: List[dict]) -> List[Symbol]:
        with self._session_manager.get_session() as session:
            instances = [Symbol.from_dict(data) for data in data_list]
            session.add_all(instances)
            session.flush()
            return instances
