"""
Chown.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Chown
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
import os
from datetime import datetime, timezone
import uuid

from src.modules.filesystem.adapters.reader import _norm, _get_owner, _get_group
from src.core import ApiError


class DiskChown:
    def __init__(self):
        pass

    def chown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        paths = params.get("paths", [])
        owner = params.get("owner")
        group = params.get("group")
        recursive = params.get("recursive", False)
        dry_run = params.get("dry_run", False)
        if not paths:
            return self._respond(False, 400, "paths is required for chown")
        if not owner and not group:
            return self._respond(False, 400, "At least one of owner or group is required")

        if os.name == "nt":
            return self._respond(False, 400, "chown operation is not supported on Windows. Use Windows ACL tools separately.")

        uid = -1
        gid = -1
        owner_name = ""
        group_name = ""

        try:
            if owner:
                try:
                    uid = int(owner)
                except ValueError:
                    import pwd
                    pw = pwd.getpwnam(owner)
                    uid = pw.pw_uid
                    owner_name = owner
            if group:
                try:
                    gid = int(group)
                except ValueError:
                    import grp
                    gr = grp.getgrnam(group)
                    gid = gr.gr_gid
                    group_name = group
        except (ImportError, KeyError) as e:
            return self._respond(False, 400, f"Cannot resolve user/group: {e}")

        results = []
        errors = []

        for p in paths:
            resolved = Path(p).resolve()
            if not resolved.exists():
                errors.append({"path": _norm(str(resolved)), "error": "Path does not exist"})
                continue

            import mimetypes
            if dry_run:
                stat_info = resolved.stat()
                old_owner = _get_owner(stat_info)
                old_group = _get_group(stat_info)
                dry_entry: Dict[str, Any] = {
                    "path": _norm(str(resolved)), "status": "dry_run",
                    "is_directory": resolved.is_dir(),
                    "current_owner": old_owner, "current_group": old_group,
                    "proposed_owner": owner_name or old_owner,
                    "proposed_group": group_name or old_group,
                }
                if not resolved.is_dir():
                    mime, _ = mimetypes.guess_type(str(resolved))
                    dry_entry["file_type"] = mime or "application/octet-stream"
                results.append(dry_entry)
                continue

            try:
                old_stat = resolved.stat()
                old_owner = _get_owner(old_stat)
                old_group = _get_group(old_stat)

                os.chown(resolved, uid if uid != -1 else -1, gid if gid != -1 else -1)
                entry: Dict[str, Any] = {
                    "path": _norm(str(resolved)), "status": "changed",
                    "is_directory": resolved.is_dir(),
                    "old_owner": old_owner, "new_owner": owner_name or old_owner,
                    "old_group": old_group, "new_group": group_name or old_group,
                }
                if not resolved.is_dir():
                    mime, _ = mimetypes.guess_type(str(resolved))
                    entry["file_type"] = mime or "application/octet-stream"

                if resolved.is_dir() and recursive:
                    count = 0
                    for root, dirs, files in os.walk(resolved):
                        for name in dirs + files:
                            fp = Path(root) / name
                            try:
                                os.chown(fp, uid if uid != -1 else -1, gid if gid != -1 else -1)
                                count += 1
                            except OSError:
                                pass
                    entry["recursive_count"] = count

                results.append(entry)
            except PermissionError:
                errors.append({"path": _norm(str(resolved)),
                                "error": "Permission denied: chown requires root/administrator privileges"})
            except OSError as e:
                errors.append({"path": _norm(str(resolved)), "error": str(e)})

        data: Dict[str, Any] = {"operation": "chown", "owner": owner, "group": group,
                                 "results": results, "errors": errors if errors else None}

        msg = f"Ownership changed for {len(results)} items"
        if errors:
            msg += f", {len(errors)} failed"
        return self._respond(True, 200 if not errors else 207, msg, data)

    def _respond(self, success: bool, status_code: int, message: str, data: Any = None) -> Dict[str, Any]:
        if not success or int(status_code) >= 400:
            raise ApiError(message, status_code=int(status_code), error_code="FS_004")
        return {"status_code": int(status_code), "message": message, "data": data}
