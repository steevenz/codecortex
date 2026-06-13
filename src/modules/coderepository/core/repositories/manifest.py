"""
Manifest.

:project: CodeCortex
:package: Modules.Coderepository.Core.Repositories.Manifest
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from src.core.database.orm import SessionManager
from src.modules.coderepository.core.models import ManifestEntry


class ManifestEntryRepository:
    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager

    def get_by_path(self, repository_id: str, file_path: str) -> Optional[ManifestEntry]:
        with self._session_manager.get_session() as session:
            return session.execute(
                select(ManifestEntry).where(
                    ManifestEntry.repository_id == repository_id,
                    ManifestEntry.file_path == file_path
                )
            ).scalar_one_or_none()

    def list_by_repository(self, repository_id: str) -> List[ManifestEntry]:
        with self._session_manager.get_session() as session:
            return session.execute(
                select(ManifestEntry).where(ManifestEntry.repository_id == repository_id)
            ).scalars().all()

    def create_or_update(self, repository_id: str, file_path: str, data: dict) -> ManifestEntry:
        with self._session_manager.get_session() as session:
            existing = session.execute(
                select(ManifestEntry).where(
                    ManifestEntry.repository_id == repository_id,
                    ManifestEntry.file_path == file_path
                )
            ).scalar_one_or_none()
            if existing:
                for key, value in data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                return existing
            instance = ManifestEntry.from_dict({
                "repository_id": repository_id,
                "file_path": file_path,
                **data
            })
            session.add(instance)
            session.flush()
            return instance
