"""
Symlink.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Symlink
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
import os
import shutil
from datetime import datetime, timezone
import uuid

from src.modules.filesystem.adapters.reader import _norm
from src.core import ApiError


class DiskSymlink:
    def __init__(self):
        pass

    def symlink(self, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get("target", "")
        link_path = params.get("link_path", "")
        overwrite = params.get("overwrite", False)
        is_directory = params.get("is_directory", False)
        dry_run = params.get("dry_run", False)
        if not target or not link_path:
            return self._respond(False, 400, "target and link_path are required for symlink")

        resolved_target = Path(target).resolve()
        resolved_link = Path(link_path).resolve()

        if dry_run:
            target_exists = resolved_target.exists()
            target_is_dir = is_directory or (resolved_target.is_dir() if target_exists else False)
            return self._respond(True, 200, "DRY RUN: No changes made", {
                "operation": "symlink", "dry_run": True,
                "target": _norm(str(resolved_target)),
                "link_path": _norm(str(resolved_link)),
                "target_exists": target_exists,
                "target_is_directory": target_is_dir,
                "would_overwrite": resolved_link.exists() and overwrite,
            })

        if resolved_link.exists():
            if overwrite:
                if resolved_link.is_dir():
                    try:
                        resolved_link.rmdir()
                    except OSError:
                        shutil.rmtree(resolved_link)
                else:
                    resolved_link.unlink()
            else:
                return self._respond(False, 409, f"Link path already exists: {resolved_link}", {
                    "target": _norm(str(resolved_target)), "link_path": _norm(str(resolved_link)),
                    "suggestion": "Set overwrite=true to replace",
                })

        resolved_link.parent.mkdir(parents=True, exist_ok=True)

        try:
            target_is_dir = is_directory or (resolved_target.is_dir() if resolved_target.exists() else False)
            if os.name == "nt":
                os.symlink(str(resolved_target), str(resolved_link), target_is_directory=target_is_dir)
            else:
                os.symlink(str(resolved_target), str(resolved_link))
            link_type = "directory" if target_is_dir else "file"

            data: Dict[str, Any] = {
                "operation": "symlink",
                "target": _norm(str(resolved_target)),
                "link_path": _norm(str(resolved_link)),
                "type": link_type,
                "target_exists": target_exists,
                "target_is_directory": target_is_dir,
                "overwritten": overwrite and resolved_link.exists(),
            }

            return self._respond(True, 200, "Symbolic link created", data)
        except OSError as e:
            msg = f"Failed to create symlink: {e}"
            help_msg = ""
            if os.name == "nt" and "1314" in str(e):
                help_msg = "Enable Developer Mode or run as Administrator. See: https://docs.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development"
            elif "permission" in str(e).lower():
                help_msg = "Try running with elevated privileges."
            return self._respond(False, 403, msg + (" " + help_msg if help_msg else ""), {
                "target": _norm(str(resolved_target)),
                "link_path": _norm(str(resolved_link)),
                "error_detail": str(e),
                "help_link": "https://docs.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development" if os.name == "nt" else None,
            })

    def _respond(self, success: bool, status_code: int, message: str, data: Any = None) -> Dict[str, Any]:
        if not success or int(status_code) >= 400:
            raise ApiError(message, status_code=int(status_code), error_code="FS_007")
        return {"status_code": int(status_code), "message": message, "data": data}
