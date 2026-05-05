"""
/**
 * @project   CodeCortex
 * @package   Core/Database
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-Database-v1.0
 * @stack     Python, SQLite
 * * Class DatabaseManager – Single Responsibility: Unified project intelligence storage.
 */
"""

import sqlite3
import uuid
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .logging_config import get_logger
from .graph_manager import GraphManager

# Aegis Structured Logging
logger = get_logger("CodeCortex.Core.Database")

class _LockedConnection:
    """Thread-safe proxy around sqlite3.Connection for check_same_thread=False usage."""
    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock):
        self._conn = conn
        self._lock = lock

    def execute(self, sql: str, parameters=()):
        with self._lock:
            return self._conn.execute(sql, parameters)

    def executemany(self, sql: str, parameters):
        with self._lock:
            return self._conn.executemany(sql, parameters)

    def executescript(self, sql: str):
        with self._lock:
            return self._conn.executescript(sql)

    def commit(self):
        with self._lock:
            return self._conn.commit()

    def rollback(self):
        with self._lock:
            return self._conn.rollback()

    def cursor(self):
        with self._lock:
            return self._conn.cursor()

    def close(self):
        with self._lock:
            return self._conn.close()

    def __enter__(self):
        return self._conn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._conn.__exit__(exc_type, exc_val, exc_tb)

    def __getattr__(self, name: str):
        return getattr(self._conn, name)


