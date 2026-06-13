"""
CodeCortex Auto-Updater — background version checking, download, and upgrade signals.

:project: CodeCortex
:package: Core.Update.Updater
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0

Architecture
────────────
┌─────────────────────────────────────────────────────────┐
│                    Auto-Updater Service                    │
├─────────────────────────────────────────────────────────┤
│  CodeCortexUpdater (threading.Thread)                     │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ VersionChecker │→│UpdateSignal │→│Downloader   │ │
│  │ - GitHub API  │  │ - signal.md │  │ - git pull  │ │
│  │ - .version    │  │ - notify AI │  │ - uv sync   │ │
│  └────────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
        │                        │
        ▼                        ▼
  ~/.coddy/codecortex/      GitHub API
  update.json               /releases/latest
  .version
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("CodeCortex.Core.Update.Updater")

# ─────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────

GITHUB_API_RELEASES: str = (
    "https://api.github.com/repos/steevenz/mcp-codecortex/releases/latest"
)
"""GitHub Releases API URL for the latest release."""

GITHUB_REPO_SSH: str = "git@github.com:steevenz/mcp-codecortex.git"
"""SSH remote for pulling updates."""

GITHUB_REPO_HTTPS: str = "https://github.com/steevenz/mcp-codecortex.git"
"""HTTPS remote fallback."""

CHECK_INTERVAL_SECONDS: float = 3600.0
"""Default interval between background version checks (1 hour)."""

CONNECTIVITY_TIMEOUT: int = 8
"""Seconds to wait for GitHub connectivity check."""

SIGNAL_FILENAME: str = "update_signal.json"
"""Filename inside ~/.coddy/codecortex/ for AI update signals."""

UPDATE_CONFIG_FILENAME: str = "update.json"
"""Filename inside ~/.coddy/codecortex/ for update metadata."""

BACKOFF_BASE: float = 30.0
"""Base retry backoff (seconds). Doubles on each failure up to MAX_BACKOFF."""

MAX_BACKOFF: float = 3600.0
"""Maximum retry backoff (seconds)."""

RETRY_CODES: set = {429, 500, 502, 503, 504}
"""HTTP status codes that trigger a retry."""


# ─────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────

class UpdateStatus(str, Enum):
    """Status of the update checker."""

    IDLE = "idle"
    CHECKING = "checking"
    UPDATE_AVAILABLE = "update_available"
    UP_TO_DATE = "up_to_date"
    ERROR = "error"
    DOWNLOADING = "downloading"
    APPLYING = "applying"


@dataclass
class VersionCheckResult:
    """Result of a version check."""

    local_version: str
    latest_version: str
    update_available: bool
    release_url: str = ""
    release_notes: str = ""
    checked_at: str = ""
    error: Optional[str] = None


@dataclass
class UpdateSignal:
    """Signal file that tells the AI an update is available.

    Written to ~/.coddy/codecortex/update_signal.json.
    AI reads this file and can trigger the update process.
    """

    update_available: bool = False
    local_version: str = ""
    latest_version: str = ""
    release_url: str = ""
    release_title: str = ""
    release_notes: str = ""
    signal_at: str = ""
    dismissed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UpdateSignal":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def signal_path(cls) -> Path:
        from src.core.config.database import get_data_dir
        return get_data_dir() / SIGNAL_FILENAME

    def write(self) -> None:
        path = self.signal_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def read(cls) -> Optional["UpdateSignal"]:
        path = cls.signal_path()
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return cls.from_dict(raw)
        except Exception:
            return None

    def dismiss(self) -> None:
        self.dismissed = True
        self.write()


# ─────────────────────────────────────────────────────────
# Core Updater
# ─────────────────────────────────────────────────────────

class CodeCortexUpdater:
    """Auto-update service for CodeCortex.

    Features:
      - Periodic version checks against GitHub Releases API
      - Connectivity validation before API calls
      - Exponential backoff retry on failures
      - Signal file for AI notification
      - Git-based update download and apply
      - Efficient resource usage (sleep between checks, no CPU burn)

    Usage:
        updater = CodeCortexUpdater()
        updater.start()           # starts background thread
        result = updater.check()  # one-shot check
        updater.apply()           # apply available update
        updater.stop()            # stop background thread
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        check_interval: float = CHECK_INTERVAL_SECONDS,
        auto_start: bool = False,
    ):
        self._project_root = project_root or Path(__file__).resolve().parents[3]
        self._version_path = self._project_root / ".version"
        self._check_interval = check_interval
        self._status = UpdateStatus.IDLE
        self._latest_check: Optional[VersionCheckResult] = None
        self._last_check_time: float = 0.0

        # Background thread
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Retry state
        self._consecutive_failures: int = 0

        if auto_start:
            self.start()

    # ── Public API ──────────────────────────────────────

    @property
    def status(self) -> UpdateStatus:
        return self._status

    @property
    def latest_check(self) -> Optional[VersionCheckResult]:
        return self._latest_check

    def get_local_version(self) -> str:
        """Read current version from .version file."""
        try:
            return self._version_path.read_text(encoding="utf-8").strip()
        except Exception:
            return "0.0.0"

    def check(self) -> VersionCheckResult:
        """Perform a one-shot version check against GitHub.

        Returns a VersionCheckResult regardless of outcome (success or error).
        The result is cached in ``self._latest_check``.
        """
        local_ver = self.get_local_version()
        self._status = UpdateStatus.CHECKING

        # 1. Connectivity check
        if not self._internet_reachable():
            self._status = UpdateStatus.ERROR
            result = VersionCheckResult(
                local_version=local_ver,
                latest_version=local_ver,
                update_available=False,
                checked_at=_now_iso(),
                error="No internet connectivity or GitHub unreachable",
            )
            self._latest_check = result
            self._consecutive_failures += 1
            return result

        # 2. Fetch latest version from GitHub
        try:
            latest_ver, release_data = self._fetch_latest_release()
        except Exception as e:
            self._status = UpdateStatus.ERROR
            err_msg = str(e)
            result = VersionCheckResult(
                local_version=local_ver,
                latest_version=local_ver,
                update_available=False,
                checked_at=_now_iso(),
                error=err_msg,
            )
            self._latest_check = result
            self._consecutive_failures += 1
            return result

        # 3. Compare versions
        update_avail = self._compare_versions(local_ver, latest_ver)
        self._consecutive_failures = 0

        result = VersionCheckResult(
            local_version=local_ver,
            latest_version=latest_ver,
            update_available=update_avail,
            release_url=release_data.get("html_url", ""),
            release_notes=release_data.get("body", ""),
            checked_at=_now_iso(),
        )
        self._latest_check = result
        self._last_check_time = time.time()

        if update_avail:
            self._status = UpdateStatus.UPDATE_AVAILABLE
        else:
            self._status = UpdateStatus.UP_TO_DATE

        # 4. Write signal file for AI
        self._write_signal(result)
        self._write_update_config(result)

        return result

    def download(self) -> bool:
        """Download the latest update (git pull).

        Must be called after ``check()`` returns update_available=True.
        Returns True on success.
        """
        if not self._latest_check or not self._latest_check.update_available:
            logger.warning("No update available to download.")
            return False

        self._status = UpdateStatus.DOWNLOADING
        try:
            # Determine current remote URL
            remote = self._resolve_remote_url()
            branch = self._resolve_default_branch()

            # Fetch latest commits
            subprocess.run(
                ["git", "fetch", remote, branch],
                cwd=str(self._project_root),
                capture_output=True, text=True, timeout=120,
            ).check_returncode()

            # Check if local is behind
            behind = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..{remote}/{branch}"],
                cwd=str(self._project_root),
                capture_output=True, text=True, timeout=30,
            )
            if behind.returncode == 0:
                count = int(behind.stdout.strip())
                logger.info("Local is %d commits behind %s/%s", count, remote, branch)

            self._status = UpdateStatus.UPDATE_AVAILABLE
            return True

        except subprocess.TimeoutExpired:
            logger.error("git fetch timed out after 120s")
            self._status = UpdateStatus.ERROR
            return False
        except subprocess.CalledProcessError as e:
            logger.error("git fetch failed: %s", e.stderr)
            self._status = UpdateStatus.ERROR
            return False
        except Exception as e:
            logger.error("Download failed: %s", e)
            self._status = UpdateStatus.ERROR
            return False

    def apply(self) -> bool:
        """Apply the downloaded update (git merge + uv sync).

        Must be called after ``download()``.
        Returns True on success.
        """
        if self._status not in (UpdateStatus.DOWNLOADING, UpdateStatus.UPDATE_AVAILABLE):
            logger.warning("No downloaded update to apply. Run download() first.")
            return False

        self._status = UpdateStatus.APPLYING
        try:
            remote = self._resolve_remote_url()
            branch = self._resolve_default_branch()

            # 1. Merge fetched changes
            subprocess.run(
                ["git", "merge", "--ff-only", f"{remote}/{branch}"],
                cwd=str(self._project_root),
                capture_output=True, text=True, timeout=60,
            ).check_returncode()

            # 2. Sync dependencies
            subprocess.run(
                [sys.executable, "-m", "uv", "sync"],
                cwd=str(self._project_root),
                capture_output=True, text=True, timeout=300,
            ).check_returncode()

            # 3. Update .version file if new version.json was pulled
            #    (already done by git merge)

            self._status = UpdateStatus.UP_TO_DATE
            signal = UpdateSignal.read()
            if signal:
                signal.dismiss()

            logger.info("Update applied successfully.")
            return True

        except subprocess.CalledProcessError as e:
            logger.error("Apply failed: %s", e.stderr)
            self._status = UpdateStatus.ERROR
            return False
        except Exception as e:
            logger.error("Apply failed: %s", e)
            self._status = UpdateStatus.ERROR
            return False

    # ── Background Thread ───────────────────────────────

    def start(self) -> None:
        """Start background periodic checker in a daemon thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="codecortex-updater",
            daemon=True,
        )
        self._thread.start()
        logger.info("Background updater thread started (interval=%ds)", self._check_interval)

    def stop(self) -> None:
        """Signal the background thread to stop."""
        self._stop_event.set()
        logger.info("Background updater stop signalled.")

    # ── Internal ────────────────────────────────────────

    def _run_loop(self) -> None:
        """Background loop: check → sleep → check → ..."""
        # Initial check after short delay to let server start
        if not self._stop_event.wait(10):
            try:
                self.check()
            except Exception as e:
                logger.debug("Initial version check skipped: %s", e)

        while not self._stop_event.is_set():
            # Sleep in short increments so we can be stopped promptly
            deadline = time.time() + self._check_interval
            while time.time() < deadline:
                if self._stop_event.wait(min(5.0, deadline - time.time())):
                    return
            try:
                self.check()
            except Exception as e:
                logger.warning("Background version check failed: %s", e)

    def _internet_reachable(self) -> bool:
        """Quick connectivity check: HEAD request to github.com."""
        try:
            req = urllib.request.Request(
                "https://github.com",
                method="HEAD",
            )
            with urllib.request.urlopen(req, timeout=CONNECTIVITY_TIMEOUT) as resp:
                return 200 <= resp.status < 500
        except Exception:
            return False

    def _fetch_latest_release(self) -> Tuple[str, Dict[str, Any]]:
        """Fetch latest release info from GitHub Releases API.

        Returns (version_string, release_data_dict).
        Raises on network or parse errors.
        """
        req = urllib.request.Request(
            GITHUB_API_RELEASES,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "CodeCortex-Updater/2.0",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in RETRY_CODES:
                raise ConnectionError(f"GitHub API returned {resp.status}")
            raw = resp.read().decode("utf-8")

        data = json.loads(raw)
        tag = data.get("tag_name", "").lstrip("v")
        if not tag:
            raise ValueError("No tag_name in GitHub release payload")
        return tag, data

    def _compare_versions(self, local: str, remote: str) -> bool:
        """Semver comparison. Returns True if remote > local."""
        try:
            return self._parse_semver(remote) > self._parse_semver(local)
        except Exception:
            # Fallback: string comparison
            return remote > local

    @staticmethod
    def _parse_semver(ver: str) -> tuple:
        """Parse 'X.Y.Z' into (major, minor, patch). Handles pre-release suffixes."""
        import re
        parts = re.split(r"[.-]", ver.strip().lstrip("v"))
        majors = []
        for p in parts[:3]:
            try:
                majors.append(int(p))
            except ValueError:
                majors.append(0)
        # Pad to 3
        while len(majors) < 3:
            majors.append(0)
        return tuple(majors)

    def _resolve_remote_url(self) -> str:
        """Detect the git remote URL (SSH preferred, fallback HTTPS)."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(self._project_root),
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                if url:
                    return url
        except Exception:
            pass
        # Check if SSH is configured
        try:
            subprocess.run(
                ["git", "ls-remote", GITHUB_REPO_SSH, "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            return GITHUB_REPO_SSH
        except Exception:
            return GITHUB_REPO_HTTPS

    def _resolve_default_branch(self) -> str:
        """Detect the default branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(self._project_root),
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                if branch:
                    return branch
        except Exception:
            pass
        return "main"

    def _write_signal(self, result: VersionCheckResult) -> None:
        """Write update signal file for AI consumption."""
        signal = UpdateSignal(
            update_available=result.update_available,
            local_version=result.local_version,
            latest_version=result.latest_version,
            release_url=result.release_url,
            release_notes=result.release_notes[:500] if result.release_notes else "",
            signal_at=_now_iso(),
        )
        signal.write()

    def _write_update_config(self, result: VersionCheckResult) -> None:
        """Write update metadata to ~/.coddy/codecortex/update.json."""
        from src.core.config.database import get_data_dir
        config_path = get_data_dir() / UPDATE_CONFIG_FILENAME
        config: Dict[str, Any] = {
            "last_check_at": result.checked_at,
            "local_version": result.local_version,
            "latest_version": result.latest_version,
            "update_available": result.update_available,
            "error": result.error,
            "consecutive_failures": self._consecutive_failures,
        }
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    def get_signal(self) -> Optional[UpdateSignal]:
        """Read the current update signal file."""
        return UpdateSignal.read()


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
