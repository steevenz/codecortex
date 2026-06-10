"""
Class Svn – Subprocess-based wrapper for SVN CLI.
Mirrors Git interface for consistent repo lifecycle management.

:project: CodeCortex
:package: Modules.Coderepository.Adapters.Svn.Adapter
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any
from src.core.logging import get_logger

logger = get_logger("CodeCortex.Domain.CodeRepository.Infra.Svn")

class Svn:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self._available: Optional[bool] = None
        self._root: Optional[Path] = None

    @property
    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            result = subprocess.run(
                ["svn", "info"],
                cwd=str(self.repo_path),
                capture_output=True, text=True, timeout=10,
            )
            self._available = result.returncode == 0
            if self._available:
                self._root = self.repo_path
            return self._available
        except Exception:
            self._available = False
            return False

    def get_info(self) -> Dict[str, Any]:
        if not self.is_available:
            return {}
        result: Dict[str, Any] = {}
        try:
            proc = subprocess.run(
                ["svn", "info"],
                cwd=str(self.repo_path),
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        ks = k.strip().lower().replace(" ", "_")
                        vs = v.strip()
                        if ks == "revision":
                            result["revision"] = int(vs)
                        elif ks == "url":
                            result["url"] = vs
                        elif ks == "last_changed_rev":
                            result["last_changed_rev"] = int(vs)
                        elif ks == "last_changed_author":
                            result["last_changed_author"] = vs
                        elif ks == "repository_root":
                            result["repository_root"] = vs
        except Exception as e:
            logger.error(f"SVN info failed: {e}")
        return result

    def get_status(self) -> Dict[str, Any]:
        if not self.is_available:
            return {}
        result: Dict[str, List[str]] = {"modified": [], "unversioned": [], "added": [], "deleted": []}
        try:
            proc = subprocess.run(
                ["svn", "status", "--non-interactive"],
                cwd=str(self.repo_path),
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    line = line.strip()
                    if not line or len(line) < 8:
                        continue
                    sc = line[0]
                    fp = line[7:].strip()
                    if sc == "M":
                        result["modified"].append(fp)
                    elif sc == "A":
                        result["added"].append(fp)
                    elif sc == "D":
                        result["deleted"].append(fp)
                    elif sc == "?":
                        result["unversioned"].append(fp)
        except Exception as e:
            logger.error(f"SVN status failed: {e}")
        return result

    def get_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.is_available:
            return []
        entries: List[Dict[str, Any]] = []
        try:
            proc = subprocess.run(
                ["svn", "log", "-l", str(limit), "--xml"],
                cwd=str(self.repo_path),
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode == 0:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(proc.stdout)
                for log_entry in root.findall(".//logentry"):
                    rev = log_entry.get("revision")
                    author = log_entry.findtext("author", "")
                    date = log_entry.findtext("date", "")
                    msg = log_entry.findtext("msg", "")
                    entries.append({
                        "revision": int(rev) if rev else 0,
                        "author": author,
                        "date": date,
                        "message": msg.strip(),
                    })
        except Exception as e:
            logger.error(f"SVN log failed: {e}")
        return entries

    def get_diff(self, revision_from: Optional[int] = None,
                 revision_to: Optional[int] = None) -> str:
        if not self.is_available:
            return ""
        try:
            cmd = ["svn", "diff"]
            if revision_from is not None and revision_to is not None:
                cmd.extend(["-r", f"{revision_from}:{revision_to}"])
            elif revision_from is not None:
                cmd.extend(["-r", str(revision_from)])
            proc = subprocess.run(
                cmd, cwd=str(self.repo_path),
                capture_output=True, text=True, timeout=30,
            )
            return proc.stdout if proc.returncode == 0 else ""
        except Exception as e:
            logger.error(f"SVN diff failed: {e}")
            return ""

    def get_current_revision(self) -> Optional[int]:
        info = self.get_info()
        return info.get("revision")

    def get_changed_files_since(self, revision: int) -> List[str]:
        if not self.is_available:
            return []
        try:
            proc = subprocess.run(
                ["svn", "diff", "--summarize", "-r", f"{revision}:HEAD"],
                cwd=str(self.repo_path),
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode == 0:
                files = []
                for line in proc.stdout.splitlines():
                    line = line.strip()
                    if len(line) >= 2:
                        fp = line[1:].strip()
                        if fp:
                            files.append(fp)
                return files
        except Exception as e:
            logger.error(f"SVN diff --summarize failed: {e}")
        return []
