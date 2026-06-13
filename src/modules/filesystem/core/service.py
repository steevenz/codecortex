"""
Manage DB-backed filesystem operations and destructive actions.

:project: CodeCortex
:package: Modules.Filesystem.Core.Service
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Filesystem-v1.0
"""

import os
import json
import uuid
import asyncio
import stat as stat_module
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from src.core.database import DatabaseManager
from src.core.logging import get_logger

logger = get_logger("CodeCortex.Domain.Filesystem")

try:
    import pwd
    import grp
    HAS_UNIX_MODULES = True
except ImportError:
    pwd = None
    grp = None
    HAS_UNIX_MODULES = False

from src.modules.coderepository.adapters.git.adapter import Git
from src.modules.coderepository.core.store import ICodeRepositoryStore
from src.modules.filesystem.adapters.reader import DiskReader

from src.core.utils.path import norm_path as _norm
from src.core.config.environment import utc_ts_to_iso as _utc_from_ts
from src.core.logging.event_logger import log_event

class Filesystem:
    def __init__(self, db: DatabaseManager, repo_store: ICodeRepositoryStore,
                 graph_service: Optional[Any] = None,
                 index_service: Optional[Any] = None,
                 git_service: Optional[Any] = None,
                 svn_service: Optional[Any] = None,
                 qa_service: Optional[Any] = None):
        self.db = db
        self.repo_store = repo_store
        self.graph_service = graph_service
        self.index_service = index_service
        self.git_service = git_service
        self.svn_service = svn_service
        self.qa_service = qa_service
        self._git_adapters: Dict[str, Git] = {}

    def _get_git_adapter(self, repo_id: str, repo_root: Path) -> Git:
        if repo_id not in self._git_adapters:
            self._git_adapters[repo_id] = Git(repo_root)
            self._ensure_git_author(repo_id, self._git_adapters[repo_id])
        return self._git_adapters[repo_id]

    def _ensure_git_author(self, repo_id: str, adapter: Git):
        if not adapter.is_available:
            return

        row = self.db.conn.execute(
            "SELECT author_name, author_email FROM repositories WHERE id = ?", (repo_id,)
        ).fetchone()

        if row and row["author_name"]:
            adapter.set_config("user", "name", row["author_name"])
        if row and row["author_email"]:
            adapter.set_config("user", "email", row["author_email"])

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: Optional[str] = None):
        log_event(level, event_code, context, request_id=request_id, logger=getattr(self, 'logger', None))

    def _get_owner(self, stat_info) -> str:
        if HAS_UNIX_MODULES:
            try:
                return pwd.getpwuid(stat_info.st_uid).pw_name
            except KeyError:
                pass
        if stat_info.st_uid == 0 and not HAS_UNIX_MODULES:
            return os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
        return str(stat_info.st_uid)

    def _get_group(self, stat_info) -> str:
        if HAS_UNIX_MODULES:
            try:
                return grp.getgrgid(stat_info.st_gid).gr_name
            except KeyError:
                pass
        if stat_info.st_gid == 0 and not HAS_UNIX_MODULES:
            return os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
        return str(stat_info.st_gid)

    def resolve_repo_path(self, repo_id: Optional[str] = None, relative_path: Optional[str] = None) -> str:
        if repo_id:
            cursor = self.db.conn.execute(
                "SELECT root_path FROM repositories WHERE id = ?",
                (repo_id,)
            )
            row = cursor.fetchone()
            if row and row["root_path"]:
                root = Path(row["root_path"])
                return _norm(str(root / relative_path)) if relative_path else _norm(str(root))
        if relative_path:
            return _norm(str(Path(relative_path).resolve()))
        return _norm(str(Path.cwd()))

    def get_codebase_tree(self, repo_id: Optional[str] = None, path: Optional[str] = None, max_depth: int = 6) -> Dict[str, Any]:
        try:
            target_path: Optional[Path] = None
            if repo_id:
                cursor = self.db.conn.execute(
                    "SELECT root_path FROM repositories WHERE id = ?",
                    (repo_id,)
                )
                row = cursor.fetchone()
                if row and row["root_path"]:
                    repo_root = Path(row["root_path"])
                    target_path = repo_root / path if path else repo_root
                else:
                    target_path = Path.cwd()
                    self._log_event("WARN", "REPO_NOT_FOUND_FALLBACK", {"repo_id": repo_id, "using_cwd": str(target_path)})
            else:
                if path:
                    target_path = Path(path).resolve()
                else:
                    target_path = Path.cwd()

            if not target_path.exists():
                return {"success": False, "status_code": 404, "message": f"Directory not found: {target_path}", "data": None}

            if not os.access(target_path, os.R_OK):
                return {"success": False, "status_code": 403, "message": f"Permission denied: cannot read directory {target_path}", "data": None}

            git_root: Optional[Path] = None
            if target_path:
                from src.modules.filesystem.adapters.git import DiskGit as _GH
                git_root = _GH.find_root(target_path)

            def get_file_info(file_path: Path, is_dir: bool = False) -> Dict[str, Any]:
                stat_info = file_path.stat()
                mode = stat_info.st_mode
                perms = stat_module.filemode(mode)
                ctime = getattr(stat_info, "st_birthtime", None)
                if ctime is None:
                    ctime = stat_info.st_ctime

                info = {
                    "name": str(file_path.name),
                    "type": "directory" if is_dir else "file",
                    "path": _norm(str(file_path)),
                    "permissions": str(perms),
                    "mode": int(stat_module.S_IMODE(mode)),
                    "owner": self._get_owner(stat_info),
                    "group": self._get_group(stat_info),
                    "size": int(stat_info.st_size),
                    "created": _utc_from_ts(ctime),
                    "modified": _utc_from_ts(stat_info.st_mtime),
                }

                if not is_dir:
                    info["extension"] = str(file_path.suffix.lower()) if file_path.suffix else ""

                if git_root:
                    try:
                        git_status = _GH.get_file_status(git_root, file_path)
                        if git_status:
                            info["git_status"] = git_status
                    except Exception:
                        pass

                return info

            def build_tree(current_path: Path, max_depth: int = 10, current_depth: int = 0) -> List[Dict[str, Any]]:
                if current_depth >= max_depth:
                    return []

                items = []
                try:
                    entries = sorted(list(current_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
                    for entry in entries:
                        try:
                            info = get_file_info(entry, entry.is_dir())
                            if entry.is_dir():
                                info["children"] = build_tree(entry, max_depth, current_depth + 1)
                            items.append(info)
                        except PermissionError:
                            continue
                except PermissionError:
                    pass
                return items

            tstat = target_path.stat()
            ctime = getattr(tstat, "st_birthtime", None)
            if ctime is None:
                ctime = tstat.st_ctime
            tree_data = {
                "path": _norm(str(target_path)),
                "name": str(target_path.name),
                "type": "directory",
                "permissions": str(stat_module.filemode(tstat.st_mode)),
                "mode": int(stat_module.S_IMODE(tstat.st_mode)),
                "owner": self._get_owner(tstat),
                "group": self._get_group(tstat),
                "size": 4096,
                "created": _utc_from_ts(ctime),
                "modified": _utc_from_ts(tstat.st_mtime),
                "children": build_tree(target_path, max_depth=max_depth)
            }

            return {"success": True, "status_code": 200, "message": "Directory tree successfully retrieved", "data": tree_data}

        except Exception as e:
            self._log_event("ERROR", "GET_TREE_FAILED", {"repo_id": repo_id, "path": path, "error": str(e)})
            return {"success": False, "status_code": 500, "message": f"Error retrieving tree: {str(e)}", "data": None}

    def read_file(self, file_path_or_id: str, repo_id: Optional[str] = None,
                  lines: Optional[Dict[str, int]] = None, args: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Read a file with optional line targeting.

        Args:
            file_path_or_id: File path or ID
            repo_id: Repository ID (optional)
            lines: Optional dict with start_line/end_line for line-specific read
                  Example: {"start_line": 100, "end_line": 121}
            args: Additional args (for backward compatibility)

        Returns:
            Dict with file content and metadata
        """
        if lines:
            start = lines.get("start_line", 1)
            end = lines.get("end_line")
            return self.read_lines(file_path_or_id, start, end, repo_id)

        try:
            if repo_id:
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

    def read_from_disk(self, path: str) -> Dict[str, Any]:
        resolved = Path(path).resolve()
        if ".." in str(resolved):
            return {"error": "Path traversal detected", "status_code": 400}
        if not resolved.exists():
            return {"error": f"Path does not exist: {path}", "status_code": 404}
        try:
            reader = DiskReader()
            result = reader.read(path)
            result = self._enrich_with_domain_services(result, resolved)
            return result
        except Exception as e:
            self._log_event("ERROR", "FS_READ_DISK_FAILED", {"path": path, "error": str(e)})
            return {"error": str(e), "status_code": 500}

    def _enrich_with_domain_services(self, result: Dict[str, Any], resolved: Path) -> Dict[str, Any]:
        if result.get("file_type") != "source_code":
            return result

        if self.graph_service is not None:
            try:
                dead = asyncio.run(self.graph_service.find_dead_code(path=str(resolved.parent), limit=50))
                if dead:
                    file_dead = [d for d in dead if resolved.name in str(d.get("path", ""))]
                    if file_dead:
                        existing = result.get("analysis", {}).get("dead_code", [])
                        for d in file_dead:
                            existing.append({
                                "type": "graph_dead_code",
                                "message": f"Unused symbol: {d.get('name', '?')}",
                                "line": d.get("line_number", 0),
                                "severity": "warning",
                                "source": "codegraph",
                            })
                        result.setdefault("analysis", {})["dead_code"].extend(existing)
            except Exception:
                pass

            try:
                sec = asyncio.run(self.graph_service._audit_security_hygiene(None))
                if sec:
                    file_sec = [s for s in sec if resolved.name in str(s.get("path", ""))]
                    existing = result.get("analysis", {}).get("security_issues", [])
                    existing.extend(file_sec)
                    result.setdefault("analysis", {})["security_issues"] = existing
            except Exception:
                pass

        if self.qa_service is not None:
            try:
                import asyncio
                lint_result = asyncio.run(self.qa_service.run_qa_task(
                    repo_id="cli",
                    tool="flake8",
                    target_path=str(resolved),
                    background=False,
                ))
                if lint_result and "data" in lint_result:
                    result.setdefault("analysis", {}).setdefault("linting_status", {})["external_linter"] = lint_result["data"]
            except Exception:
                pass

        return result

    def delete_file(self, file_path_or_id: str, repo_id: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
        try:
            file_data = self.read_file(file_path_or_id, repo_id)
            if "error" in file_data:
                return file_data

            cursor = self.db.conn.execute(
                "SELECT root_path FROM repositories WHERE id = (SELECT repository_id FROM files WHERE id = ?)",
                (file_data["id"],)
            )
            repo_root = Path(cursor.fetchone()["root_path"])

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

            if abs_path.exists():
                os.remove(abs_path)

            with self.db.transaction() as txn:
                txn.execute("UPDATE files SET is_deleted = 1 WHERE id = ?", (file_data["id"],))

            adapter = self._get_git_adapter(file_data.get("repository_id", repo_id), repo_root)
            if adapter.is_available:
                adapter.add([str(abs_path.relative_to(repo_root))])
                adapter.commit(f"chore: delete {file_data['name']}")

            return {"status": "success", "file": file_data["name"], "path": str(abs_path)}
        except Exception as e:
            self._log_event("ERROR", "DELETE_FILE_FAILED", {"input": file_path_or_id, "error": str(e)})
            return {"error": str(e)}

    def write_file(self, path: str, content: str, repo_id: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
        try:
            if repo_id:
                cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                row = cursor.fetchone()
                if not row or not row["root_path"]:
                    return {"error": "repository_not_found"}
                repo_root = Path(row["root_path"])
                abs_path = (repo_root / path).resolve()
            else:
                abs_path = Path(path).resolve()
                repo_root = None

            if repo_root and not str(abs_path).startswith(str(repo_root.resolve())):
                return {"error": "path_traversal_blocked"}

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

            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")

            if repo_root and repo_id:
                from src.modules.coderepository.adapters.filesystem.file_reader import FileReader
                reader = FileReader(repo_root)
                file_hash = reader.calculate_hash(path)

                stat = abs_path.stat()
                size_bytes = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime)
                mtime_epoch = float(stat.st_mtime)

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
                        "hash": file_hash,
                        "last_size_bytes": int(size_bytes),
                        "mtime": mtime_epoch
                    }
                )

                adapter = self._get_git_adapter(repo_id, repo_root)
                if adapter.is_available:
                    adapter.add([path])
                    adapter.commit(f"chore: update {path}")

            return {"status": "success", "path": str(abs_path), "size": len(content)}
        except Exception as e:
            logger.exception(f"Failed to write file {path}")
            return {"error": str(e)}

    def move_file(self, source_path: str, dest_path: str, repo_id: str, dry_run: bool = True) -> Dict[str, Any]:
        try:
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            row = cursor.fetchone()
            if not row or not row["root_path"]:
                return {"error": "repository_not_found"}
            repo_root = Path(row["root_path"])
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
                    "destination": dest_path,
                    "message": f"Would move {source_path} to {dest_path}"
                }

            abs_dst.parent.mkdir(parents=True, exist_ok=True)
            abs_src.rename(abs_dst)

            with self.db.transaction() as txn:
                txn.execute("UPDATE files SET relative_path = ? WHERE repository_id = ? AND relative_path = ?",
                           (dest_path, repo_id, source_path))

            adapter = self._get_git_adapter(repo_id, repo_root)
            if adapter.is_available:
                adapter.add([dest_path])
                adapter.commit(f"chore: move {source_path} to {dest_path}")

            return {"status": "success", "source": source_path, "destination": dest_path}
        except Exception as e:
            self._log_event("ERROR", "MOVE_FILE_FAILED", {"source": source_path, "error": str(e)})
            return {"error": str(e)}

    def list_files_glob(self, pattern: str, repo_id: str) -> Dict[str, Any]:
        try:
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            row = cursor.fetchone()
            if not row or not row["root_path"]:
                return {"error": "repository_not_found"}

            repo_root = Path(row["root_path"])
            matches = [str(p.relative_to(repo_root)) for p in repo_root.rglob(pattern) if p.is_file()]
            return {"matches": matches, "count": len(matches)}
        except Exception as e:
            self._log_event("ERROR", "GLOB_FAILED", {"pattern": pattern, "error": str(e)})
            return {"error": str(e)}

    def create_directory(self, path: str, repo_id: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
        try:
            if repo_id:
                cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                row = cursor.fetchone()
                if not row or not row["root_path"]:
                    return {"error": "repository_not_found"}
                abs_path = Path(row["root_path"]) / path
            else:
                abs_path = Path(path).resolve()

            if dry_run:
                return {"status": "dry_run", "action": "mkdir", "path": str(abs_path)}

            abs_path.mkdir(parents=True, exist_ok=True)
            return {"status": "success", "path": str(abs_path), "action": "mkdir"}
        except Exception as e:
            self._log_event("ERROR", "MKDIR_FAILED", {"path": path, "error": str(e)})
            return {"error": str(e)}

    def list_directory(self, path: str, repo_id: Optional[str] = None, recursive: bool = False,
                       max_depth: Optional[int] = None, include_hidden: bool = False) -> Dict[str, Any]:
        try:
            if repo_id:
                cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                row = cursor.fetchone()
                target = Path(row["root_path"]) / path if row and row["root_path"] else Path(path)
            else:
                target = Path(path).resolve()

            if not target.exists():
                return {"error": "path_not_found", "path": str(target)}

            entries = []
            if recursive:
                for root, dirs, files in os.walk(target):
                    depth = Path(root).relative_to(target).parts.__len__()
                    if max_depth and depth > max_depth:
                        continue
                    for name in dirs + files:
                        if not include_hidden and name.startswith("."):
                            continue
                        fp = Path(root) / name
                        entries.append({
                            "name": name,
                            "path": str(fp.relative_to(target)),
                            "is_dir": fp.is_dir(),
                            "size": fp.stat().st_size if fp.is_file() else 0,
                        })
            else:
                for entry in target.iterdir():
                    if not include_hidden and entry.name.startswith("."):
                        continue
                    entries.append({
                        "name": entry.name,
                        "path": str(entry.relative_to(target)) if repo_id else str(entry),
                        "is_dir": entry.is_dir(),
                        "size": entry.stat().st_size if entry.is_file() else 0,
                    })

            return {"entries": entries, "count": len(entries), "path": str(target)}
        except Exception as e:
            self._log_event("ERROR", "LIST_DIR_FAILED", {"path": path, "error": str(e)})
            return {"error": str(e)}

    def search_files(self, path: str, pattern: str = "*", repo_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            if repo_id:
                cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                row = cursor.fetchone()
                target = Path(row["root_path"]) / path if row and row["root_path"] else Path(path)
            else:
                target = Path(path).resolve()

            matches = list(target.rglob(pattern))
            return {"matches": [str(m) for m in matches], "count": len(matches)}
        except Exception as e:
            self._log_event("ERROR", "SEARCH_FILES_FAILED", {"path": path, "error": str(e)})
            return {"error": str(e)}

    def watch_directory(self, path: str, repo_id: Optional[str] = None, events: Optional[list] = None,
                        poll_interval: int = 1, max_events: int = 100) -> Dict[str, Any]:
        try:
            if repo_id:
                cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                row = cursor.fetchone()
                target = Path(row["root_path"]) / path if row and row["root_path"] else Path(path)
            else:
                target = Path(path).resolve()

            return {"status": "watching", "path": str(target), "events": events or ["create", "modify", "delete"]}
        except Exception as e:
            self._log_event("ERROR", "WATCH_FAILED", {"path": path, "error": str(e)})
            return {"error": str(e)}

    def get_disk_usage(self, path: str, repo_id: Optional[str] = None, recursive: bool = True,
                       unit: str = "auto", max_items: int = 100) -> Dict[str, Any]:
        try:
            if repo_id:
                cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                row = cursor.fetchone()
                target = Path(row["root_path"]) / path if row and row["root_path"] else Path(path)
            else:
                target = Path(path).resolve()

            total_size = 0
            file_count = 0
            for root, dirs, files in os.walk(target):
                for f in files:
                    fp = Path(root) / f
                    try:
                        total_size += fp.stat().st_size
                        file_count += 1
                    except OSError:
                        pass

            return {"path": str(target), "total_size_bytes": total_size, "file_count": file_count}
        except Exception as e:
            self._log_event("ERROR", "DISK_USAGE_FAILED", {"path": path, "error": str(e)})
            return {"error": str(e)}

    def audit_filesystem(self, path: str, repo_id: Optional[str] = None, check_permissions: bool = True,
                         max_file_size_mb: int = 100, limit: int = 200) -> Dict[str, Any]:
        try:
            if repo_id:
                cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                row = cursor.fetchone()
                target = Path(row["root_path"]) / path if row and row["root_path"] else Path(path)
            else:
                target = Path(path).resolve()

            findings = []
            for root, dirs, files in os.walk(target):
                for f in files[:limit]:
                    fp = Path(root) / f
                    findings.append({"path": str(fp), "size": fp.stat().st_size})

            return {"findings": findings, "count": len(findings), "path": str(target)}
        except Exception as e:
            self._log_event("ERROR", "FS_AUDIT_FAILED", {"path": path, "error": str(e)})
            return {"error": str(e)}

    def copy_file(self, source_path: str, dest_path: str, repo_id: str, dry_run: bool = True) -> Dict[str, Any]:
        try:
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            row = cursor.fetchone()
            if not row or not row["root_path"]:
                return {"error": "repository_not_found"}
            repo_root = Path(row["root_path"])
            abs_src = (repo_root / source_path).resolve()
            abs_dst = (repo_root / dest_path).resolve()

            if not str(abs_src).startswith(str(repo_root)) or not str(abs_dst).startswith(str(repo_root)):
                return {"error": "path_traversal_blocked"}

            if not abs_src.exists():
                return {"error": "source_not_found"}

            if dry_run:
                return {"status": "dry_run", "action": "copy", "source": source_path, "destination": dest_path}

            abs_dst.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(abs_src, abs_dst)

            return {"status": "success", "source": source_path, "destination": dest_path}
        except Exception as e:
            self._log_event("ERROR", "COPY_FILE_FAILED", {"source": source_path, "error": str(e)})
            return {"error": str(e)}

    def read_lines(self, path: str, start_line: int = 1, end_line: Optional[int] = None,
                   repo_id: Optional[str] = None, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Read specific lines from a file.

        Args:
            path: File path (relative to repo if repo_id provided)
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (inclusive, default: all lines from start)
            repo_id: Repository ID (optional)
            encoding: File encoding (default: utf-8)

        Returns:
            Dict with lines content and metadata
        """
        try:
            if repo_id:
                cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                row = cursor.fetchone()
                if not row or not row["root_path"]:
                    return {"error": "repository_not_found"}
                abs_path = Path(row["root_path"]) / path
            else:
                abs_path = Path(path).resolve()

            if not abs_path.exists():
                return {"error": "file_not_found", "path": str(abs_path)}

            with open(abs_path, 'r', encoding=encoding) as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)
            start_idx = max(0, start_line - 1)
            end_idx = end_line if end_line is None else min(total_lines, end_line)

            selected_lines = all_lines[start_idx:end_idx]
            lines_data = [{"line_number": i + start_line, "content": line.rstrip('\n\r')}
                         for i, line in enumerate(selected_lines)]

            return {
                "path": str(abs_path),
                "start_line": start_line,
                "end_line": end_idx if end_line else total_lines,
                "total_lines": total_lines,
                "lines": lines_data,
                "count": len(lines_data)
            }
        except Exception as e:
            self._log_event("ERROR", "READ_LINES_FAILED", {"path": path, "error": str(e)})
            return {"error": str(e)}

    def write_lines(self, path: str, start_line: int, end_line: Optional[int],
                    content: List[str], repo_id: Optional[str] = None,
                    encoding: str = "utf-8", dry_run: bool = True) -> Dict[str, Any]:
        """
        Write/edit specific lines in a file.

        Args:
            path: File path (relative to repo if repo_id provided)
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (inclusive, default: replace from start_line to end)
            content: List of new lines to insert/replace
            repo_id: Repository ID (optional)
            encoding: File encoding (default: utf-8)
            dry_run: If True, return what would change without modifying

        Returns:
            Dict with operation result and metadata
        """
        try:
            if repo_id:
                cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                row = cursor.fetchone()
                if not row or not row["root_path"]:
                    return {"error": "repository_not_found"}
                abs_path = Path(row["root_path"]) / path
            else:
                abs_path = Path(path).resolve()

            if not abs_path.exists():
                return {"error": "file_not_found", "path": str(abs_path)}

            with open(abs_path, 'r', encoding=encoding) as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)
            start_idx = max(0, start_line - 1)
            end_idx = total_lines if end_line is None else min(total_lines, end_line)

            if dry_run:
                return {
                    "status": "dry_run",
                    "path": str(abs_path),
                    "action": "write_lines",
                    "start_line": start_line,
                    "end_line": end_idx if end_line is None else end_line,
                    "new_lines_count": len(content),
                    "old_lines_count": end_idx - start_idx
                }

            new_content = all_lines[:start_idx] + [line if not line.endswith('\n') else line for line in content]
            if not (content and content[-1].endswith('\n')):
                new_content[-1] = new_content[-1] + '\n' if isinstance(new_content[-1], str) else new_content[-1]
            new_content.extend(all_lines[end_idx:])

            abs_path.write_text(''.join(new_content), encoding=encoding)

            return {
                "status": "success",
                "path": str(abs_path),
                "action": "write_lines",
                "start_line": start_line,
                "end_line": end_idx if end_line is None else end_line,
                "lines_changed": len(content)
            }
        except Exception as e:
            self._log_event("ERROR", "WRITE_LINES_FAILED", {"path": path, "error": str(e)})
            return {"error": str(e)}
