"""
/**
 * @project   CodeCortex
 * @package   Domain/Repository
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python, GitPython
 * * Class GitHistoryWorker – Single Responsibility: Index git commits and file change history.
 */
"""

import uuid
from pathlib import Path
from typing import Dict, List, Optional
from git import Repo
from datetime import datetime

from src.core.database import DatabaseManager
from src.core.logging_config import get_logger

logger = get_logger("CodeCortex.Domain.CodeRepository.History")

class GitHistoryWorker:
    """
    Extracts commit metadata and file-level change history from Git.
    """
    def __init__(self, store: ICodeRepositoryStore, repo_path: Path):
        self.store = store
        self.repo_path = repo_path
        try:
            self.git_repo = Repo(repo_path)
        except Exception as e:
            logger.warning(f"Git repository not detected at {repo_path}: {e}")
            self.git_repo = None

    def index_history(self, repository_id: str, limit: int = 1000):
        if not self.git_repo:
            return

        logger.info(f"Indexing git history for repository {repository_id} (limit: {limit})")
        
        try:
            commits = list(self.git_repo.iter_commits(max_count=limit))
            for commit in reversed(commits):
                self._upsert_commit(repository_id, commit)
                self._index_commit_diffs(repository_id, commit)
            
            logger.info(f"History indexing completed for {repository_id}")
        except Exception as e:
            logger.error(f"Failed to index git history: {e}", exc_info=True)

    def _upsert_commit(self, repository_id: str, commit):
        parent_hashes = ",".join([p.hexsha for p in commit.parents])
        self.store.upsert_commit({
            "id": str(uuid.uuid4()),
            "repository_id": repository_id,
            "commit_hash": commit.hexsha,
            "author_name": commit.author.name,
            "author_email": commit.author.email,
            "committed_at": datetime.fromtimestamp(commit.committed_date),
            "message": commit.message.strip(),
            "parent_hashes": parent_hashes
        })

    def _index_commit_diffs(self, repository_id: str, commit):
        commit_id = self.store.get_commit_id(repository_id, commit.hexsha)
        if not commit_id:
            return

        if commit.parents:
            diffs = commit.parents[0].diff(commit)
        else:
            diffs = commit.diff(None, create_patch=False, paths=None)

        for diff in diffs:
            change_type = diff.change_type
            file_path = diff.b_path if diff.b_path else diff.a_path
            
            file_id = self.store.find_file_id_by_path(repository_id, file_path)
            if file_id:
                self.store.upsert_file_commit({
                    "id": str(uuid.uuid4()),
                    "repository_id": repository_id,
                    "file_id": file_id,
                    "commit_id": commit_id,
                    "change_type": change_type
                })
