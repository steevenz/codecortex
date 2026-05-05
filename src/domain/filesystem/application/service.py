# project   CodeCortex
# package   Domain/Filesystem
# author    Steeven Andrian
# copyright (c) 2026 Aegis Codework
# standard  Aegis-CrossStack-v1.0
# stack     Python
# Class FilesystemService - Manage DB-backed filesystem operations and destructive actions.

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from src.core.database import DatabaseManager
from src.core.logging_config import get_logger

logger = get_logger("CodeCortex.Domain.Filesystem")

from src.domain.coderepository.infrastructure.git_adapter import GitAdapter
from src.domain.coderepository.core.store import ICodeRepositoryStore

class FilesystemService:
    def __init__(self, db: DatabaseManager, repo_store: ICodeRepositoryStore):
        self.db = db
        self.repo_store = repo_store
        self._git_adapters: Dict[str, GitAdapter] = {}

    def _get_git_adapter(self, repo_id: str, repo_root: Path) -> GitAdapter:
        if repo_id not in self._git_adapters:
            self._git_adapters[repo_id] = GitAdapter(repo_root)
            # Ensure author config
            self._ensure_git_author(repo_id, self._git_adapters[repo_id])
        return self._git_adapters[repo_id]

    def _ensure_git_author(self, repo_id: str, adapter: GitAdapter):
        """Ensure git local config has user.name and user.email from repo metadata."""
        if not adapter.is_available:
            return

        row = self.db.conn.execute(
            "SELECT author_name, author_email FROM repositories WHERE id = ?", (repo_id,)
        ).fetchone()
        
        if row and row["author_name"]:
            adapter.set_config("user", "name", row["author_name"])
        if row and row["author_email"]:
            adapter.set_config("user", "email", row["author_email"])

    def _log_event(self, level: str, event_code: str, context: Dict):
        msg = f"[{event_code}] {json.dumps(context)}"
        if level == "ERROR":
            logger.error(msg)
        else:
            logger.info(msg)

    def get_codebase_tree(self, repo_id: str) -> Dict[str, Any]:
        """Generate a hierarchical tree from database entries."""
        try:
            # 1. Get Directories
            dirs = self.db.conn.execute(
                "SELECT id, relative_path, parent_id FROM directories WHERE repository_id = ? ORDER BY relative_path",
                (repo_id,)
            ).fetchall()

            # 2. Get Files
            files = self.db.conn.execute(
                "SELECT id, directory_id, name, classification, size_bytes FROM files WHERE repository_id = ? AND is_deleted = 0",
                (repo_id,)
            ).fetchall()

            # 3. Build Tree Structure
            tree = {"name": "root", "type": "directory", "children": []}
            id_map = {None: tree}

            # Map directories
            for d in dirs:
                node = {
                    "id": d["id"],
                    "name": Path(d["relative_path"]).name if d["relative_path"] else "root",
                    "path": d["relative_path"],
                    "type": "directory",
                    "children": []
                }
                id_map[d["id"]] = node
                if d["relative_path"] == "": # Root directory record
                    id_map[None] = node
                    tree = node

            # Link directories to parents
            for d in dirs:
                if d["parent_id"] in id_map:
                    id_map[d["parent_id"]]["children"].append(id_map[d["id"]])

            # Add files to directories
            for f in files:
                node = {
                    "id": f["id"],
                    "name": f["name"],
                    "type": "file",
                    "classification": f["classification"],
                    "size": f["size_bytes"]
                }
                if f["directory_id"] in id_map:
                    id_map[f["directory_id"]]["children"].append(node)

            return tree
        except Exception as e:
            self._log_event("ERROR", "GET_TREE_FAILED", {"repo_id": repo_id, "error": str(e)})
            return {"error": str(e)}

    def read_file(self, file_path_or_id: str, repo_id: Optional[str] = None) -> Dict[str, Any]:
        """Read file content from database."""
        try:
            if repo_id:
                # If path is relative
                rel_path = file_path_or_id.replace("\\", "/").strip("/")
                dir_path = str(Path(rel_path).parent).replace("\\", "/").strip("/")
                if dir_path == ".": dir_path = ""
                file_name = Path(rel_path).name

                query = """
                    SELECT f.*, d.relative_path AS dir_path 
                    FROM files f
                    JOIN directories d ON d.id = f.directory_id
                    WHERE f.repository_id = ? AND d.relative_path = ? AND f.name = ? AND f.is_deleted = 0
                """
                params = (repo_id, dir_path, file_name)
            else:
                # Assume UUID
                query = "SELECT * FROM files WHERE id = ? AND is_deleted = 0"
                params = (file_path_or_id,)

            row = self.db.conn.execute(query, params).fetchone()
            if not row:
                return {"error": "file_not_found"}

            return {
                "id": row["id"],
                "name": row["name"],
                "content": row["content"],
                "classification": row["classification"],
                "size": row["size_bytes"],
                "hash": row["content_hash"],
                "last_modified": row["mtime"]
            }
        except Exception as e:
            self._log_event("ERROR", "READ_FILE_FAILED", {"input": file_path_or_id, "error": str(e)})
            return {"error": str(e)}

    def delete_file(self, file_path_or_id: str, repo_id: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
        """Soft-delete file from DB and physically from disk (if not dry_run)."""
        try:
            # 1. Resolve File
            file_data = self.read_file(file_path_or_id, repo_id)
            if "error" in file_data:
                return file_data

            # 2. Get Repository Root
            cursor = self.db.conn.execute(
                "SELECT root_path FROM repositories WHERE id = (SELECT repository_id FROM files WHERE id = ?)",
                (file_data["id"],)
            )
            repo_root = Path(cursor.fetchone()["root_path"])
            
            # Resolve physical path
            cursor = self.db.conn.execute(
                "SELECT d.relative_path FROM directories d JOIN files f ON f.directory_id = d.id WHERE f.id = ?",
                (file_data["id"],)
            )
            rel_dir = cursor.fetchone()["relative_path"]
            abs_path = repo_root / rel_dir / file_data["name"]

            if dry_run:
                return {
                    "status": "dry_run",
                    "action": "delete",
                    "file": file_data["name"],
                    "path": str(abs_path),
                    "message": "File would be deleted from disk and database."
                }

            # 3. Execution
            if abs_path.exists():
                os.remove(abs_path)
            
            with self.db.transaction() as txn:
                txn.execute("UPDATE files SET is_deleted = 1 WHERE id = ?", (file_data["id"],))
                # Update manifest as well? Or just let sync handle it.
                # Soft delete is enough for now.

            # 4. Git Integration
            adapter = self._get_git_adapter(file_data.get("repository_id", repo_id), repo_root)
            if adapter.is_available:
                adapter.add([str(abs_path.relative_to(repo_root))])
                adapter.commit(f"chore: delete {file_data['name']}")

            return {"status": "success", "file": file_data["name"], "path": str(abs_path)}
        except Exception as e:
            self._log_event("ERROR", "DELETE_FILE_FAILED", {"input": file_path_or_id, "error": str(e)})
            return {"error": str(e)}

    def write_file(self, path: str, content: str, repo_id: str, dry_run: bool = True) -> Dict[str, Any]:
        """Write file to disk and update database."""
        try:
            # 1. Resolve Paths
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            repo_root = Path(cursor.fetchone()["root_path"])
            abs_path = (repo_root / path).resolve()

            if not str(abs_path).startswith(str(repo_root.resolve())):
                return {"error": "path_traversal_blocked"}

            # 2. Dry Run / Diff
            old_content = ""
            if abs_path.exists():
                old_content = abs_path.read_text(encoding="utf-8", errors="ignore")

            if dry_run:
                return {
                    "status": "dry_run",
                    "action": "write",
                    "path": path,
                    "changes": f"Writing {len(content)} bytes. (Old: {len(old_content)} bytes)"
                }

            # 3. Physical Write
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")

            # 4. Update Database
            from src.domain.coderepository.infrastructure.file_reader import FileReader
            import hashlib

            reader = FileReader(repo_root)
            file_hash = reader.calculate_hash(path)
            
            stat = abs_path.stat()
            size_bytes = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)
            mtime_epoch = float(stat.st_mtime)

            # Ensure directory exists in DB
            dir_id = self.repo_store.ensure_directory_chain(repo_id, str(Path(path).parent))

            self.repo_store.upsert_file_and_manifest(
                {
                    "id": str(uuid.uuid4()),
                    "repository_id": repo_id,
                    "directory_id": dir_id,
                    "name": abs_path.name,
                    "classification": "code",
                    "size_bytes": size_bytes,
                    "content": content,
                    "content_hash": file_hash,
                    "mtime": mtime
                },
                {
                    "id": str(uuid.uuid4()),
                    "repository_id": repo_id,
                    "file_path": path,
                    "last_hash": file_hash,
                    "last_size_bytes": int(size_bytes),
                    "last_mtime": mtime_epoch
                }
            )
            
            # 5. Git Integration
            adapter = self._get_git_adapter(repo_id, repo_root)
            if adapter.is_available:
                adapter.add([path])
                adapter.commit(f"chore: update {path}")

            return {"status": "success", "path": path, "size": len(content)}
        except Exception as e:
            logger.exception(f"Failed to write file {path}")
            return {"error": str(e)}

    def move_file(self, source_path: str, dest_path: str, repo_id: str, dry_run: bool = True) -> Dict[str, Any]:
        """Move file or directory and update database."""
        try:
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            repo_root = Path(cursor.fetchone()["root_path"])
            abs_src = (repo_root / source_path).resolve()
            abs_dst = (repo_root / dest_path).resolve()

            if not str(abs_src).startswith(str(repo_root)) or not str(abs_dst).startswith(str(repo_root)):
                return {"error": "path_traversal_blocked"}

            if not abs_src.exists():
                return {"error": "source_not_found"}

            if dry_run:
                return {
                    "status": "dry_run",
                    "action": "move",
                    "source": source_path,
                    "destination": dest_path
                }

            # Execution
            import shutil
            abs_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(abs_src), str(abs_dst))

            # Trigger re-indexing for both paths
            from src.domain.coderepository.application.service import CodeRepositoryService
            repo_svc = CodeRepositoryService(self.repo_store)
            import asyncio
            asyncio.run(repo_svc.sync_repository_paths(str(repo_root), [source_path, dest_path]))

            # 5. Git Integration
            adapter = self._get_git_adapter(repo_id, repo_root)
            if adapter.is_available:
                adapter.add([source_path, dest_path])
                adapter.commit(f"chore: move {source_path} to {dest_path}")

            return {"status": "success", "source": source_path, "destination": dest_path}
        except Exception as e:
            self._log_event("ERROR", "MOVE_FILE_FAILED", {"src": source_path, "dst": dest_path, "error": str(e)})
            return {"error": str(e)}

    def copy_file(self, source_path: str, dest_path: str, repo_id: str, dry_run: bool = True) -> Dict[str, Any]:
        """Copy file or directory and update database."""
        try:
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            repo_root = Path(cursor.fetchone()["root_path"])
            abs_src = (repo_root / source_path).resolve()
            abs_dst = (repo_root / dest_path).resolve()

            if not str(abs_src).startswith(str(repo_root)) or not str(abs_dst).startswith(str(repo_root)):
                return {"error": "path_traversal_blocked"}

            if not abs_src.exists():
                return {"error": "source_not_found"}

            if dry_run:
                return {
                    "status": "dry_run",
                    "action": "copy",
                    "source": source_path,
                    "destination": dest_path
                }

            # Execution
            import shutil
            abs_dst.parent.mkdir(parents=True, exist_ok=True)
            if abs_src.is_dir():
                shutil.copytree(str(abs_src), str(abs_dst))
            else:
                shutil.copy2(str(abs_src), str(abs_dst))

            # Trigger re-indexing for dest path
            from src.domain.coderepository.application.service import CodeRepositoryService
            repo_svc = CodeRepositoryService(self.repo_store)
            import asyncio
            asyncio.run(repo_svc.sync_repository_paths(str(repo_root), [dest_path]))

            # 5. Git Integration
            adapter = self._get_git_adapter(repo_id, repo_root)
            if adapter.is_available:
                adapter.add([dest_path])
                adapter.commit(f"chore: copy {source_path} to {dest_path}")

            return {"status": "success", "source": source_path, "destination": dest_path}
        except Exception as e:
            self._log_event("ERROR", "COPY_FILE_FAILED", {"src": source_path, "dst": dest_path, "error": str(e)})
            return {"error": str(e)}

    def list_files_glob(self, pattern: str, repo_id: str) -> Dict[str, Any]:
        """List files matching a glob pattern."""
        try:
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            repo_root = Path(cursor.fetchone()["root_path"])
            
            matches = []
            for p in repo_root.glob(pattern):
                if p.is_file():
                    matches.append(str(p.relative_to(repo_root)).replace("\\", "/"))
            
            return {"matches": matches, "count": len(matches)}
        except Exception as e:
            self._log_event("ERROR", "GLOB_FAILED", {"pattern": pattern, "error": str(e)})
            return {"error": str(e)}
