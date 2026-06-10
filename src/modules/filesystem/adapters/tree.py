"""
DiskTree — database-backed directory tree with disk fallback.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Tree
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core import ApiError

class DiskTree:
    """Directory tree generator with DB-backed integrity cache.

    Serve strategy:
    1. DB cache exists + tree synced → serve from DB (instant)
    2. Else → build from disk and auto-cache
    """

    @staticmethod
    def get_tree(
        params: Dict[str, Any],
        db=None,
        repo_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = params.get("path")
        if not path:
            raise ApiError("path is required", status_code=400, error_code="FS_004")

        base_path = Path(path).resolve()
        if not base_path.exists():
            raise ApiError(f"Path not found: {path}", status_code=404, error_code="FS_004")

        max_depth = params.get("max_depth")
        include_hidden = params.get("include_hidden", False)

        if db is not None and repo_id:
            from src.core.database.integrity import FileIntegrity
            fi = FileIntegrity(db)

            if fi.is_synced(repo_id, "tree"):
                tree = fi.get_tree(repo_id, parent_path=str(base_path), max_depth=max_depth or 10)
                if tree.get("cached") and tree.get("children"):
                    tree["source"] = "database"
                    state = fi.get_sync_state(repo_id)
                    tree["synced_at"] = state.get("sync_at")
                    return {
                        "status_code": 200,
                        "message": "Tree retrieved from cache",
                        "data": tree,
                    }

        tree = DiskTree._build_tree(base_path, max_depth, include_hidden)
        tree["source"] = "disk"

        if db is not None and repo_id:
            try:
                from src.core.database.integrity import FileIntegrity
                fi = FileIntegrity(db)
                fi.update_bulk(repo_id, base_path, max_depth=max_depth or 10)
                state = fi.get_sync_state(repo_id)
                tree["synced_at"] = state.get("sync_at")
            except Exception:
                pass

        return {
            "status_code": 200,
            "message": "Tree generated from disk scan",
            "data": tree,
        }

    @staticmethod
    def _build_tree(
        path: Path,
        max_depth: int | None = None,
        include_hidden: bool = False,
        current_depth: int = 0,
    ) -> Dict[str, Any]:
        if max_depth is not None and current_depth > max_depth:
            return {}

        result: Dict[str, Any] = {
            "name": path.name,
            "path": str(path),
            "type": "directory" if path.is_dir() else "file",
        }

        if path.is_dir():
            children: List[Dict[str, Any]] = []
            total_size = 0
            file_count = 0
            dir_count = 0
            try:
                for item in sorted(path.iterdir()):
                    if not include_hidden and item.name.startswith('.'):
                        continue
                    child = DiskTree._build_tree(
                        item, max_depth, include_hidden, current_depth + 1
                    )
                    if child:
                        children.append(child)
                        if child["type"] == "file":
                            try:
                                total_size += item.stat().st_size
                                file_count += 1
                            except OSError:
                                pass
                        else:
                            dir_count += 1
            except PermissionError:
                pass
            result["children"] = children
            result["child_count"] = len(children)
            result["total_size_bytes"] = total_size
            result["file_count"] = file_count
            result["directory_count"] = dir_count
        else:
            try:
                result["size_bytes"] = path.stat().st_size
            except OSError:
                pass

        return result
