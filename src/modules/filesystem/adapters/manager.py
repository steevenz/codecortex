"""
Pure filesystem operations — no VCS logic (use repo_git/repo_svn instead).

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Manager
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

from typing import Any, Dict, Optional

from src.core.errors.errors import ApiError
from .writer import DiskWriter
from .deleter import DiskDeleter, DiskMover
from .chmod import DiskChmod
from .chown import DiskChown
from .symlink import DiskSymlink
from .touch import DiskTouch
from .archiver import DiskArchiver
from .xattr import DiskXattr
from .converter import DiskConverter


class DiskManager:
    """Unified filesystem management — dispatches operations to specialized adapters."""

    def execute(
        self,
        params: Dict[str, Any],
        db=None,
        repo_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        op = params.get("operation", "")
        dry_run = params.get("dry_run", False)

        if op in ("write", "append"):
            write_mode = "append" if op == "append" else ("overwrite" if params.get("overwrite") else "create")
            return DiskWriter().write({
                **params, "write_mode": write_mode, "operation": op, "dry_run": dry_run,
            })

        if op == "write_batch":
            return DiskWriter().write_batch({**params, "dry_run": dry_run})

        if op == "delete":
            return DiskDeleter().delete({**params, "dry_run": dry_run})

        if op in ("move", "rename"):
            return DiskMover().move({**params, "dry_run": dry_run})

        if op == "chmod":
            return DiskChmod().chmod({**params, "dry_run": dry_run})

        if op == "chown":
            return DiskChown().chown({**params, "dry_run": dry_run})

        if op == "symlink":
            return DiskSymlink().symlink({**params, "dry_run": dry_run})

        if op == "touch":
            return DiskTouch().touch({**params, "dry_run": dry_run})

        if op == "archive":
            return DiskArchiver.execute({**params, "dry_run": dry_run})

        if op == "xattr":
            return DiskXattr.execute(params)

        if op == "convert":
            return DiskConverter.convert(params)

        if op == "tree":
            from src.modules.filesystem.adapters.tree import DiskTree
            return DiskTree.get_tree(params, db=db, repo_id=repo_id or params.get("repo_id"))

        if op == "read":
            from src.modules.filesystem.adapters.reader import DiskReader
            params["_db"] = db
            return DiskReader.read_file(params)

        raise ApiError(f"Unknown operation: {op}", status_code=400, error_code="FS_004")
