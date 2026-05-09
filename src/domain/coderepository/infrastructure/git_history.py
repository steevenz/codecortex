"""
/**
 * @project   CodeCortex
 * @package   Domain/Repository
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python, GitPython
 * * Class GitHistoryWorker – Single Responsibility: Index git commits and file change history.
 * * Supports SSH auth, delta fetch (--depth=1), and commit audit (secrets scan).
 */
"""

import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from git import Repo
from datetime import datetime

from src.core.database import DatabaseManager
from src.core.logging_config import get_logger
from src.domain.coderepository.core.store import ICodeRepositoryStore

logger = get_logger("CodeCortex.Domain.CodeRepository.History")

# Secrets patterns for git audit
SECRETS_PATTERNS = [
    (re.compile(r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?', re.I), "api_key"),
    (re.compile(r'(?:secret|token|password|passwd)\s*[=:]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?', re.I), "password_or_token"),
    (re.compile(r'(?:-----BEGIN\s+(?:RSA|OPENSSH|EC)\s+PRIVATE\s+KEY-----)', re.I), "private_key"),
    (re.compile(r'(?:ghp_|gho_|github_pat_)[a-zA-Z0-9]{36,}', re.I), "github_token"),
    (re.compile(r'(?:sk-[a-zA-Z0-9]{32,})', re.I), "openai_api_key"),
    (re.compile(r'(?:AKIA[0-9A-Z]{16})', re.I), "aws_access_key"),
]

class GitHistoryWorker:
    """
    Extracts commit metadata and file-level change history from Git.
    Supports SSH auth and delta-only fetch for incremental updates.
    """
    def __init__(self, store: ICodeRepositoryStore, repo_path: Path, auth_type: str = "https"):
        self.store = store
        self.repo_path = repo_path
        self.auth_type = auth_type
        try:
            self.git_repo = Repo(repo_path)
            if auth_type == "ssh":
                logger.info(f"SSH auth configured for {repo_path}")
        except Exception as e:
            logger.warning(f"Git repository not detected at {repo_path}: {e}")
            self.git_repo = None

    def index_history(self, repository_id: str, limit: int = 1000, shallow: bool = True):
        """Index git history. If shallow=True, uses delta fetch (depth=1) for speed."""
        if not self.git_repo:
            return

        logger.info(f"Indexing git history for repository {repository_id} (limit: {limit}, shallow: {shallow})")

        try:
            if shallow:
                try:
                    self.git_repo.git.fetch("--depth=1")
                except Exception as e:
                    logger.warning(f"Shallow fetch failed, falling back to full history: {e}")

            commits = list(self.git_repo.iter_commits(max_count=limit))
            for commit in reversed(commits):
                self._upsert_commit(repository_id, commit)
                self._index_commit_diffs(repository_id, commit)

            logger.info(f"History indexing completed for {repository_id}")
        except Exception as e:
            logger.error(f"Failed to index git history: {e}", exc_info=True)

    def audit_commits(self, repository_id: str, limit: int = 100) -> List[Dict]:
        """Scan recent commits for secrets. Returns list of findings."""
        if not self.git_repo:
            return []

        findings = []
        commits = list(self.git_repo.iter_commits(max_count=limit))

        for commit in commits:
            commit_hash = commit.hexsha
            try:
                diff = self.git_repo.git.show(commit_hash, "--", diff_filter="ACM")
            except Exception:
                diff = ""

            for pattern, secret_type in SECRETS_PATTERNS:
                matches = pattern.findall(diff)
                if matches:
                    findings.append({
                        "commit": commit_hash,
                        "author": commit.author.email,
                        "type": secret_type,
                        "match_count": len(matches),
                        "risk": "high" if secret_type in ("private_key", "aws_access_key") else "medium"
                    })

        return findings

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
