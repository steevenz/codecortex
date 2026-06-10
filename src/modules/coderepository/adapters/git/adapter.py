"""
Class Git – Wrapper for GitPython to interact with local repositories.

:project: CodeCortex
:package: Modules.Coderepository.Adapters.Git.Adapter
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from git import Repo, exc
from src.core.logging import get_logger

logger = get_logger("CodeCortex.Domain.CodeRepository.Infra.Git")

class Git:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self._repo: Optional[Repo] = None
        try:
            self._repo = Repo(repo_path)
        except exc.InvalidGitRepositoryError:
            logger.warning(f"No git repository found at {repo_path}")
        except Exception as e:
            logger.error(f"Error initializing Git: {e}")

    @property
    def is_available(self) -> bool:
        return self._repo is not None

    def get_config(self, section: str, option: str) -> Optional[str]:
        if not self._repo: return None
        try:
            return self._repo.config_reader().get_value(section, option)
        except:
            return None

    def set_config(self, section: str, option: str, value: str, level: str = "local"):
        if not self._repo: return
        try:
            with self._repo.config_writer(config_level=level) as cw:
                cw.set_value(section, option, value)
        except Exception as e:
            logger.error(f"Failed to set git config {section}.{option}: {e}")

    def add(self, paths: List[str]):
        if not self._repo: return
        self._repo.index.add(paths)

    def commit(self, message: str, author_name: Optional[str] = None, author_email: Optional[str] = None) -> Optional[str]:
        if not self._repo: return None
        try:
            # GitPython uses the environment or config by default.
            # We can override if needed, but usually we set it in config first.
            commit_obj = self._repo.index.commit(message)
            return commit_obj.hexsha
        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        if not self._repo: return {}
        return {
            "modified": [item.a_path for item in self._repo.index.diff(None)],
            "staged": [item.a_path for item in self._repo.index.diff("HEAD")],
            "untracked": self._repo.untracked_files,
            "branch": self._repo.active_branch.name if not self._repo.head.is_detached else "DETACHED"
        }

    def revert(self, commit_hash: str):
        if not self._repo: return
        try:
            self._repo.git.revert(commit_hash, no_edit=True)
        except Exception as e:
            logger.error(f"Git revert failed for {commit_hash}: {e}")
            raise

    def get_diff(self, path: Optional[str] = None, staged: bool = False) -> str:
        if not self._repo: return ""
        try:
            if staged:
                return self._repo.git.diff("--cached", path)
            return self._repo.git.diff(path)
        except Exception as e:
            logger.error(f"Git diff failed: {e}")
            return ""

    def init_repo(self):
        """Initialize a new git repository if it doesn't exist."""
        if self._repo: return
        try:
            self._repo = Repo.init(self.repo_path)
            logger.info(f"Initialized new git repository at {self.repo_path}")
        except Exception as e:
            logger.error(f"Failed to initialize git repository: {e}")
            raise
