"""
Touch.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Touch
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
import os
from datetime import datetime, timezone
import uuid

from src.modules.filesystem.adapters.reader import _norm, _utc_from_ts
from src.core import ApiError


class DiskTouch:
    def __init__(self):
        pass

    def touch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params.get("path", "")
        create_if_not_exists = params.get("create_if_not_exists", True)
        set_timestamps = params.get("set_timestamps", {})
        dry_run = params.get("dry_run", False)
        if not path:
            return self._respond(False, 400, "path is required for touch")

        resolved = Path(path).resolve()
        if resolved.is_dir():
            return self._respond(False, 400, "Cannot touch a directory. Use file path only.",
                                  {"path": _norm(str(resolved)), "is_directory": True})

        old_timestamps = None
        if resolved.exists():
            stat_info = resolved.stat()
            old_timestamps = {
                "access_time": _utc_from_ts(stat_info.st_atime),
                "modify_time": _utc_from_ts(stat_info.st_mtime),
            }

        import mimetypes
        if dry_run:
            dry_data: Dict[str, Any] = {
                "operation": "touch", "dry_run": True,
                "would_create": not resolved.exists(),
                "would_update_timestamps": True,
                "current_timestamps": old_timestamps,
                "proposed_timestamps": self._parse_timestamps(set_timestamps, old_timestamps),
            }
            if resolved.exists():
                try:
                    dry_data["file_type"] = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
                    dry_data["size_bytes"] = resolved.stat().st_size
                except OSError:
                    pass
            return self._respond(True, 200, "DRY RUN: No changes made", dry_data)

        created = False
        try:
            if not resolved.exists():
                if create_if_not_exists:
                    resolved.parent.mkdir(parents=True, exist_ok=True)
                    resolved.touch()
                    created = True
                else:
                    return self._respond(False, 404, "File not found and create_if_not_exists=false",
                                          {"path": _norm(str(resolved))})
        except Exception as e:
            return self._respond(False, 500, f"Failed to create file: {e}", {"path": _norm(str(resolved))})

        now = datetime.now(timezone.utc)
        proposed_ts = self._parse_timestamps(
            set_timestamps,
            old_timestamps or {"access_time": _utc_from_ts(now.timestamp()), "modify_time": _utc_from_ts(now.timestamp())},
        )

        try:
            atime = self._to_epoch(proposed_ts["access_time"])
            mtime = self._to_epoch(proposed_ts["modify_time"])
            os.utime(resolved, times=(atime, mtime))
        except Exception as e:
            return self._respond(False, 500, f"Failed to update timestamps: {e}", {"path": _norm(str(resolved))})

        final_stat = resolved.stat()
        new_timestamps = {
            "access_time": _utc_from_ts(final_stat.st_atime),
            "modify_time": _utc_from_ts(final_stat.st_mtime),
        }

        data: Dict[str, Any] = {
            "operation": "touch",
            "path": _norm(str(resolved)),
            "created": created,
            "old_timestamps": old_timestamps,
            "new_timestamps": new_timestamps,
        }
        try:
            data["file_type"] = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            data["size_bytes"] = resolved.stat().st_size
        except OSError:
            pass

        msg = "Timestamps updated" if not created else "File touched (created and/or timestamps updated)"
        return self._respond(True, 200, msg, data)

    def _respond(self, success: bool, status_code: int, message: str, data: Any = None) -> Dict[str, Any]:
        if not success or int(status_code) >= 400:
            raise ApiError(message, status_code=int(status_code), error_code="FS_008")
        return {"status_code": int(status_code), "message": message, "data": data}

    def _parse_timestamps(self, set_timestamps: Dict[str, str], current_timestamps: Optional[Dict[str, str]]) -> Dict[str, str]:
        now = datetime.now(timezone.utc)
        now_iso = _utc_from_ts(now.timestamp())
        current = current_timestamps or {"access_time": now_iso, "modify_time": now_iso}
        at = set_timestamps.get("access_time")
        mt = set_timestamps.get("modify_time")
        return {
            "access_time": at if at else current.get("access_time", now_iso),
            "modify_time": mt if mt else current.get("modify_time", now_iso),
        }

    def _to_epoch(self, iso_str: str) -> float:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()
