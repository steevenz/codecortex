"""
Extended attributes (xattr) operations: list, get, set, remove.
    Uses os.listxattr/getxattr/setxattr/removexattr on Unix.
    Returns 501 Not Supported on Windows.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Xattr
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

import os
import base64
from pathlib import Path
from typing import Any, Dict, List

from src.core.errors.errors import ApiError


def _is_unix() -> bool:
    """Check if running on a Unix-like OS (Linux/macOS)."""
    return os.name == "posix"


def _norm(path: str) -> str:
    """Normalize path to forward slashes."""
    return path.replace("\\", "/")


class DiskXattr:
    """Extended attributes (xattr) operations: list, get, set, remove."""

    @staticmethod
    def execute(params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action", "")
        path = params.get("path", "")
        name = params.get("name", "")
        value = params.get("value", "")
        encoding = params.get("encoding", "utf8")
        recursive = params.get("recursive", False)

        if not path:
            raise ApiError("path is required for xattr operation", status_code=400, error_code="FS_004")
        if not action:
            raise ApiError("action (list/get/set/remove) is required for xattr operation", status_code=400, error_code="FS_004")

        resolved = str(Path(path).resolve())
        if not os.path.exists(resolved):
            raise ApiError(f"Path not found: {resolved}", status_code=404, error_code="FS_004")

        if not _is_unix():
            raise ApiError(
                "Extended attributes are not supported on Windows. Use Alternate Data Streams (ADS) via 'file:stream' syntax.",
                status_code=501,
                error_code="FS_004",
                details={
                    "operation": "xattr",
                    "action": action,
                    "path": _norm(resolved),
                    "platform": "Windows",
                    "suggestion": "For Windows metadata, consider using NTFS streams with ':' in filename, e.g., 'file.txt:comment'",
                },
            )

        try:
            if action == "list":
                return DiskXattr._list(resolved)
            elif action == "get":
                if not name:
                    raise ApiError("name is required for xattr get", status_code=400, error_code="FS_004")
                return DiskXattr._get(resolved, name, encoding)
            elif action == "set":
                if not name:
                    raise ApiError("name is required for xattr set", status_code=400, error_code="FS_004")
                return DiskXattr._set(resolved, name, value, encoding, recursive)
            elif action == "remove":
                if not name:
                    raise ApiError("name is required for xattr remove", status_code=400, error_code="FS_004")
                return DiskXattr._remove(resolved, name, recursive)
            else:
                raise ApiError(f"Unknown xattr action: {action}. Use: list, get, set, remove", status_code=400, error_code="FS_004")
        except PermissionError:
            raise ApiError(f"Permission denied accessing extended attributes for: {resolved}", status_code=403, error_code="FS_004")
        except OSError as e:
            if "not supported" in str(e).lower() or "operation not supported" in str(e).lower():
                raise ApiError(f"Extended attributes not supported on this filesystem: {e}", status_code=501, error_code="FS_004")
            raise ApiError(f"Extended attribute error: {e}", status_code=400, error_code="FS_004")
        except Exception as e:
            raise ApiError(f"Extended attribute error: {e}", status_code=500, error_code="FS_004")

    @staticmethod
    def _list(path: str) -> Dict[str, Any]:
        names: List[str] = list(os.listxattr(path))
        import mimetypes
        mime, _ = mimetypes.guess_type(str(path))
        try:
            sz = path.stat().st_size if path.is_file() else None
        except OSError:
            sz = None
        return {
            "status_code": 200,
            "message": f"Extended attributes listed ({len(names)} attributes)",
            "data": {
                "operation": "xattr",
                "action": "list",
                "path": _norm(path),
                "file_type": mime or "application/octet-stream",
                "size_bytes": sz,
                "attributes": sorted(names),
                "platform": "Unix",
            },
        }

    @staticmethod
    def _get(path: str, name: str, encoding: str) -> Dict[str, Any]:
        raw = os.getxattr(path, name)
        if encoding == "base64":
            value = base64.b64encode(raw).decode("ascii")
        else:
            try:
                value = raw.decode("utf-8")
            except UnicodeDecodeError:
                value = base64.b64encode(raw).decode("ascii")
                encoding = "base64"

        return {
            "status_code": 200,
            "message": f"Extended attribute '{name}' retrieved",
            "data": {
                "operation": "xattr",
                "action": "get",
                "path": _n(path),
                "name": name,
                "value": value,
                "encoding": encoding,
                "size_bytes": len(raw),
                "file_type": mimetypes.guess_type(str(path))[0] or "application/octet-stream",
            },
        }

    @staticmethod
    def _set(path: str, name: str, value: str, encoding: str, recursive: bool) -> Dict[str, Any]:
        if encoding == "base64":
            raw = base64.b64decode(value)
        else:
            raw = value.encode("utf-8")

        paths_modified: List[str] = []
        targets = [path]
        if recursive and os.path.isdir(path):
            targets = []
            for root, dirs, files in os.walk(path):
                targets.extend(os.path.join(root, d) for d in dirs)
                targets.extend(os.path.join(root, f) for f in files)
                targets.append(root)

        for p in targets:
            try:
                os.setxattr(p, name, raw)
                paths_modified.append(_norm(p))
            except OSError as e:
                if not recursive:
                    raise
                # In recursive mode, skip individual errors

        return {
            "status_code": 200,
            "message": f"Extended attribute '{name}' set on {len(paths_modified)} path(s)",
            "data": {
                "operation": "xattr",
                "action": "set",
                "path": _norm(path),
                "name": name,
                "paths_modified": paths_modified,
                "recursive": recursive,
                "file_type": mimetypes.guess_type(str(path))[0] or "application/octet-stream",
            },
        }

    @staticmethod
    def _remove(path: str, name: str, recursive: bool) -> Dict[str, Any]:
        paths_modified: List[str] = []
        targets = [path]
        if recursive and os.path.isdir(path):
            targets = []
            for root, dirs, files in os.walk(path):
                targets.extend(os.path.join(root, d) for d in dirs)
                targets.extend(os.path.join(root, f) for f in files)
                targets.append(root)

        for p in targets:
            try:
                os.removexattr(p, name)
                paths_modified.append(_norm(p))
            except OSError as e:
                if not recursive:
                    raise

        return {
            "status_code": 200,
            "message": f"Extended attribute '{name}' removed from {len(paths_modified)} path(s)",
            "data": {
                "operation": "xattr",
                "action": "remove",
                "path": _norm(path),
                "name": name,
                "paths_modified": paths_modified,
                "recursive": recursive,
                "file_type": mimetypes.guess_type(str(path))[0] or "application/octet-stream",
            },
        }
