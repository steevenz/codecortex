"""
Chmod.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Chmod
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
import stat as stat_module
from datetime import datetime, timezone
import uuid

from src.modules.filesystem.adapters.reader import _norm
from src.core import ApiError


class DiskChmod:
    def __init__(self):
        pass

    def chmod(self, params: Dict[str, Any]) -> Dict[str, Any]:
        paths = params.get("paths", [])
        mode = params.get("mode", "755")
        modes = params.get("modes")
        recursive = params.get("recursive", False)
        dry_run = params.get("dry_run", False)
        if not paths:
            return self._respond(False, 400, "paths is required for chmod")

        try:
            if isinstance(mode, str) and any(c in mode for c in "rwxugo"):
                mode_int = self._parse_symbolic_mode(mode)
            else:
                mode_int = int(str(mode), 8) if isinstance(mode, str) else int(mode)
        except (ValueError, TypeError):
            return self._respond(False, 400, f"Invalid mode: {mode}")

        is_windows = os.name == "nt"
        results = []
        errors = []
        total_recursive = 0

        for i, p in enumerate(paths):
            resolved = Path(p).resolve()
            if not resolved.exists():
                errors.append({"path": _norm(str(resolved)), "error": "Path does not exist"})
                continue

            path_mode = mode_int
            if modes and i < len(modes):
                try:
                    path_mode = int(str(modes[i]), 8)
                except (ValueError, TypeError):
                    pass

            if dry_run:
                stat_info = resolved.stat()
                results.append({
                    "path": _norm(str(resolved)),
                    "status": "dry_run",
                    "current_mode": oct(stat_module.S_IMODE(stat_info.st_mode)),
                    "current_mode_human": stat_module.filemode(stat_info.st_mode),
                    "proposed_mode": oct(path_mode),
                    "proposed_mode_human": stat_module.filemode(path_mode),
                    "platform_note": "Windows only: readonly bit will be applied" if is_windows else None,
                })
                continue

            try:
                if is_windows:
                    readonly = not bool(path_mode & stat_module.S_IWRITE)
                    current_readonly = not os.access(resolved, os.W_OK)
                    os.chmod(resolved, path_mode)
                    results.append({
                        "path": _norm(str(resolved)),
                        "status": "changed",
                        "readonly_set": readonly,
                        "original_readonly": current_readonly,
                        "actual_effect": "read-only" if readonly else "read-write",
                        "proposed_mode": oct(path_mode),
                        "platform_warning": "Windows only supports readonly flag. Full POSIX permissions ignored.",
                    })
                else:
                    old_stat = resolved.stat()
                    old_mode = oct(stat_module.S_IMODE(old_stat.st_mode))
                    old_mode_human = stat_module.filemode(old_stat.st_mode)
                    os.chmod(resolved, path_mode)
                    new_stat = resolved.stat()
                    new_mode = oct(stat_module.S_IMODE(new_stat.st_mode))
                    new_mode_human = stat_module.filemode(new_stat.st_mode)
                    entry = {
                        "path": _norm(str(resolved)), "status": "changed",
                        "old_mode": old_mode, "old_mode_human": old_mode_human,
                        "new_mode": new_mode, "new_mode_human": new_mode_human,
                    }

                    if resolved.is_dir() and recursive:
                        count = 0
                        for root, dirs, files in os.walk(resolved):
                            for name in dirs + files:
                                fp = Path(root) / name
                                try:
                                    os.chmod(fp, path_mode)
                                    count += 1
                                except OSError:
                                    pass
                        entry["recursive_count"] = count
                        total_recursive += count

                    results.append(entry)
            except OSError as e:
                errors.append({"path": _norm(str(resolved)), "error": str(e)})

        msg = f"Permissions changed on {len(results)} items"
        if is_windows:
            msg += " with limitations (Windows)"
        if errors:
            msg += f", {len(errors)} failed"
        if total_recursive:
            msg += f" (recursive: {total_recursive} child items)"

        data: Dict[str, Any] = {"operation": "chmod", "mode_requested": str(mode), "mode_octal": mode_int, "results": results}
        if is_windows:
            data["platform_warning"] = "Windows only supports readonly flag. Full POSIX permissions ignored."
        if errors:
            data["errors"] = errors

        return self._respond(True, 200 if not errors else 207, msg, data)

    def _respond(self, success: bool, status_code: int, message: str, data: Any = None) -> Dict[str, Any]:
        if not success or int(status_code) >= 400:
            raise ApiError(message, status_code=int(status_code), error_code="FS_004")
        return {"status_code": int(status_code), "message": message, "data": data}

    def _parse_symbolic_mode(self, mode_str: str) -> int:
        mode_str = mode_str.strip()
        if mode_str.isdigit():
            return int(mode_str, 8)

        current = 0
        parts = mode_str.split(",")
        for part in parts:
            part = part.strip()
            m = __import__("re").match(r"([ugoa]*)([+\-=])([rwx]+)", part)
            if not m:
                continue
            who, op, perm = m.group(1), m.group(2), m.group(3)
            who = who or "a"
            bits = 0
            for c in perm:
                if c == "r":
                    bits |= 0o444
                elif c == "w":
                    bits |= 0o222
                elif c == "x":
                    bits |= 0o111
            if "u" in who:
                if op == "+":
                    current |= (bits & 0o700)
                elif op == "-":
                    current &= ~(bits & 0o700)
                elif op == "=":
                    current = (current & ~0o700) | (bits & 0o700)
            if "g" in who:
                if op == "+":
                    current |= (bits & 0o070)
                elif op == "-":
                    current &= ~(bits & 0o070)
                elif op == "=":
                    current = (current & ~0o070) | (bits & 0o070)
            if "o" in who or "a" in who or (who == "" and op != "="):
                if op == "+":
                    current |= (bits & 0o007)
                elif op == "-":
                    current &= ~(bits & 0o007)
                elif op == "=":
                    current = (current & ~0o007) | (bits & 0o007)
        return current