class DatabaseManager:
    """
    Manager for CodeCortex SQLite persistence.

    Implements Aegis-compliant schema and structured logging.
    SQLite is opened with check_same_thread=False to allow FastAPI/MCP async
    workers, so all execute() calls are automatically serialized via _lock.
    """
    def __init__(self, db_path: Optional[str] = None, workspace_id: Optional[str] = None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Explicit path to the database file.
            workspace_id: Optional ID for project-specific isolation.
        """
        try:
            project_root = Path(__file__).resolve().parents[2]
            
            if db_path:
                self.db_path = Path(db_path)
            else:
                env_path = (os.getenv("CODECORTEX_DB_PATH") or "").strip()
                if env_path:
                    candidate = Path(env_path)
                    self.db_path = candidate if candidate.is_absolute() else (project_root / candidate)
                else:
                    # Aegis Standard (Hub-and-Spoke):
                    # Internal Engine: database/codecortex.db
                    # Workspace Domain: database/workspaces/{workspace_id}/workspace.db
                    db_root = project_root / "database"
                    if workspace_id:
                        self.db_path = db_root / "workspaces" / workspace_id / "workspace.db"
                    else:
                        self.db_path = db_root / "codecortex.db"
            
            # Ensure the directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._lock = threading.Lock()
            # Open connection with check_same_thread=False for async compatibility
            raw_conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            raw_conn.row_factory = sqlite3.Row

            # Register REGEXP function for regex-based searching
            import re
            raw_conn.create_function("REGEXP", 2, lambda expr, item: re.search(expr, item) is not None if item else False)

            self.conn: sqlite3.Connection = _LockedConnection(raw_conn, self._lock)  # type: ignore[assignment]

            # Optimize performance (WAL mode for production stability)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA foreign_keys=ON")

            self._create_schema()
            self._log_event("INFO", "DATABASE_INITIALIZED", {
                "path": str(self.db_path),
                "workspace_id": workspace_id
            })
        except Exception as e:
            self._log_event("FATAL", "DATABASE_INIT_FAILED", {"error": str(e)})
            raise

    def _log_event(self, level: str, event_code: str, context: Dict):
        """Structured JSON logging per Aegis standard."""
        if level == "FATAL":
            logger.critical(f"[{event_code}]", extra={"context": context})
        elif level == "ERROR":
            logger.error(f"[{event_code}]", extra={"context": context})
        elif level == "WARN":
            logger.warning(f"[{event_code}]", extra={"context": context})
        else:
            logger.info(f"[{event_code}]", extra={"context": context})

    @contextmanager
    def transaction(self):
        """Context manager for safe database transactions, explicitly locked."""
        with self._lock:
            cursor = self.conn.cursor()
            try:
                yield cursor
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                self._log_event("ERROR", "TRANSACTION_FAILED", {"error": str(e)})
                raise
            finally:
                cursor.close()

    def _create_schema(self):
        """Initialize the multi-domain intelligence schema."""
        with self.conn:
            # 1. Repositories
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    root_path TEXT NOT NULL UNIQUE,
                    last_indexed_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Directories (Recursive hierarchy)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS directories (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    parent_id TEXT,
                    relative_path TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_id) REFERENCES directories(id) ON DELETE CASCADE
                )
            """)

            # 3. Files
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT,
                    directory_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    classification TEXT CHECK(classification IN ('code', 'doc', 'config', 'binary', 'other')),
                    size_bytes INTEGER,
                    content TEXT,
                    content_hash TEXT,
                    mtime DATETIME,
                    is_deleted BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
                    FOREIGN KEY (directory_id) REFERENCES directories(id) ON DELETE CASCADE
                )
            """)

            # 4. Symbols (AST hierarchy)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT,
                    file_id TEXT NOT NULL,
                    parent_id TEXT,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    symbol_type TEXT NOT NULL,
                    start_line INTEGER,
                    end_line INTEGER,
                    docstring TEXT,
                    signature TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_id) REFERENCES symbols(id) ON DELETE CASCADE
                )
            """)

            # 5. Edges (Connectivity Graph)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT CHECK(relation_type IN ('CALLS', 'INHERITS', 'IMPORTS', 'USES', 'DEFINES')),
                    line_number INTEGER,
                    weight REAL DEFAULT 1.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
                    FOREIGN KEY (source_id) REFERENCES symbols(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_id) REFERENCES symbols(id) ON DELETE CASCADE
                )
            """)

            # 6. Insights (Architectural/Security Intelligence)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS insights (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    target_code TEXT,
                    category TEXT NOT NULL,
                    insight_type TEXT NOT NULL,
                    metadata JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
                )
            """)

            # 7. Manifest Entries (Incremental indexing)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS manifest_entries (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    last_hash TEXT NOT NULL,
                    last_size_bytes INTEGER,
                    last_mtime REAL,
                    last_processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
                )
            """)

            # 8. Git Commits (History Tracking)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    commit_hash TEXT NOT NULL,
                    author_name TEXT,
                    author_email TEXT,
                    committed_at DATETIME,
                    message TEXT,
                    parent_hashes TEXT,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
                    UNIQUE(repository_id, commit_hash)
                )
            """)

            # 9. File Commits (History Mapping)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS file_commits (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    commit_id TEXT NOT NULL,
                    change_type TEXT CHECK(change_type IN ('A', 'M', 'D', 'R', 'T')),
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                    FOREIGN KEY (commit_id) REFERENCES commits(id) ON DELETE CASCADE,
                    UNIQUE(file_id, commit_id)
                )
            """)

            # 10. Execution Tasks (Background Jobs)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_tasks (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    type TEXT NOT NULL, -- 'test', 'lint', 'refactor'
                    status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'failed')),
                    payload TEXT, -- Input parameters
                    result TEXT, -- Output/Error
                    webhook_url TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
                )
            """)

            # Indices for performance
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repository_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_files_name ON files(name)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_code ON symbols(code)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_repo ON symbols(repository_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repository_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_commits_hash ON commits(commit_hash)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_file_commits_file ON file_commits(file_id)")

            self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_directories_repo_relpath ON directories(repository_id, relative_path)"
            )
            self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_files_repo_dir_name ON files(repository_id, directory_id, name)"
            )
            self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_manifest_repo_path ON manifest_entries(repository_id, file_path)"
            )

        # Migrations (backward-compat)
        def _add_column(sql: str) -> None:
            try:
                self.conn.execute(sql)
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    logger.warning("[MIGRATION_WARN] %s", e)

        _add_column("ALTER TABLE symbols ADD COLUMN metadata TEXT")
        _add_column("ALTER TABLE files ADD COLUMN repository_id TEXT")
        _add_column("ALTER TABLE symbols ADD COLUMN repository_id TEXT")
        _add_column("ALTER TABLE manifest_entries ADD COLUMN last_size_bytes INTEGER")
        _add_column("ALTER TABLE manifest_entries ADD COLUMN last_mtime REAL")
        _add_column("ALTER TABLE files ADD COLUMN content TEXT")
        _add_column("ALTER TABLE files ADD COLUMN is_deleted BOOLEAN DEFAULT 0")

        # Migration: remove UNIQUE constraint on symbols.code (causes silent data loss)
        try:
            row = self.conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='symbols'"
            ).fetchone()
            if row and row[0] and "code TEXT NOT NULL UNIQUE" in row[0]:
                self.conn.executescript("""
                    PRAGMA foreign_keys = OFF;
                    CREATE TABLE IF NOT EXISTS symbols_rebuild (
                        id TEXT PRIMARY KEY,
                        repository_id TEXT,
                        file_id TEXT NOT NULL,
                        parent_id TEXT,
                        code TEXT NOT NULL,
                        name TEXT NOT NULL,
                        symbol_type TEXT NOT NULL,
                        start_line INTEGER,
                        end_line INTEGER,
                        docstring TEXT,
                        signature TEXT,
                        metadata TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
                        FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                        FOREIGN KEY (parent_id) REFERENCES symbols_rebuild(id) ON DELETE CASCADE
                    );
                    INSERT OR IGNORE INTO symbols_rebuild
                        SELECT id, repository_id, file_id, parent_id, code, name, symbol_type,
                               start_line, end_line, docstring, signature, metadata, created_at
                        FROM symbols;
                    DROP TABLE symbols;
                    ALTER TABLE symbols_rebuild RENAME TO symbols;
                    PRAGMA foreign_keys = ON;
                """)
                logger.info("[MIGRATION] Removed UNIQUE constraint from symbols.code")
        except Exception as e:
            logger.warning("[MIGRATION_WARN] symbols.code UNIQUE removal failed: %s", e)

        try:
            self.conn.execute(
                """
                UPDATE files
                SET repository_id = (
                    SELECT d.repository_id FROM directories d WHERE d.id = files.directory_id
                )
                WHERE repository_id IS NULL
                """
            )
        except sqlite3.OperationalError as e:
            logger.warning("[MIGRATION_WARN] files.repository_id backfill: %s", e)

        try:
            self.conn.execute(
                """
                UPDATE symbols
                SET repository_id = (
                    SELECT f.repository_id FROM files f WHERE f.id = symbols.file_id
                )
                WHERE repository_id IS NULL
                """
            )
        except sqlite3.OperationalError as e:
            logger.warning("[MIGRATION_WARN] symbols.repository_id backfill: %s", e)

    @property
    def graph_manager(self) -> GraphManager:
        """Lazy access to the graph backend manager (Kùzu/Neo4j/FalkorDB)."""
        if not hasattr(self, '_graph_manager'):
            self._graph_manager = GraphManager()
        return self._graph_manager

    def close(self):
        """Close the database connection and graph backend."""
        if hasattr(self, 'conn'):
            self.conn.close()
        if hasattr(self, '_graph_manager'):
            self._graph_manager.close()

    @staticmethod
    def generate_id() -> str:
        """Generate a standard UUID string."""
        return str(uuid.uuid4())
