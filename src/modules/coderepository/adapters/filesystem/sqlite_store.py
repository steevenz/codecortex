"""
Class SQLiteCodeRepositoryStore - Implementation of ICodeRepositoryStore using SQLite.

:project: CodeCortex
:package: Modules.Coderepository.Adapters.Filesystem.Sqlite_store
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""

import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any
from src.core.database import DatabaseManager
from src.modules.coderepository.core.store import ICodeRepositoryStore

class SQLiteCodeRepositoryStore(ICodeRepositoryStore):
    def __init__(self, db: DatabaseManager):
        self.db = db

    def transaction(self):
        return self.db.transaction()

    def get_repository(self, repo_id: str) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM repositories WHERE id = ?", (repo_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_repository_by_path(self, root_path: str) -> Optional[Dict[str, Any]]:
        normalized = str(Path(root_path).resolve())
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM repositories WHERE root_path = ? COLLATE NOCASE", (normalized,)
            ).fetchone()
            return dict(row) if row else None

    def get_repository_by_remote_url(self, remote_url: str) -> Optional[Dict[str, Any]]:
        if not remote_url:
            return None
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM repositories WHERE vcs_url = ? AND vcs_url IS NOT NULL AND vcs_url != ''",
                (remote_url,),
            ).fetchone()
            return dict(row) if row else None

    def list_repositories(self) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM repositories").fetchall()
            return [dict(row) for row in rows]

    def upsert_repository(self, name: str, root_path: str, repo_id: Optional[str] = None,
                          vcs_metadata: Optional[Dict[str, Any]] = None,
                          remote_url: Optional[str] = None) -> str:
        normalized = str(Path(root_path).resolve())
        url: Optional[str] = None
        existing = self.get_repository_by_path(normalized)
        if existing:
            with self.db.transaction() as txn:
                txn.execute(
                    "UPDATE repositories SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (name, existing["id"]),
                )
            url = remote_url or ((vcs_metadata or {}).get("vcs_url") if vcs_metadata else None)
            if url:
                self.update_vcs_metadata(existing["id"], {"vcs_url": url})
            if vcs_metadata:
                self.update_vcs_metadata(existing["id"], vcs_metadata)
            return existing["id"]

        # Monorepo detection: path inside existing repo with no .git/.svn = subdir
        all_repos = self.list_repositories()
        for r in all_repos:
            parent = Path(r["root_path"]).resolve()
            try:
                Path(normalized).relative_to(parent)
                has_own_vcs = (
                    (Path(normalized) / ".git").is_dir()
                    or (Path(normalized) / ".svn").is_dir()
                )
                if not has_own_vcs:
                    return r["id"]
            except ValueError:
                pass
        if url:
            matched = self.get_repository_by_remote_url(url)
            if matched:
                if vcs_metadata:
                    self.update_vcs_metadata(matched["id"], vcs_metadata)
                return matched["id"]

        new_repo_id = str(uuid.uuid4())
        vcs_type = (vcs_metadata or {}).get("vcs_type") or "git"
        with self.db.transaction() as txn:
            txn.execute(
                "INSERT INTO repositories (id, name, root_path, vcs_type, vcs_url, total_files, total_symbols, total_edges, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (new_repo_id, name, root_path, vcs_type, url)
            )
        if vcs_metadata:
            self.update_vcs_metadata(new_repo_id, vcs_metadata)
        return new_repo_id

    def update_vcs_metadata(self, repo_id: str, meta: Dict[str, Any]) -> None:
        """Update VCS metadata columns for a repository."""
        fields = []
        params = []
        for key in ("vcs_type", "vcs_url", "index_version", "current_branch",
                     "last_commit_hash", "last_commit_time", "current_revision",
                     "last_changed_rev"):
            if key in meta and meta[key] is not None:
                fields.append(f"{key} = ?")
                params.append(meta[key])
        if not fields:
            return
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(repo_id)
        with self.db.transaction() as txn:
            txn.execute(
                f"UPDATE repositories SET {', '.join(fields)} WHERE id = ?",
                params
            )

    def update_indexing_time(self, repo_id: str):
        with self.db.transaction() as txn:
            txn.execute(
                "UPDATE repositories SET sync_at = CURRENT_TIMESTAMP WHERE id = ?",
                (repo_id,)
            )

    def get_directory_id(self, repo_id: str, relative_path: str) -> Optional[str]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM directories WHERE repository_id = ? AND relative_path = ?",
                (repo_id, relative_path)
            ).fetchone()
            return row["id"] if row else None

    def ensure_directory_chain(self, repo_id: str, relative_path: str) -> str:
        """Recursive directory creation in DB."""
        rel_path = relative_path.replace("\\", "/").strip("/")

        # Check cache/db first
        existing = self.get_directory_id(repo_id, rel_path)
        if existing:
            return existing

        # Ensure parent
        parent_id = None
        if "/" in rel_path:
            parent_path = "/".join(rel_path.split("/")[:-1])
            parent_id = self.ensure_directory_chain(repo_id, parent_path)
        elif rel_path != "":
            # Root is parent
            parent_id = self.ensure_directory_chain(repo_id, "")

        new_id = str(uuid.uuid4())
        with self.db.transaction() as txn:
            txn.execute("""
                INSERT INTO directories (id, repository_id, parent_id, relative_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(repository_id, relative_path) DO NOTHING
            """, (new_id, repo_id, parent_id, rel_path))

            # Re-fetch in case of race condition / conflict
            row = txn.execute(
                "SELECT id FROM directories WHERE repository_id = ? AND relative_path = ?",
                (repo_id, rel_path)
            ).fetchone()
            return row["id"]

    def list_files(self, repo_id: str, directory_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            if directory_id:
                rows = conn.execute(
                    "SELECT * FROM files WHERE repository_id = ? AND directory_id = ? AND is_deleted = 0",
                    (repo_id, directory_id)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM files WHERE repository_id = ? AND is_deleted = 0",
                    (repo_id,)
                ).fetchall()
            return [dict(row) for row in rows]

    def get_manifest_entry(self, repo_id: str, file_path: str) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT hash, last_size_bytes, mtime FROM manifest_entries WHERE repository_id = ? AND file_path = ?",
                (repo_id, file_path)
            ).fetchone()
            return dict(row) if row else None

    def upsert_file_and_manifest(self, file_data: Dict[str, Any], manifest_data: Dict[str, Any]):
        with self.db.transaction() as txn:
            txn.execute("""
                INSERT INTO files (id, repository_id, directory_id, name, relative_path, classification, size_bytes, content, content_hash, mtime, is_deleted, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(repository_id, directory_id, name) DO UPDATE SET
                    relative_path = EXCLUDED.relative_path,
                    classification = EXCLUDED.classification,
                    size_bytes = EXCLUDED.size_bytes,
                    content = EXCLUDED.content,
                    content_hash = EXCLUDED.content_hash,
                    mtime = EXCLUDED.mtime,
                    updated_at = CURRENT_TIMESTAMP,
                    is_deleted = 0
            """, (
                file_data["id"], file_data["repository_id"], file_data["directory_id"],
                file_data["name"], file_data["relative_path"], file_data["classification"], file_data["size_bytes"],
                file_data["content"], file_data["content_hash"], file_data["mtime"]
            ))

            txn.execute("""
                INSERT INTO manifest_entries (id, repository_id, file_path, hash, last_size_bytes, mtime, last_processed_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(repository_id, file_path) DO UPDATE SET
                    hash = EXCLUDED.hash,
                    last_size_bytes = EXCLUDED.last_size_bytes,
                    mtime = EXCLUDED.mtime,
                    last_processed_at = CURRENT_TIMESTAMP
            """, (
                manifest_data["id"], manifest_data["repository_id"], manifest_data["file_path"],
                manifest_data["hash"], manifest_data["last_size_bytes"], manifest_data["mtime"]
            ))

    def upsert_commit(self, commit_data: Dict[str, Any]):
        with self.db.transaction() as txn:
            txn.execute("""
                INSERT INTO commits (
                    id, repository_id, commit_hash, author_name, author_email,
                    committed_at, message, parent_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repository_id, commit_hash) DO UPDATE SET
                    author_name = EXCLUDED.author_name,
                    author_email = EXCLUDED.author_email,
                    committed_at = EXCLUDED.committed_at,
                    message = EXCLUDED.message,
                    parent_hash = EXCLUDED.parent_hash
            """, (
                commit_data["id"], commit_data["repository_id"], commit_data["commit_hash"],
                commit_data["author_name"], commit_data["author_email"], commit_data["committed_at"],
                commit_data["message"], commit_data["parent_hash"]
            ))

    def get_commit_id(self, repo_id: str, commit_hash: str) -> Optional[str]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM commits WHERE repository_id = ? AND commit_hash = ?",
                (repo_id, commit_hash)
            ).fetchone()
            return row["id"] if row else None

    def find_file_id_by_path(self, repo_id: str, file_path: str) -> Optional[str]:
        fp = file_path.replace("\\", "/").strip("/")
        with self.db.get_connection() as conn:
            row = conn.execute("""
                SELECT f.id FROM files f
                JOIN directories d ON f.directory_id = d.id
                WHERE f.repository_id = ? AND (
                    (d.relative_path = '' AND f.name = ?) OR
                    (d.relative_path || '/' || f.name = ?)
                )
            """, (repo_id, fp, fp)).fetchone()
            return row["id"] if row else None

    def upsert_file_commit(self, mapping_data: Dict[str, Any]):
        with self.db.transaction() as txn:
            txn.execute("""
                INSERT INTO file_commits (id, repository_id, file_id, commit_id, change_type)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(file_id, commit_id) DO UPDATE SET change_type = EXCLUDED.change_type
            """, (
                mapping_data["id"], mapping_data["repository_id"], mapping_data["file_id"],
                mapping_data["commit_id"], mapping_data["change_type"]
            ))
