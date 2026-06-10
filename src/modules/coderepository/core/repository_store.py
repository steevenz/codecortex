"""
Repository Store.

:project: CodeCortex
:package: Modules.Coderepository.Core.Repository_store
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, ContextManager, Dict, List, Optional

from src.core.database import DatabaseManager
from src.core.database.orm import SessionManager
from src.modules.coderepository.core.repositories import (
    RepositoryRepository,
    FileRepository,
    DirectoryRepository,
    ManifestEntryRepository,
    CommitRepository,
)
from src.modules.coderepository.core.store import ICodeRepositoryStore


class RepositoryStore(ICodeRepositoryStore):
    def __init__(self, db: DatabaseManager):
        self._db = db
        self._session_manager = SessionManager()
        self._repo_repo = RepositoryRepository(self._session_manager)
        self._file_repo = FileRepository(self._session_manager)
        self._dir_repo = DirectoryRepository(self._session_manager)
        self._manifest_repo = ManifestEntryRepository(self._session_manager)
        self._commit_repo = CommitRepository(self._session_manager)

    @contextmanager
    def transaction(self) -> ContextManager[Any]:
        with self._session_manager.get_session() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def get_repository(self, repo_id: str) -> Optional[Dict[str, Any]]:
        instance = self._repo_repo.get_by_id(repo_id)
        return instance.to_dict() if instance else None

    def get_repository_by_path(self, root_path: str) -> Optional[Dict[str, Any]]:
        instance = self._repo_repo.get_by_path(root_path)
        return instance.to_dict() if instance else None

    def list_repositories(self) -> List[Dict[str, Any]]:
        instances = self._repo_repo.get_all()
        return [i.to_dict() for i in instances]

    def upsert_repository(self, name: str, root_path: str, repo_id: Optional[str] = None,
                          vcs_metadata: Optional[Dict[str, Any]] = None,
                          remote_url: Optional[str] = None) -> str:
        normalized = str(Path(root_path).resolve())
        existing = self._repo_repo.get_by_path_ci(normalized)
        if existing:
            url = remote_url or (vcs_metadata or {}).get("vcs_url")
            if url and not existing.vcs_url:
                self._db.conn.execute(
                    "UPDATE repositories SET vcs_url = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (url, existing.id),
                )
                self._db.conn.commit()
            return existing.id

        url = remote_url or (vcs_metadata or {}).get("vcs_url") if vcs_metadata else None
        if url:
            matched = self._repo_repo.get_by_remote_url(url)
            if matched:
                self._db.conn.execute(
                    "UPDATE repositories SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (matched.id,),
                )
                self._db.conn.commit()
                return matched.id

        data = {
            "name": name,
            "root_path": normalized,
            "vcs_type": (vcs_metadata or {}).get("vcs_type", "git"),
            "vcs_url": url,
            "sync_at": datetime.utcnow(),
        }
        instance = self._repo_repo.create(data)
        return instance.id

    def update_indexing_time(self, repo_id: str):
        self._repo_repo.update(repo_id, {"sync_at": datetime.utcnow()})

    def get_directory_id(self, repo_id: str, relative_path: str) -> Optional[str]:
        instance = self._dir_repo.get_by_path(repo_id, relative_path)
        return instance.id if instance else None

    def ensure_directory_chain(self, repo_id: str, relative_path: str) -> str:
        if not relative_path:
            return self._get_or_create_root_directory(repo_id)
        paths = relative_path.replace("\\", "/").split("/")
        current_path = ""
        dir_id = self._get_or_create_root_directory(repo_id)
        for part in paths:
            current_path = f"{current_path}/{part}" if current_path else part
            existing = self._dir_repo.get_by_path(repo_id, current_path)
            if existing:
                dir_id = existing.id
            else:
                instance = self._dir_repo.create({
                    "repository_id": repo_id,
                    "parent_id": dir_id,
                    "relative_path": current_path,
                })
                dir_id = instance.id
        return dir_id

    def _get_or_create_root_directory(self, repo_id: str) -> str:
        instance = self._dir_repo.get_by_path(repo_id, "")
        if instance:
            return instance.id
        return self._dir_repo.create({
            "repository_id": repo_id,
            "parent_id": None,
            "relative_path": "",
        }).id

    def list_files(self, repo_id: str, directory_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if directory_id:
            instances = self._file_repo.list_by_repository(repo_id)
        else:
            instances = self._file_repo.list_by_repository(repo_id)
        return [i.to_dict() for i in instances]

    def get_manifest_entry(self, repo_id: str, file_path: str) -> Optional[Dict[str, Any]]:
        instance = self._manifest_repo.get_by_path(repo_id, file_path)
        return instance.to_dict() if instance else None

    def upsert_file_and_manifest(self, file_data: Dict[str, Any], manifest_data: Dict[str, Any]):
        self._file_repo.create(file_data)
        self._manifest_repo.create_or_update(
            repo_id=file_data["repository_id"],
            file_path=manifest_data["file_path"],
            data=manifest_data,
        )

    def upsert_commit(self, commit_data: Dict[str, Any]):
        self._commit_repo.create(commit_data)

    def get_commit_id(self, repo_id: str, commit_hash: str) -> Optional[str]:
        instance = self._commit_repo.get_by_hash(repo_id, commit_hash)
        return instance.id if instance else None

    def find_file_id_by_path(self, repo_id: str, file_path: str) -> Optional[str]:
        instance = self._file_repo.list_by_repository(repo_id)
        for f in instance:
            if f.relative_path == file_path or f.name == file_path:
                return f.id
        return None

    def upsert_file_commit(self, mapping_data: Dict[str, Any]):
        self._commit_repo.create(mapping_data)
