"""
Repository.

:project: CodeCortex
:package: Modules.Coderepository.Core.Repositories.Repository
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select

from src.core.database.orm import SessionManager
from src.modules.coderepository.core.models import Repository


class RepositoryRepository:
    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager

    def get_by_id(self, id: str) -> Optional[Repository]:
        with self._session_manager.get_session() as session:
            return session.get(Repository, id)

    def get_by_path(self, root_path: str) -> Optional[Repository]:
        with self._session_manager.get_session() as session:
            return session.execute(
                select(Repository).where(Repository.root_path == root_path)
            ).scalar_one_or_none()

    def get_by_path_ci(self, root_path: str) -> Optional[Repository]:
        """Case-insensitive path lookup (important on Windows)."""
        normalized = root_path.lower().replace("\\", "/").rstrip("/")
        candidates = self.get_all(limit=500)
        for r in candidates:
            rp = (r.root_path or "").lower().replace("\\", "/").rstrip("/")
            if rp == normalized:
                return r
        return None

    def get_by_remote_url(self, remote_url: str) -> Optional[Repository]:
        if not remote_url:
            return None
        with self._session_manager.get_session() as session:
            return session.execute(
                select(Repository).where(
                    Repository.vcs_url == remote_url,
                    Repository.vcs_url.isnot(None),
                    Repository.vcs_url != "",
                )
            ).scalar_one_or_none()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Repository]:
        with self._session_manager.get_session() as session:
            return session.execute(
                select(Repository).limit(limit).offset(offset)
            ).scalars().all()

    def create(self, data: Dict[str, Any]) -> Repository:
        with self._session_manager.get_session() as session:
            instance = Repository.from_dict(data)
            session.add(instance)
            session.flush()
            return instance

    def update(self, id: str, data: Dict[str, Any]) -> Optional[Repository]:
        with self._session_manager.get_session() as session:
            instance = session.get(Repository, id)
            if instance is None:
                return None
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            session.flush()
            return instance

    def delete(self, id: str) -> bool:
        with self._session_manager.get_session() as session:
            instance = session.get(Repository, id)
            if instance is None:
                return False
            session.delete(instance)
            session.flush()
            return True
