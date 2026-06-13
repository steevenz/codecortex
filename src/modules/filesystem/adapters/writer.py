"""
Class DiskWriter – Cross-platform filesystem writer.
Wraps DiskReader.write_to_disk for CLI and MCP tool compatibility.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Writer
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
import os
import base64
import hashlib
import shutil
import stat as stat_module
from datetime import datetime, timezone

from src.core import ApiError

from src.core.utils.path import norm_path as _norm
from src.core.config.environment import utc_ts_to_iso as _utc_from_ts

def _get_owner(stat_info: os.stat_result) -> str:
    if os.name in ("posix",):
        try:
            import pwd
            return pwd.getpwuid(stat_info.st_uid).pw_name
        except (ImportError, KeyError):
            pass
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return str(stat_info.st_uid)

def _get_group(stat_info: os.stat_result) -> str:
    if os.name in ("posix",):
        try:
            import grp
            return grp.getgrgid(stat_info.st_gid).gr_name
        except (ImportError, KeyError):
            pass
    return str(stat_info.st_gid)

def _get_created_ts(stat_info: os.stat_result) -> float:
    if hasattr(stat_info, "st_birthtime"):
        return stat_info.st_birthtime
    return stat_info.st_ctime

class DiskWriter:
    """
    Cross-platform filesystem writer for creating and modifying files.
    Supports: text (utf8), binary (base64), directory creation, atomic writes,
    backup before overwrite, and permission handling.
    """

    def __init__(self):
        pass

    def write(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params.get("path", "")
        content = params.get("content", "")
        encoding = params.get("encoding", "utf8")
        write_mode = params.get("write_mode", "create")
        is_directory = params.get("is_directory", False)
        permissions = params.get("permissions")
        create_parents = params.get("create_parents", True)
        backup_existing = params.get("backup_existing", False)
        atomic_write = params.get("atomic_write", True)
        dry_run = params.get("dry_run", False)
        operation = params.get("operation", "write")

        if dry_run:
            resolved = Path(path).resolve()
            exists = resolved.exists()
            existing_size = resolved.stat().st_size if exists else None
            content_bytes = content.encode("utf-8") if isinstance(content, str) and encoding != "base64" else None
            import hashlib
            dry_data: Dict[str, Any] = {
                "operation": operation, "dry_run": True, "path": _norm(str(resolved)),
                "would_create": not exists,
                "would_overwrite": exists and write_mode == "overwrite",
                "would_append": operation == "append" and exists,
                "content_size_bytes": len(content_bytes) if content_bytes else len(content),
                "estimated_lines": content.count("\n") + 1 if isinstance(content, str) else None,
                "sha256_preview": hashlib.sha256(content_bytes).hexdigest()[:16] + "..." if content_bytes else None,
                "encoding": encoding,
            }
            if exists:
                dry_data["existing_size_bytes"] = existing_size
                dry_data["existing_modified"] = _utc_from_ts(resolved.stat().st_mtime)
                if not is_directory and write_mode == "create":
                    dry_data["next_action"] = "Use overwrite=true to replace or append mode to extend."
            return {
                "status_code": 200,
                "message": "DRY RUN: No changes made",
                "data": dry_data,
            }

        result = self._write_to_disk(
            path,
            content,
            encoding=encoding,
            write_mode=write_mode,
            is_directory=is_directory,
            permissions=permissions,
            create_parents=create_parents,
            backup_existing=backup_existing,
            atomic_write=atomic_write,
        )

        if "error" in result:
            raise ApiError(
                str(result.get("error")),
                status_code=int(result.get("status_code", 500)),
                error_code="FS_004",
                details=result.get("data"),
            )

        response = self._format_response(write_mode, is_directory, result)

        return response

    def _write_to_disk(
        self,
        path: str,
        content: str,
        encoding: str,
        write_mode: str,
        is_directory: bool,
        permissions: Optional[int],
        create_parents: bool,
        backup_existing: bool,
        atomic_write: bool,
    ) -> Dict[str, Any]:
        resolved = Path(path).resolve()

        if ".." in path.split("/") or ".." in path.split("\\"):
            return {
                "error": "Path traversal detected",
                "status_code": 400,
                "data": {
                    "provided_path": path,
                    "resolved_path": _norm(str(resolved)),
                    "reason": "Path contains parent directory references ('..')",
                }
            }

        if is_directory:
            return self._write_directory(resolved, write_mode, create_parents, permissions)

        return self._write_file(
            resolved, content, encoding, write_mode, create_parents,
            backup_existing, atomic_write, permissions
        )

    def _write_directory(
        self,
        resolved: Path,
        write_mode: str,
        create_parents: bool,
        permissions: Optional[int],
    ) -> Dict[str, Any]:
        if resolved.exists() and resolved.is_dir():
            if write_mode == "create":
                return {
                    "error": "Directory already exists",
                    "status_code": 409,
                    "data": {
                        "existing_path": _norm(str(resolved)),
                        "last_modified": _utc_from_ts(resolved.stat().st_mtime),
                    }
                }
        elif resolved.exists() and not resolved.is_dir():
            return {"error": f"Path exists but is not a directory: {resolved}", "status_code": 400}

        created_paths = []
        try:
            if create_parents:
                parent = resolved.parent
                if not parent.exists():
                    parts = []
                    for p in resolved.parents:
                        if not p.exists():
                            parts.append(p)
                        else:
                            break
                    parts.reverse()
                    for p in parts:
                        p.mkdir(exist_ok=True)
                        created_paths.append(_norm(str(p)))
                        if permissions and os.name == "posix":
                            p.chmod(permissions)

            resolved.mkdir(exist_ok=(write_mode == "overwrite"))
            created_paths.append(_norm(str(resolved)))
            if permissions and os.name == "posix":
                resolved.chmod(permissions)

            stat_info = resolved.stat()
            return {
                "operation": "create_directory",
                "path": _norm(str(resolved)),
                "created_paths": created_paths,
                "permissions": int(stat_module.S_IMODE(stat_info.st_mode)),
                "owner": _get_owner(stat_info),
                "group": _get_group(stat_info),
                "created": _utc_from_ts(_get_created_ts(stat_info)),
            }
        except PermissionError:
            return {
                "error": "Permission denied: cannot create directory",
                "status_code": 403,
                "data": {
                    "path": _norm(str(resolved)),
                    "error_detail": "PermissionError: Access denied",
                    "platform_hint": "Try running with elevated privileges or choose a writable directory.",
                }
            }
        except OSError as e:
            return {"error": f"Cannot create directory: {e}", "status_code": 500}

    def _write_file(
        self,
        resolved: Path,
        content: str,
        encoding: str,
        write_mode: str,
        create_parents: bool,
        backup_existing: bool,
        atomic_write: bool,
        permissions: Optional[int],
    ) -> Dict[str, Any]:
        if resolved.exists() and resolved.is_dir():
            return {"error": f"Path is a directory, not a file: {resolved}", "status_code": 400}

        if resolved.exists() and write_mode == "create":
            stat_info = resolved.stat()
            return {
                "error": "File already exists. Use overwrite=true or append mode to modify.",
                "status_code": 409,
                "data": {
                    "existing_file": _norm(str(resolved)),
                    "existing_size_bytes": stat_info.st_size,
                    "last_modified": _utc_from_ts(stat_info.st_mtime),
                    "next_action": "Set overwrite=true to replace, or use operation='append' to add content.",
                }
            }

        if create_parents:
            try:
                resolved.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                return {"error": "Permission denied: cannot create parent directories", "status_code": 403}
            except OSError as e:
                return {"error": f"Cannot create parent directories: {e}", "status_code": 500}

        is_binary = encoding == "base64"
        data: bytes | str
        try:
            if is_binary:
                data = base64.b64decode(content)
            else:
                data = content
        except Exception as e:
            return {"error": f"Invalid {encoding} encoding: {e}", "status_code": 400}

        try:
            if write_mode == "append":
                original_size = resolved.stat().st_size if resolved.exists() else 0
                mode = "ab" if is_binary else "a"
                enc = None if is_binary else "utf-8"
                with open(resolved, mode, encoding=enc) as f:
                    f.write(data)
                stat_info = resolved.stat()
                appended_bytes = len(data) if is_binary else len(data.encode("utf-8"))
                append_result: Dict[str, Any] = {
                    "operation": "append",
                    "path": _norm(str(resolved)),
                    "original_size_bytes": original_size,
                    "appended_bytes": appended_bytes,
                    "new_size_bytes": stat_info.st_size,
                    "modified": _utc_from_ts(stat_info.st_mtime),
                }
                if not is_binary:
                    append_result["appended_lines"] = data.count("\n") + 1 if isinstance(data, str) else 0
                return append_result

            original_size = 0
            original_stat = None
            if resolved.exists():
                original_stat = resolved.stat()
                original_size = original_stat.st_size

            backup_path = None
            if backup_existing and resolved.exists():
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                backup_path = resolved.with_name(resolved.name + f".bak.{ts}")
                shutil.copy2(resolved, backup_path)

            if atomic_write:
                temp = resolved.with_name(resolved.name + ".tmp." + str(os.getpid()))
                try:
                    mode = "wb" if is_binary else "w"
                    enc = None if is_binary else "utf-8"
                    with open(temp, mode, encoding=enc) as f:
                        f.write(data)
                    shutil.move(str(temp), str(resolved))
                except Exception:
                    if temp.exists():
                        temp.unlink()
                    raise
            else:
                mode = "wb" if is_binary else "w"
                enc = None if is_binary else "utf-8"
                with open(resolved, mode, encoding=enc) as f:
                    f.write(data)

            if permissions and os.name == "posix":
                resolved.chmod(permissions)

            stat_info = resolved.stat()
            result = {
                "operation": "write_file",
                "path": _norm(str(resolved)),
                "size_bytes": stat_info.st_size,
                "write_mode": write_mode,
                "backup_created": backup_path is not None,
                "atomic_write_used": atomic_write,
                "modified": _utc_from_ts(stat_info.st_mtime),
            }

            if backup_path:
                result["backup_path"] = _norm(str(backup_path))
                result["original_size_bytes"] = original_size

            mime, _ = self._guess_mime_type(str(resolved))
            if mime:
                result["file_type"] = mime

            if is_binary:
                content_bytes = content.encode("ascii") if isinstance(content, str) else content
                result["sha256_checksum"] = hashlib.sha256(content_bytes).hexdigest()
                result["checksum_algorithm"] = "sha256"
            else:
                text_bytes = data.encode("utf-8") if isinstance(data, str) else b""
                result["sha256_checksum"] = hashlib.sha256(text_bytes).hexdigest()
                result["checksum_algorithm"] = "sha256"
                result["line_count"] = data.count("\n") + 1 if isinstance(data, str) else 0

            result["permissions"] = int(stat_module.S_IMODE(stat_info.st_mode))
            result["owner"] = _get_owner(stat_info)
            result["group"] = _get_group(stat_info)
            if write_mode != "overwrite":
                result["created"] = _utc_from_ts(_get_created_ts(stat_info))

            return result

        except PermissionError:
            return {
                "error": "Permission denied: cannot write to file",
                "status_code": 403,
                "data": {
                    "path": _norm(str(resolved)),
                    "error_detail": "PermissionError: [Errno 13] Access denied",
                    "platform_hint": "Try running with elevated privileges or choose a writable directory.",
                }
            }
        except OSError as e:
            return {"error": f"OS error: {e}", "status_code": 500}
        except Exception as e:
            return {"error": str(e), "status_code": 500}

    def _guess_mime_type(self, path: str) -> tuple:
        import mimetypes
        mimetypes.init()
        return mimetypes.guess_type(path)

    def write_batch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        items = params.get("items", [])
        if not items:
            raise ApiError("items is required for write_batch", status_code=400, error_code="FS_004")

        results = []
        errors = []
        for item in items:
            item_params = {
                "path": item.get("path", ""),
                "content": item.get("content", ""),
                "encoding": item.get("encoding", "utf8"),
                "write_mode": "overwrite" if item.get("overwrite", False) else "create",
                "permissions": item.get("permissions"),
                "create_parents": item.get("create_parents", True),
                "backup_existing": item.get("backup_existing", False),
                "atomic_write": item.get("atomic_write", True),
                "dry_run": params.get("dry_run", False),
            }
            try:
                r = self.write(item_params)
                results.append({"path": item.get("path", ""), "status": "written", "size": r.get("data", {}).get("size_bytes", 0)})
            except ApiError as e:
                errors.append({"path": item.get("path", ""), "error": str(e)})

        msg = f"Batch write: {len(results)} succeeded"
        if errors:
            msg += f", {len(errors)} failed"
        return {
            "status_code": 200 if not errors else 207,
            "message": msg,
            "data": {"results": results, "errors": errors if errors else None},
        }

    def _error_response(self, status_code: int, message: str) -> Dict[str, Any]:
        raise ApiError(message, status_code=int(status_code), error_code="FS_004")

    def _format_response(self, write_mode: str, is_directory: bool, result: Dict[str, Any]) -> Dict[str, Any]:
        message = self._get_message(write_mode, is_directory)
        return {"status_code": 200, "message": message, "data": result}

    def _get_message(self, write_mode: str, is_directory: bool) -> str:
        if is_directory:
            return "Directory created successfully"
        if write_mode == "create":
            return "File created successfully"
        if write_mode == "overwrite":
            return "File overwritten successfully"
        if write_mode == "append":
            return "Content appended successfully"
        return "Operation completed"
