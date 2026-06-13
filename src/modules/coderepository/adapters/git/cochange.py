"""
Co-change Analysis Engine — temporal coupling via git co-change detection.

Analyzes git history to find files that frequently change together.
High co-change scores indicate logical coupling even when there's no
direct code dependency. Critical for impact analysis and refactoring.

:project: CodeCortex
:package: Modules.Coderepository.Adapters.Git.Cochange
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""

from __future__ import annotations

import logging
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("CodeCortex.Coderepository.Git.Cochange")

# Default exclusion patterns for co-change analysis
EXCLUDED_EXTENSIONS = frozenset({
    ".lock", ".log", ".tmp", ".bak", ".swp", ".orig",
    ".png", ".jpg", ".gif", ".ico", ".svg", ".woff", ".eot",
    ".ttf", ".pdf", ".zip", ".tar", ".gz", ".bz2",
})

EXCLUDED_PATHS = frozenset({
    "node_modules", ".git", ".svn", "__pycache__", "venv",
    ".venv", "dist", "build", "target", ".next", ".nuxt",
    "vendor", ".tox", ".eggs", "egg-info", ".mypy_cache",
    ".pytest_cache", ".coverage", ".idea", ".vscode",
})


class CoChangeResult:
    """Result of a co-change analysis for a single file pair."""

    __slots__ = ("file_a", "file_b", "co_change_count", "total_commits",
                 "score", "risk")

    def __init__(
        self,
        file_a: str,
        file_b: str,
        co_change_count: int,
        total_commits: int,
    ):
        self.file_a = file_a
        self.file_b = file_b
        self.co_change_count = co_change_count
        self.total_commits = total_commits
        self.score = co_change_count / max(total_commits, 1)
        self.risk = self._classify_risk()

    def _classify_risk(self) -> str:
        if self.score >= 0.6:
            return "high"
        elif self.score >= 0.3:
            return "medium"
        return "low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_a": self.file_a,
            "file_b": self.file_b,
            "co_change_count": self.co_change_count,
            "total_commits": self.total_commits,
            "score": round(self.score, 3),
            "risk": self.risk,
        }


class CoChangeMatrix:
    """Co-change frequency matrix built from git history.

    Usage:
        matrix = CoChangeMatrix.build("/path/to/repo")
        results = matrix.get_top_pairs(20)
        score = matrix.get_score("src/a.py", "src/b.py")
    """

    def __init__(self, repo_path: str):
        self.repo_path = str(Path(repo_path).resolve())
        self._matrix: Dict[Tuple[str, str], int] = defaultdict(int)
        self._file_commit_count: Dict[str, int] = defaultdict(int)
        self._total_commits: int = 0
        self._built: bool = False

    @classmethod
    def build(
        cls,
        repo_path: str,
        since: Optional[str] = None,
        max_commits: int = 5000,
        exclude_extensions: Optional[Set[str]] = None,
        exclude_paths: Optional[Set[str]] = None,
        timeout: int = 60,
    ) -> "CoChangeMatrix":
        """Build co-change matrix from git history.

        Args:
            repo_path: Path to git repository.
            since: Git time range (e.g. "1 year", "6 months", "90 days").
            max_commits: Maximum commits to process.
            exclude_extensions: File extensions to skip.
            exclude_paths: Directory names to skip.
            timeout: Git command timeout in seconds.
        """
        instance = cls(repo_path)
        exts = exclude_extensions or EXCLUDED_EXTENSIONS
        paths = exclude_paths or EXCLUDED_PATHS

        since_arg = f"--since={since}" if since else "--since=1 year"
        cmd = [
            "git", "log", "--name-only", since_arg,
            "--pretty=format:COMMIT:%H",
            f"--max-count={max_commits}",
        ]

        try:
            start = time.time()
            result = subprocess.run(
                cmd, cwd=instance.repo_path, capture_output=True,
                text=True, timeout=timeout, shell=False,
            )
            elapsed = time.time() - start
            logger.debug(f"git log completed in {elapsed:.2f}s ({len(result.stdout)} chars)")
        except subprocess.TimeoutExpired:
            logger.warning(f"git log timed out after {timeout}s for {repo_path}")
            return instance
        except FileNotFoundError:
            logger.warning(f"git not found or not a git repo: {repo_path}")
            return instance
        except Exception as e:
            logger.error(f"git log failed: {e}")
            return instance

        current_commit_files: List[str] = []
        commit_count = 0

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("COMMIT:"):
                # Process previous commit's files
                if current_commit_files and len(current_commit_files) > 1:
                    instance._process_commit_files(current_commit_files, exts, paths)
                    commit_count += 1
                current_commit_files = []
            elif line and not line.startswith("COMMIT:"):
                current_commit_files.append(line)

        # Process last commit
        if current_commit_files and len(current_commit_files) > 1:
            instance._process_commit_files(current_commit_files, exts, paths)
            commit_count += 1

        instance._total_commits = commit_count
        instance._built = True
        logger.info(f"Co-change matrix built: {commit_count} commits, "
                     f"{len(instance._matrix)} file pairs")
        return instance

    def _process_commit_files(
        self,
        files: List[str],
        exclude_extensions: Set[str],
        exclude_paths: Set[str],
    ) -> None:
        """Record co-change for all file pairs in a single commit."""
        # Filter files
        filtered = []
        for f in files:
            fpath = Path(f)
            ext = fpath.suffix.lower()
            parts = fpath.parts
            if ext in exclude_extensions:
                continue
            if any(p in exclude_paths for p in parts):
                continue
            filtered.append(f)

        # Record co-change pairs
        for i in range(len(filtered)):
            self._file_commit_count[filtered[i]] += 1
            for j in range(i + 1, len(filtered)):
                pair = (filtered[i], filtered[j])
                self._matrix[pair] += 1

    def get_score(self, file_a: str, file_b: str) -> float:
        """Get normalized co-change score between two files (0.0 - 1.0)."""
        pair = (file_a, file_b)
        reverse = (file_b, file_a)
        count = max(self._matrix.get(pair, 0), self._matrix.get(reverse, 0))
        if count == 0 or self._total_commits == 0:
            return 0.0
        return count / self._total_commits

    def get_top_pairs(
        self,
        limit: int = 20,
        min_score: float = 0.0,
    ) -> List[CoChangeResult]:
        """Get file pairs with highest co-change scores."""
        results = []
        for (a, b), count in self._matrix.items():
            score = count / max(self._total_commits, 1)
            if score >= min_score:
                results.append(CoChangeResult(a, b, count, self._total_commits))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def get_hotspots(
        self,
        limit: int = 10,
        min_pairs: int = 3,
        min_score: float = 0.2,
    ) -> List[Dict[str, Any]]:
        """Find files with the most high-scoring co-change partners.

        These are 'temporal hubs' — files that couple strongly with many others.
        """
        file_scores: Dict[str, List[CoChangeResult]] = defaultdict(list)
        for (a, b), count in self._matrix.items():
            score = count / max(self._total_commits, 1)
            if score >= min_score:
                file_scores[a].append(CoChangeResult(a, b, count, self._total_commits))
                file_scores[b].append(CoChangeResult(b, a, count, self._total_commits))

        hotspots = []
        for file_path, pairs in file_scores.items():
            if len(pairs) >= min_pairs:
                avg_score = sum(p.score for p in pairs) / len(pairs)
                hotspots.append({
                    "file": file_path,
                    "co_change_partners": len(pairs),
                    "avg_score": round(avg_score, 3),
                    "max_score": round(max(p.score for p in pairs), 3),
                    "risk": "high" if avg_score >= 0.4 else "medium" if avg_score >= 0.2 else "low",
                    "top_partners": [
                        {"file": p.file_b, "score": round(p.score, 3)}
                        for p in sorted(pairs, key=lambda x: x.score, reverse=True)[:5]
                    ],
                })

        hotspots.sort(key=lambda h: h["co_change_partners"], reverse=True)
        return hotspots[:limit]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the co-change matrix."""
        if not self._built:
            return {"built": False, "message": "Matrix not built. Call .build() first."}

        total_pairs = len(self._matrix)
        high_risk = sum(1 for p in self._matrix.values() if p / max(self._total_commits, 1) >= 0.6)
        med_risk = sum(1 for p in self._matrix.values() if 0.3 <= p / max(self._total_commits, 1) < 0.6)
        unique_files = len(self._file_commit_count)

        return {
            "built": True,
            "total_commits_analyzed": self._total_commits,
            "unique_files": unique_files,
            "total_pairs": total_pairs,
            "high_risk_pairs": high_risk,
            "medium_risk_pairs": med_risk,
            "hotspots": self.get_hotspots(limit=10),
        }
