"""
Protocol ICodeRepositoryStore - Interface for repository persistence.

:project: CodeCortex
:package: Modules.Coderepository.Core.Store
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from typing import Protocol, List, Dict, Optional, Any, ContextManager
from uuid import UUID

class ICodeRepositoryStore(Protocol):
    def transaction(self) -> ContextManager[Any]:
        ...

    def get_repository(self, repo_id: str) -> Optional[Dict[str, Any]]:
        ...

    def get_repository_by_path(self, root_path: str) -> Optional[Dict[str, Any]]:
        ...

    def list_repositories(self) -> List[Dict[str, Any]]:
        ...

    def upsert_repository(self, name: str, root_path: str, repo_id: Optional[str] = None, vcs_metadata: Optional[Dict[str, Any]] = None) -> str:
        ...

    def update_indexing_time(self, repo_id: str):
        ...

    def get_directory_id(self, repo_id: str, relative_path: str) -> Optional[str]:
        ...

    def ensure_directory_chain(self, repo_id: str, relative_path: str) -> str:
        ...

    def list_files(self, repo_id: str, directory_id: Optional[str] = None) -> List[Dict[str, Any]]:
        ...

    def get_manifest_entry(self, repo_id: str, file_path: str) -> Optional[Dict[str, Any]]:
        ...

    def upsert_file_and_manifest(self, file_data: Dict[str, Any], manifest_data: Dict[str, Any]):
        ...

    def upsert_commit(self, commit_data: Dict[str, Any]):
        ...

    def get_commit_id(self, repo_id: str, commit_hash: str) -> Optional[str]:
        ...

    def find_file_id_by_path(self, repo_id: str, file_path: str) -> Optional[str]:
        ...

    def upsert_file_commit(self, mapping_data: Dict[str, Any]):
        ...
