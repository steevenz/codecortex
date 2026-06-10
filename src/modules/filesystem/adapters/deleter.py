"""
Pure filesystem deleter and mover — no VCS operations.
Use repo_git/repo_svn in CodeRepository for version control.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Deleter
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path
import os
import shutil
from datetime import datetime, timezone

from src.core.utils.path import norm_path as _norm

class DiskDeleter:
    """Pure filesystem deleter — no VCS."""

    def delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        paths = params.get("paths", [])
        recursive = params.get("recursive", False)
        dry_run = params.get("dry_run", False)
        force = params.get("force", False)

        if not paths:
            return {"error": "paths parameter is required", "status_code": 400}

        results = []
        successful = 0
        failed = 0

        for p in paths:
            result = self._delete_one(p, recursive, dry_run, force)
            s = result.get("status")
            if s == "deleted":
                successful += 1
            elif s == "error":
                failed += 1
            results.append(result)

        status_code = 200 if failed == 0 else (207 if successful > 0 else 400)

        return {
            "success": failed == 0,
            "status_code": status_code,
            "message": f"All {successful} item(s) deleted successfully" if not failed else f"{successful} deleted, {failed} failed",
            "data": {
                "total_requests": len(paths),
                "successful": successful,
                "failed": failed,
                "results": results,
            },
            "meta": {
                "request_id": f"req_del_{os.urandom(4).hex()}",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        }

    def _delete_one(self, path: str, recursive: bool, dry_run: bool, force: bool) -> Dict[str, Any]:
        resolved = Path(path).resolve()
        is_dir = resolved.is_dir()
        exists = resolved.exists()

        if not exists:
            if force:
                return {"path": path, "status": "deleted", "note": "force: already missing"}
            return {"path": path, "status": "error", "error": "Path does not exist"}

        if dry_run:
            import mimetypes
            dry_entry: Dict[str, Any] = {
                "path": _norm(str(resolved)), "status": "dry_run", "dry_run": True,
                "message": "Would delete",
                "is_directory": is_dir,
            }
            try:
                st = resolved.stat()
                dry_entry["size_bytes"] = st.st_size if not is_dir else None
                if is_dir:
                    child_count = sum(1 for _ in resolved.iterdir()) if resolved.is_dir() else 0
                    dry_entry["child_count"] = child_count
                    dry_entry["warning"] = f"Will recursively delete {child_count} immediate children." if child_count > 0 else None
                else:
                    mime, _ = mimetypes.guess_type(str(resolved))
                    dry_entry["file_type"] = mime or "application/octet-stream"
            except OSError:
                pass
            return dry_entry

        try:
            file_stat = resolved.stat()
            perms = oct(file_stat.st_mode)[-3:]
            sz = file_stat.st_size
            if is_dir:
                if not recursive:
                    return {"path": _norm(str(resolved)), "status": "error", "error": "Is directory — use recursive=True"}
                shutil.rmtree(resolved)
            else:
                resolved.unlink()
            import mimetypes
            deleted_entry: Dict[str, Any] = {
                "path": _norm(str(resolved)), "status": "deleted",
                "is_directory": is_dir,
                "permissions": perms,
                "size_bytes": sz,
            }
            if not is_dir:
                mime, _ = mimetypes.guess_type(str(resolved))
                deleted_entry["file_type"] = mime or "application/octet-stream"
            return deleted_entry
        except Exception as e:
            return {"path": _norm(str(resolved)), "status": "error", "error": str(e)}

class DiskMover:
    """Pure filesystem mover — no VCS."""

    def move(self, params: Dict[str, Any]) -> Dict[str, Any]:
        operations = params.get("operations", [])
        create_parents = params.get("create_dest_parents", True)
        overwrite = params.get("overwrite", False)
        dry_run = params.get("dry_run", False)

        if not operations:
            return {"error": "operations parameter is required", "status_code": 400}

        results = []
        successful = 0
        failed = 0

        for op in operations:
            src = op.get("source", "")
            dst = op.get("destination", "")
            if not src or not dst:
                results.append({"source": src, "destination": dst, "status": "error", "error": "Both source and destination required"})
                failed += 1
                continue
            result = self._move_one(src, dst, create_parents, overwrite, dry_run)
            if result.get("status") == "moved":
                successful += 1
            else:
                failed += 1
            results.append(result)

        status_code = 200 if failed == 0 else 400
        return {
            "success": failed == 0,
            "status_code": status_code,
            "message": f"Moved {successful} items" if not failed else f"{successful} moved, {failed} failed",
            "data": {
                "total_requests": len(operations),
                "successful": successful,
                "failed": failed,
                "results": results,
            },
            "meta": {
                "request_id": f"req_mov_{os.urandom(4).hex()}",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        }

    def _move_one(self, src: str, dst: str, create_parents: bool, overwrite: bool, dry_run: bool) -> Dict[str, Any]:
        src_path = Path(src).resolve()
        dst_path = Path(dst).resolve()

        if not src_path.exists():
            return {"source": _norm(str(src_path)), "destination": _norm(str(dst_path)), "status": "error", "error": "Source not found"}

        if dst_path.exists() and not overwrite:
            return {"source": _norm(str(src_path)), "destination": _norm(str(dst_path)), "status": "error", "error": "Destination exists — use overwrite=True"}

        import mimetypes
        dry_entry: Dict[str, Any] = {
            "source": _norm(str(src_path)), "destination": _norm(str(dst_path)), "status": "dry_run", "message": "Would move",
            "is_directory": src_path.is_dir(),
        }
        try:
            dry_entry["source_size_bytes"] = src_path.stat().st_size if not src_path.is_dir() else None
            if not src_path.is_dir():
                mime, _ = mimetypes.guess_type(str(src_path))
                dry_entry["source_file_type"] = mime or "application/octet-stream"
        except OSError:
            pass
        return dry_entry

        try:
            if create_parents:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            moved_entry: Dict[str, Any] = {
                "source": _norm(str(src_path)), "destination": _norm(str(dst_path)), "status": "moved",
                "is_directory": src_path.is_dir(),
            }
            try:
                moved_entry["source_size_bytes"] = src_path.stat().st_size if not src_path.is_dir() else None
                if not src_path.is_dir():
                    mime, _ = mimetypes.guess_type(str(src_path))
                    moved_entry["source_file_type"] = mime or "application/octet-stream"
            except OSError:
                pass
            return moved_entry
        except Exception as e:
            return {"source": _norm(str(src_path)), "destination": _norm(str(dst_path)), "status": "error", "error": str(e)}
