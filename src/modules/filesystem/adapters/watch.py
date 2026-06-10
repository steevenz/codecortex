"""
Watch.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Watch
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
import os
import subprocess
import time
from datetime import datetime, timezone

from src.core import ApiError

from src.core.utils.path import norm_path as _norm


def _parse_since(since: Optional[str]):
    if since is None:
        return "none", None
    if since.startswith("git:"):
        return "git", since[4:]
    if since.startswith("svn:"):
        rev_str = since[4:]
        try:
            return "svn", int(rev_str)
        except ValueError:
            return "svn", rev_str
    try:
        ts = since.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        return "timestamp", dt.timestamp()
    except ValueError:
        raise ValueError(f"Invalid 'since' format. Use ISO timestamp (e.g., 2026-05-23T12:00:00Z), 'git:<commit-hash>', or 'svn:<revision>'.")


class DiskWatcher:
    """Polling-based file change detector with git/SVN integration."""

    @classmethod
    def watch(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get("target", "")
        since = params.get("since")
        recursive = params.get("recursive", True)
        include_ignored = params.get("include_ignored", False)
        included_events = params.get("events", ["create", "modify", "delete", "rename", "attribute"])
        detailed = params.get("format", "simple") == "detailed"
        max_changes = min(params.get("max_changes", 500), 5000)
        timeout_seconds = params.get("timeout_seconds", 60)

        target_path = Path(target).resolve()
        if not target_path.exists():
            raise ApiError(f"Target path does not exist: {target}", status_code=404, error_code="FS_006")

        try:
            method, since_value = _parse_since(since)
        except ValueError as e:
            raise ApiError(str(e), status_code=400, error_code="FS_006", details={"provided": since})

        deadline = time.time() + timeout_seconds
        changes: List[Dict[str, Any]] = []
        scan_method = method

        try:
            if method == "timestamp":
                changes = cls._scan_by_timestamp(target_path, since_value, recursive, included_events, detailed, deadline)
            elif method == "git":
                changes = cls._get_git_changes(target_path, since_value, included_events, include_ignored, detailed, deadline)
                scan_method = "git"
            elif method == "svn":
                changes = cls._get_svn_changes(target_path, since_value, included_events, include_ignored, detailed, deadline)
                scan_method = "svn"
            else:
                changes = cls._get_current_status(target_path, recursive, included_events, include_ignored, detailed, deadline)
                scan_method = "current_state"
        except TimeoutError:
            raise ApiError(
                f"Watch scan timed out after {timeout_seconds}s",
                status_code=408,
                error_code="FS_006",
                details={"target": _norm(str(target_path)), "partial_changes": changes[:max_changes]},
            )

        changes = changes[:max_changes]

        summary: Dict[str, int] = {}
        for c in changes:
            ev = c.get("event", "unknown")
            summary[ev] = summary.get(ev, 0) + 1

        data: Dict[str, Any] = {
            "target": _norm(str(target_path)),
            "since": since,
            "scan_method": scan_method,
            "summary": summary,
            "changes": changes,
        }

        if method == "git":
            try:
                branch = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=str(target_path) if target_path.is_dir() else str(target_path.parent),
                    capture_output=True, text=True, timeout=5,
                )
                if branch.returncode == 0:
                    data["current_branch"] = branch.stdout.strip()
            except Exception as e:
                    logger.debug(f"Watch operation warning: {e}")
        elif method == "svn":
            try:
                root = target_path if target_path.is_dir() else target_path.parent
                info = subprocess.run(
                    ["svn", "info", "--show-item", "revision"],
                    cwd=str(root), capture_output=True, text=True, timeout=5,
                )
                if info.returncode == 0 and info.stdout.strip():
                    data["current_revision"] = int(info.stdout.strip())
            except Exception as e:
                    logger.debug(f"Watch operation warning: {e}")

        return {"status_code": 200, "message": f"Found {len(changes)} change(s) since {since or 'current state'}", "data": data}

    @classmethod
    def _scan_by_timestamp(cls, target: Path, since_ts: float, recursive: bool,
                           events: List[str], detailed: bool, deadline: float) -> List[Dict[str, Any]]:
        changes: List[Dict[str, Any]] = []

        def _walk() -> List[Path]:
            if target.is_file():
                return [target]
            if not recursive:
                return [p for p in target.iterdir() if p.is_file()]
            result: List[Path] = []
            for root, _dirs, fnames in os.walk(str(target)):
                if time.time() > deadline:
                    raise TimeoutError("Scan timed out")
                for fn in fnames:
                    result.append(Path(root) / fn)
            return result

        for fp in _walk():
            if time.time() > deadline:
                raise TimeoutError("Scan timed out")
            try:
                st = fp.stat()
                if st.st_mtime >= since_ts:
                    if cls._event_allowed("modified", events):
                        changes.append(cls._build_entry(fp, "modified", detailed))
            except OSError:
                continue

        return changes

    @classmethod
    def _get_git_changes(cls, target: Path, revision: str, events: List[str],
                         include_ignored: bool, detailed: bool, deadline: float) -> List[Dict[str, Any]]:
        from src.modules.filesystem.adapters.git import DiskGit
        changes: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        git_root = DiskGit.find_root(target)
        if not git_root:
            return changes

        cwd = str(git_root)

        try:
            diff_proc = subprocess.run(
                ["git", "diff", "--name-status", f"{revision}..HEAD"],
                cwd=cwd, capture_output=True, text=True, timeout=10,
            )
            if diff_proc.returncode == 0 and diff_proc.stdout.strip():
                for line in diff_proc.stdout.splitlines():
                    if time.time() > deadline:
                        raise TimeoutError("Scan timed out")
                    line = line.strip()
                    if not line or "\t" not in line:
                        continue
                    sc, _, fp = line.partition("\t")
                    rel = _norm(fp)
                    if rel in seen:
                        continue
                    seen.add(rel)
                    ev = cls._git_char_to_event(sc)
                    if not cls._event_allowed(ev, events):
                        continue
                    entry = cls._build_entry(git_root / fp, ev, detailed)
                    entry["git_status"] = cls._git_char_to_label(sc)
                    if detailed and ev == "modified":
                        entry["diff"] = cls._get_git_file_diff(cwd, revision, fp)
                    changes.append(entry)
        except subprocess.TimeoutExpired:
            pass

        try:
            stat_proc = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd, capture_output=True, text=True, timeout=10,
            )
            if stat_proc.returncode == 0 and stat_proc.stdout.strip():
                for line in stat_proc.stdout.splitlines():
                    if time.time() > deadline:
                        raise TimeoutError("Scan timed out")
                    line = line.strip()
                    if len(line) < 3:
                        continue
                    staged = line[0]
                    working = line[1]
                    if not include_ignored and (staged == "!" or working == "!"):
                        continue
                    fp = line[3:].strip()
                    if staged == "R" or working == "R":
                        parts = fp.split(" -> ")
                        fp = parts[-1] if len(parts) > 1 else fp
                    rel = _norm(fp)
                    effective = working if working != " " else staged
                    ev = cls._git_char_to_event(effective)
                    if not cls._event_allowed(ev, events):
                        continue
                    if rel in seen:
                        for c in changes:
                            if c.get("path") == rel:
                                c["git_status"] = cls._git_char_to_label(effective)
                        continue
                    seen.add(rel)
                    entry = cls._build_entry(git_root / fp, ev, detailed)
                    entry["git_status"] = cls._git_char_to_label(effective)
                    changes.append(entry)
        except subprocess.TimeoutExpired:
            pass

        return changes

    @classmethod
    def _get_svn_changes(cls, target: Path, revision: int, events: List[str],
                         include_ignored: bool, detailed: bool, deadline: float) -> List[Dict[str, Any]]:
        from src.modules.filesystem.adapters.svn import DiskSvn
        changes: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        svn_root = DiskSvn.find_root(target)
        if not svn_root:
            return changes

        cwd = str(svn_root)

        try:
            diff_proc = subprocess.run(
                ["svn", "diff", "--summarize", "-r", f"{revision}:HEAD"],
                cwd=cwd, capture_output=True, text=True, timeout=10,
            )
            if diff_proc.returncode == 0 and diff_proc.stdout.strip():
                for line in diff_proc.stdout.splitlines():
                    if time.time() > deadline:
                        raise TimeoutError("Scan timed out")
                    line = line.strip()
                    if not line or len(line) < 2:
                        continue
                    sc = line[0]
                    fp = line[1:].strip()
                    rel = _norm(fp)
                    if rel in seen:
                        continue
                    seen.add(rel)
                    ev = cls._svn_char_to_event(sc)
                    if not cls._event_allowed(ev, events):
                        continue
                    entry = cls._build_entry((svn_root / fp).resolve(), ev, detailed)
                    entry["svn_status"] = cls._svn_char_to_label(sc)
                    if len(line) > 1 and line[1] == "M":
                        entry["svn_prop_changes"] = True
                    if detailed and ev == "modified":
                        entry["diff"] = cls._get_svn_file_diff(cwd, revision, fp)
                    changes.append(entry)
        except subprocess.TimeoutExpired:
            pass

        try:
            stat_proc = subprocess.run(
                ["svn", "status", "--non-interactive"],
                cwd=cwd, capture_output=True, text=True, timeout=10,
            )
            if stat_proc.returncode == 0 and stat_proc.stdout.strip():
                for line in stat_proc.stdout.splitlines():
                    if time.time() > deadline:
                        raise TimeoutError("Scan timed out")
                    line = line.strip()
                    if not line or len(line) < 8:
                        continue
                    sc = line[0]
                    if not include_ignored and sc == "I":
                        continue
                    fp = line[7:].strip()
                    rel = _norm(fp)
                    ev = cls._svn_char_to_event(sc)
                    label = cls._svn_char_to_label(sc)
                    if not cls._event_allowed(ev, events):
                        continue
                    if rel in seen:
                        for c in changes:
                            if c.get("path") == rel:
                                c["svn_status"] = label
                        continue
                    seen.add(rel)
                    entry = cls._build_entry((svn_root / fp).resolve(), ev, detailed)
                    entry["svn_status"] = label
                    changes.append(entry)
        except subprocess.TimeoutExpired:
            pass

        return changes

    @classmethod
    def _get_current_status(cls, target: Path, recursive: bool,
                            events: List[str], include_ignored: bool, detailed: bool, deadline: float) -> List[Dict[str, Any]]:
        from src.modules.filesystem.adapters.git import DiskGit
        from src.modules.filesystem.adapters.svn import DiskSvn

        git_root = DiskGit.find_root(target)
        svn_root = DiskSvn.find_root(target)
        changes: List[Dict[str, Any]] = []

        def _walk() -> List[Path]:
            if target.is_file():
                return [target]
            if not recursive:
                return [p for p in target.iterdir() if p.is_file()]
            result: List[Path] = []
            for root, _dirs, fnames in os.walk(str(target)):
                if time.time() > deadline:
                    raise TimeoutError("Scan timed out")
                for fn in fnames:
                    result.append(Path(root) / fn)
            return result

        for fp in _walk():
            if time.time() > deadline:
                raise TimeoutError("Scan timed out")
            try:
                st = fp.stat()
                entry: Dict[str, Any] = {
                    "path": _norm(str(fp)),
                    "event": "current",
                    "timestamp": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "size_bytes": st.st_size,
                }
            except OSError:
                entry = {"path": _norm(str(fp)), "event": "current"}

            if detailed and fp.exists():
                try:
                    entry["permissions"] = oct(fp.stat().st_mode)[-3:]
                except OSError:
                    pass

            if git_root:
                try:
                    rel = fp.relative_to(git_root)
                    gs = subprocess.run(
                        ["git", "status", "--porcelain", "--", str(rel)],
                        cwd=str(git_root), capture_output=True, text=True, timeout=5,
                    )
                    if gs.returncode == 0 and gs.stdout.strip():
                        gi = gs.stdout.strip()[1:2].strip() or gs.stdout.strip()[0:1].strip()
                        entry["git_status"] = cls._git_char_to_label(gi)
                except (ValueError, OSError):
                    pass

            if svn_root:
                try:
                    rel = fp.relative_to(svn_root)
                    ss = subprocess.run(
                        ["svn", "status", "--non-interactive", str(rel)],
                        cwd=str(svn_root), capture_output=True, text=True, timeout=5,
                    )
                    if ss.returncode == 0 and ss.stdout.strip():
                        svn_char = ss.stdout.strip()[0]
                        entry["svn_status"] = cls._svn_char_to_label(svn_char)
                except (ValueError, OSError):
                    pass

            changes.append(entry)

        return changes

    @classmethod
    def _build_entry(cls, path: Path, event: str, detailed: bool) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "path": _norm(str(path)),
            "event": event,
        }
        try:
            if path.exists():
                st = path.stat()
                entry["timestamp"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                entry["size_bytes"] = st.st_size
        except OSError:
            pass
        if detailed and path.exists() and event == "modified":
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                entry["content_preview"] = content[:500]
            except Exception as e:
                    logger.debug(f"Watch operation warning: {e}")
        return entry

    @classmethod
    def _get_git_file_diff(cls, cwd: str, revision: str, filepath: str) -> Optional[List[Dict[str, str]]]:
        try:
            result = subprocess.run(
                ["git", "diff", f"{revision}..HEAD", "--", filepath],
                cwd=cwd, capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None
            return cls._parse_diff_hunks(result.stdout)
        except Exception:
            return None

    @classmethod
    def _get_svn_file_diff(cls, cwd: str, revision: int, filepath: str) -> Optional[List[Dict[str, str]]]:
        try:
            result = subprocess.run(
                ["svn", "diff", "-r", f"{revision}:HEAD", filepath],
                cwd=cwd, capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None
            return cls._parse_diff_hunks(result.stdout)
        except Exception:
            return None

    @classmethod
    def _parse_diff_hunks(cls, diff_text: str) -> List[Dict[str, str]]:
        hunks: List[Dict[str, str]] = []
        current: Optional[Dict[str, str]] = None
        for line in diff_text.splitlines():
            if line.startswith("@@"):
                if current:
                    hunks.append(current)
                current = {"range": line, "content": line + "\n"}
            elif current is not None:
                current["content"] += line + "\n"
        if current:
            hunks.append(current)
        return hunks

    _EVENT_TO_FILTER = {
        "created": "create", "modified": "modify", "deleted": "delete",
        "rename": "rename", "attribute": "attribute",
        "missing": "delete", "current": "current", "unknown": "unknown",
    }

    @classmethod
    def _event_allowed(cls, event: str, events: List[str]) -> bool:
        if not events:
            return True
        return cls._EVENT_TO_FILTER.get(event, event) in events

    @classmethod
    def _git_char_to_event(cls, c: str) -> str:
        return {"M": "modified", "A": "created", "D": "deleted",
                "R": "rename", "C": "created", "U": "modified",
                "?": "created", "!": "missing"}.get(c, "modified")

    @classmethod
    def _git_char_to_label(cls, c: str) -> str:
        return {"M": "modified", "A": "added", "D": "deleted",
                "R": "renamed", "C": "copied", "U": "updated",
                "?": "untracked", "!": "ignored", " ": "unmodified"}.get(c, c)

    @classmethod
    def _svn_char_to_event(cls, c: str) -> str:
        return {"M": "modified", "A": "created", "D": "deleted",
                "R": "modified", "C": "modified", "?": "created",
                "!": "missing", "I": "ignored", "X": "external",
                "~": "obstructed"}.get(c, "modified")

    @classmethod
    def _svn_char_to_label(cls, c: str) -> str:
        return {"M": "M", "A": "A", "D": "D", "R": "R",
                "C": "C", "?": "?", "!": "!", "I": "I",
                "X": "X", "~": "~", " ": " "}.get(c, c)
