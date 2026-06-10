"""
Directory.

:project: CodeCortex
:package: Modules.Coderepository.Core.Repositories.Directory
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from src.core.database.orm import SessionManager
from src.modules.coderepository.core.models import Directory


class DirectoryRepository:
    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager

    def get_by_id(self, id: str) -> Optional[Directory]:
        with self._session_manager.get_session() as session:
            return session.get(Directory, id)

    def get_by_path(self, repository_id: str, relative_path: str) -> Optional[Directory]:
        with self._session_manager.get_session() as session:
            return session.execute(
                select(Directory).where(
                    Directory.repository_id == repository_id,
                    Directory.relative_path == relative_path
                )
            ).scalar_one_or_none()

    def create(self, data: dict) -> Directory:
        with self._session_manager.get_session() as session:
            instance = Directory.from_dict(data)
            session.add(instance)
            session.flush()
            return instance
