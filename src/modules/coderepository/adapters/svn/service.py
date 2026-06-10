"""
Class Svn — Application service for SVN-native workflows.
Mirrors Git interface for consistent lifecycle management.

:project: CodeCortex
:package: Modules.Coderepository.Adapters.Svn.Service
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from src.modules.coderepository.adapters.svn.adapter import Svn
from src.core.logging import get_logger

logger = get_logger("CodeCortex.Domain.CodeRepository.App.Svn")

class Svn:
    def __init__(self):
        self._adapters: Dict[str, Svn] = {}

    def _get_adapter(self, repo_path: Union[str, Path]) -> Svn:
        path_str = str(Path(repo_path).resolve())
        if path_str not in self._adapters:
            self._adapters[path_str] = Svn(Path(path_str))
        return self._adapters[path_str]

    def get_info(self, repo_path: Union[str, Path]) -> Dict[str, Any]:
        return self._get_adapter(repo_path).get_info()

    def get_status(self, repo_path: Union[str, Path]) -> Dict[str, Any]:
        return self._get_adapter(repo_path).get_status()

    def get_log(self, repo_path: Union[str, Path], limit: int = 100) -> List[Dict[str, Any]]:
        return self._get_adapter(repo_path).get_log(limit=limit)

    def get_current_revision(self, repo_path: Union[str, Path]) -> Optional[int]:
        return self._get_adapter(repo_path).get_current_revision()

    def get_changed_files_since(self, repo_path: Union[str, Path], revision: int) -> List[str]:
        return self._get_adapter(repo_path).get_changed_files_since(revision)

    def check_staleness(self, repo_path: Union[str, Path], last_revision: Optional[int] = None) -> Dict[str, Any]:
        current = self.get_current_revision(repo_path)
        if current is None:
            return {"is_stale": False, "commits_behind": 0, "hint": "Not an SVN working copy"}
        if last_revision is None:
            return {"is_stale": False, "commits_behind": 0, "hint": "No prior revision data"}
        behind = current - last_revision
        if behind > 0:
            return {
                "is_stale": True,
                "commits_behind": behind,
                "hint": f"Index is {behind} revision(s) behind HEAD (r{current})",
            }
        return {"is_stale": False, "commits_behind": 0}

    def audit_history(self, repo_path: Union[str, Path], limit: int = 100) -> List[Dict[str, Any]]:
        """Scan SVN log for hardcoded secrets in commit messages and diffs."""
        log_entries = self.get_log(repo_path, limit=limit)
        findings: List[Dict[str, Any]] = []

        import re
        secret_patterns = [
            (re.compile(r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?', re.I), "api_key"),
            (re.compile(r'(?:secret|token|password|passwd)\s*[=:]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?', re.I), "password_or_token"),
            (re.compile(r'(?:ghp_|gho_|github_pat_)[a-zA-Z0-9]{36,}', re.I), "github_token"),
            (re.compile(r'(?:AKIA[0-9A-Z]{16})', re.I), "aws_access_key"),
        ]

        for entry in log_entries:
            msg = entry.get("message", "")
            for pattern, ptype in secret_patterns:
                for m in pattern.finditer(msg):
                    findings.append({
                        "revision": entry.get("revision"),
                        "author": entry.get("author"),
                        "type": ptype,
                        "message_snippet": msg[:100],
                        "risk": "high",
                    })
                    break

        return findings
