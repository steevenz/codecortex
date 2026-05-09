"""
/**
 * @project   CodeCortex
 * @package   CodeRepository/Registry
 * @standard  Aegis-CrossStack-v1.0
 * * Global registry for indexed repositories.
 *   Stores repo metadata in ~/.codecortex/registry.json for cross-session discovery.
 */
"""

import json
import os
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger("CodeCortex.CodeRepository.Registry")

REGISTRY_DIR_NAME = ".codecortex"
REGISTRY_FILE_NAME = "registry.json"


def _get_registry_dir() -> Path:
    """Get the global registry directory (~/.codecortex)."""
    return Path(os.path.expanduser("~")) / REGISTRY_DIR_NAME


def _get_registry_path() -> Path:
    """Get the global registry file path."""
    return _get_registry_dir() / REGISTRY_FILE_NAME


class RegistryManager:
    """Manages cross-session repository registry."""

    @staticmethod
    def ensure_dir():
        _get_registry_dir().mkdir(parents=True, exist_ok=True)

    @staticmethod
    def read() -> List[Dict[str, Any]]:
        try:
            path = _get_registry_path()
            if path.exists():
                with open(path, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            return []
        except Exception as e:
            logger.warning(f"Failed to read registry: {e}")
            return []

    @staticmethod
    def write(entries: List[Dict[str, Any]]):
        RegistryManager.ensure_dir()
        path = _get_registry_path()
        with open(path, "w") as f:
            json.dump(entries, f, indent=2)

    @staticmethod
    def register(repo_path: str, repo_id: str, stats: Optional[Dict] = None):
        resolved = str(Path(repo_path).resolve())
        entries = RegistryManager.read()
        existing_idx = None
        for i, e in enumerate(entries):
            if Path(e.get("path", "")).resolve() == Path(resolved):
                existing_idx = i
                break

        entry = {
            "path": resolved,
            "repo_id": repo_id,
            "last_commit": RegistryManager._get_current_commit(resolved),
            "indexed_at": None,
            "stats": stats or {},
        }

        if existing_idx is not None:
            old = entries[existing_idx]
            entry["indexed_at"] = old.get("indexed_at")
            entries[existing_idx] = entry
        else:
            entries.append(entry)

        RegistryManager.write(entries)
        return entry

    @staticmethod
    def unregister(repo_path: str):
        resolved = str(Path(repo_path).resolve())
        entries = RegistryManager.read()
        entries = [e for e in entries if str(Path(e.get("path", "")).resolve()) != resolved]
        RegistryManager.write(entries)

    @staticmethod
    def list_all() -> List[Dict[str, Any]]:
        return RegistryManager.read()

    @staticmethod
    def check_staleness(repo_path: str, last_commit: Optional[str] = None) -> Dict:
        """Check how many commits the index is behind HEAD."""
        if not last_commit:
            entry = RegistryManager.find_by_path(repo_path)
            if entry:
                last_commit = entry.get("last_commit")
        if not last_commit:
            return {"is_stale": False, "commits_behind": 0, "hint": "No commit data"}

        try:
            result = subprocess.run(
                ["git", "rev-list", "--count", f"{last_commit}..HEAD"],
                cwd=repo_path,
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                behind = int(result.stdout.strip() or "0")
                if behind > 0:
                    return {
                        "is_stale": True,
                        "commits_behind": behind,
                        "hint": f"Index is {behind} commit(s) behind HEAD"
                    }
                return {"is_stale": False, "commits_behind": 0}
        except Exception as e:
            logger.warning(f"Staleness check failed: {e}")
        return {"is_stale": False, "commits_behind": 0}

    @staticmethod
    def find_by_path(repo_path: str) -> Optional[Dict]:
        resolved = str(Path(repo_path).resolve())
        for e in RegistryManager.read():
            if str(Path(e.get("path", "")).resolve()) == resolved:
                return e
        return None

    @staticmethod
    def find_by_id(repo_id: str) -> Optional[Dict]:
        for e in RegistryManager.read():
            if e.get("repo_id") == repo_id:
                return e
        return None

    @staticmethod
    def _get_current_commit(repo_path: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
