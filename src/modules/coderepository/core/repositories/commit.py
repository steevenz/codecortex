"""
Commit.

:project: CodeCortex
:package: Modules.Coderepository.Core.Repositories.Commit
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from src.core.database.orm import SessionManager
from src.modules.coderepository.core.models import Commit


class CommitRepository:
    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager

    def get_by_hash(self, repository_id: str, commit_hash: str) -> Optional[Commit]:
        with self._session_manager.get_session() as session:
            return session.execute(
                select(Commit).where(
                    Commit.repository_id == repository_id,
                    Commit.commit_hash == commit_hash
                )
            ).scalar_one_or_none()

    def create(self, data: dict) -> Commit:
        with self._session_manager.get_session() as session:
            instance = Commit.from_dict(data)
            session.add(instance)
            session.flush()
            return instance
