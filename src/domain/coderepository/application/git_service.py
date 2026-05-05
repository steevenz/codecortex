"""
/**
 * @project   CodeCortex
 * @package   Domain/Repository/Application
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Class GitService - Application service for Git-native workflows and atomic commits.
 */
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from src.domain.coderepository.infrastructure.git_adapter import GitAdapter
from src.core.logging_config import get_logger
from src.domain.coderepository.core.store import ICodeRepositoryStore

logger = get_logger("CodeCortex.Domain.CodeRepository.App.Git")

def normalize_git_path(path: Union[str, Path]) -> str:
    """Normalize path for Git consumption (handles Windows drive letters and separators)."""
    p = Path(path).resolve()
    # Ensure drive letter is uppercase for consistency if on Windows
    if os.name == 'nt' and p.drive:
        return f"{p.drive.upper()}{str(p)[len(p.drive):]}".replace("\\", "/")
    return str(p).replace("\\", "/")

class GitService:
    def __init__(self, store: ICodeRepositoryStore):
        self.store = store
        self._adapters: Dict[str, GitAdapter] = {}

    def _get_adapter(self, repo_path: Union[str, Path]) -> GitAdapter:
        path_str = normalize_git_path(repo_path)
        if path_str not in self._adapters:
            self._adapters[path_str] = GitAdapter(Path(path_str))
            self._auto_configure_if_needed(self._adapters[path_str])
        return self._adapters[path_str]

    def _auto_configure_if_needed(self, adapter: GitAdapter):
        """Automatically set git user name and email from author metadata if missing."""
        if not adapter.is_available:
            return

        name = adapter.get_config("user", "name")
        email = adapter.get_config("user", "email")

        if not name or not email:
            logger.info(f"Git user identity missing for {adapter.repo_path}. Configuring from CodeCortex author metadata...")
            if not name:
                adapter.set_config("user", "name", "Steeven Andrian")
            if not email:
                adapter.set_config("user", "email", "steeven@codecortex.local")
            logger.info("Git local user identity successfully configured.")

    async def stage_and_commit(self, repo_path: Union[str, Path], paths: List[str], message: str) -> Dict[str, Any]:
        """Stage specific paths and commit them atomically."""
        adapter = self._get_adapter(repo_path)
        if not adapter.is_available:
            return {"error": "git_repository_not_found"}

        try:
            rel_paths = []
            repo_root_abs = adapter.repo_path.resolve()
            for p in paths:
                try:
                    abs_p = Path(p).resolve()
                    rel = str(abs_p.relative_to(repo_root_abs)).replace("\\", "/")
                    rel_paths.append(rel)
                except ValueError:
                    # If not under root, maybe it's already relative or invalid
                    # We'll just pass it through and let Git handle it
                    rel_paths.append(str(p).replace("\\", "/"))
            
            await asyncio.to_thread(adapter.add, rel_paths)
            commit_hash = await asyncio.to_thread(adapter.commit, message)
            if commit_hash:
                return {
                    "status": "success",
                    "commit_hash": commit_hash,
                    "message": message,
                    "files": paths
                }
            return {"error": "commit_failed"}
        except Exception as e:
            logger.error(f"Failed to perform stage_and_commit: {e}")
            return {"error": str(e)}

    async def get_repo_status(self, repo_path: Union[str, Path]) -> Dict[str, Any]:
        """Get the current working tree status."""
        adapter = self._get_adapter(repo_path)
        if not adapter.is_available:
            return {"error": "git_repository_not_found"}
        return await asyncio.to_thread(adapter.get_status)

    async def get_file_diff(self, repo_path: Union[str, Path], file_path: str, staged: bool = False) -> str:
        """Get the diff for a specific file."""
        adapter = self._get_adapter(repo_path)
        if not adapter.is_available:
            return ""
        return await asyncio.to_thread(adapter.get_diff, file_path, staged=staged)

    async def revert_change(self, repo_path: Union[str, Path], commit_hash: str) -> Dict[str, Any]:
        """Revert a specific commit."""
        adapter = self._get_adapter(repo_path)
        if not adapter.is_available:
            return {"error": "git_repository_not_found"}
        try:
            await asyncio.to_thread(adapter.revert, commit_hash)
            return {"status": "success", "reverted_commit": commit_hash}
        except Exception as e:
            return {"error": str(e)}

    async def ensure_git_repo(self, repo_path: Union[str, Path]) -> Dict[str, Any]:
        """Initialize git repo if not exists."""
        adapter = self._get_adapter(repo_path)
        if adapter.is_available:
            return {"status": "already_exists"}
        try:
            await asyncio.to_thread(adapter.init_repo)
            self._auto_configure_if_needed(adapter)
            return {"status": "initialized"}
        except Exception as e:
            return {"error": str(e)}
