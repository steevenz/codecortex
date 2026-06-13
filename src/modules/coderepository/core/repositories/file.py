"""
File.

:project: CodeCortex
:package: Modules.Coderepository.Core.Repositories.File
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from src.core.database.orm import SessionManager
from src.modules.coderepository.core.models import File


class FileRepository:
    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager

    def get_by_id(self, id: str) -> Optional[File]:
        with self._session_manager.get_session() as session:
            return session.get(File, id)

    def list_by_repository(self, repository_id: str, include_deleted: bool = False) -> List[File]:
        with self._session_manager.get_session() as session:
            stmt = select(File).where(File.repository_id == repository_id)
            if not include_deleted:
                stmt = stmt.where(File.is_deleted == "0")
            return session.execute(stmt).scalars().all()

    def create(self, data: dict) -> File:
        with self._session_manager.get_session() as session:
            instance = File.from_dict(data)
            session.add(instance)
            session.flush()
            return instance

    def update(self, id: str, data: dict) -> Optional[File]:
        with self._session_manager.get_session() as session:
            instance = session.get(File, id)
            if instance is None:
                return None
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            session.flush()
            return instance
