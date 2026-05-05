"""
/**
 * @project   CodeCortex
 * @package   Domain/Repository
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Class RepositoryService – Single Responsibility: Manage physical codebase discovery and manifest tracking.
 */
"""

import os
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from src.core.database import DatabaseManager
from src.core.logging_config import get_logger
from src.domain.coderepository.infrastructure.file_reader import FileReader
from src.domain.coderepository.application.analyzer import RepoStructureAnalyzer
from src.domain.coderepository.core.dto import FileStructure
from src.domain.coderepository.core.store import ICodeRepositoryStore
from src.domain.coderepository.infrastructure.git_history import GitHistoryWorker
import re
import asyncio

logger = get_logger("CodeCortex.Domain.CodeRepository")

class CodeRepositoryService:
    """
    Handles codebase discovery and synchronization with SQLite.

    Uses gitignore-aware filtering and manifest-based delta tracking.
    """
    def __init__(self, store: ICodeRepositoryStore, repo_path: Optional[str] = None):
        self.store = store
        self.repo_path = Path(repo_path) if repo_path else None
        self.reader = None
        self.analyzer = None
        if self.repo_path:
            self.reader = FileReader(self.repo_path)
            self.analyzer = RepoStructureAnalyzer(self.repo_path)

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: str = "internal"):
        """Standardized structured logging."""
        context["request_id"] = request_id
        msg = f"[{event_code}] {json.dumps(context)}"
        if level == "ERROR":
            logger.error(msg, extra={"context": context})
        elif level == "WARN":
            logger.warning(msg, extra={"context": context})
        else:
            logger.info(msg, extra={"context": context})

    async def sync_repository(self, root_path: str, request_id: str = "internal") -> str:
        """
        Synchronize physical files with the database.
        Returns the repository_id.
        """
        root = Path(root_path).resolve()
        repo_name = root.name

        self._log_event("INFO", "REPO_SYNC_STARTED", {"path": str(root)}, request_id)

        hash_reader = FileReader(root)
        repo_id = self.store.upsert_repository(repo_name, str(root))
        root_dir_id = self.store.ensure_directory_chain(repo_id, "")

        # 2. Get Ignore Spec
        spec = self._load_ignore_spec(root)

        # 3. Recursive Discovery (Running in thread pool to avoid blocking)
        await asyncio.to_thread(
            self._discover_recursive, root, root, repo_id, root_dir_id, spec, hash_reader=hash_reader
        )

        # 4. Index Git History (NEW)
        try:
            history_worker = GitHistoryWorker(self.store, root)
            await asyncio.to_thread(history_worker.index_history, repo_id)
        except Exception as e:
            self._log_event("WARN", "GIT_HISTORY_FAILED", {"error": str(e)}, request_id)

        self.store.update_indexing_time(repo_id)
        self._log_event("INFO", "REPO_SYNC_COMPLETED", {"repo_id": repo_id}, request_id)
        return repo_id

    async def sync_repository_with_changes(self, root_path: str) -> Tuple[str, List[str]]:
        root = Path(root_path).resolve()
        self._log_event("INFO", "REPO_SYNC_STARTED", {"path": str(root), "mode": "with_changes"})
        changed: List[str] = []
        hash_reader = FileReader(root)
        
        repo_id = self.store.upsert_repository(root.name, str(root))
        root_dir_id = self.store.ensure_directory_chain(repo_id, "")
        spec = self._load_ignore_spec(root)
        
        await asyncio.to_thread(
            self._discover_recursive,
            root,
            root,
            repo_id,
            root_dir_id,
            spec,
            hash_reader=hash_reader,
            changed_paths=changed,
        )
        self.store.update_indexing_time(repo_id)
        self._log_event("INFO", "REPO_SYNC_COMPLETED", {"repo_id": repo_id, "changed": len(changed)})
        return repo_id, changed

    async def sync_repository_paths(self, root_path: str, include_paths: List[str]) -> Tuple[str, List[str]]:
        root = Path(root_path).resolve()
        include_paths = [p for p in include_paths if isinstance(p, str) and p.strip()]
        self._log_event("INFO", "REPO_SYNC_STARTED", {"path": str(root), "mode": "paths", "paths": len(include_paths)})
        changed: List[str] = []
        hash_reader = FileReader(root)
        
        repo_id = self.store.upsert_repository(root.name, str(root))
        spec = self._load_ignore_spec(root)
        
        for p in include_paths:
            rel = self._normalize_to_relpath(root, p)
            if rel is None:
                continue
            abs_path = (root / rel).resolve()
            if not str(abs_path).startswith(str(root)):
                continue
            if not abs_path.exists():
                continue

            if abs_path.is_dir():
                dir_id = self.store.ensure_directory_chain(repo_id, rel)
                await asyncio.to_thread(
                    self._discover_recursive,
                    abs_path,
                    root,
                    repo_id,
                    dir_id,
                    spec,
                    hash_reader=hash_reader,
                    changed_paths=changed,
                )
            elif abs_path.is_file():
                parent_rel = str(Path(rel).parent).replace("\\", "/")
                if parent_rel == ".":
                    parent_rel = ""
                parent_dir_id = self.store.ensure_directory_chain(repo_id, parent_rel)
                await asyncio.to_thread(
                    self._upsert_file,
                    repo_id,
                    root,
                    abs_path,
                    parent_dir_id,
                    spec,
                    hash_reader=hash_reader,
                    changed_paths=changed,
                )
        self.store.update_indexing_time(repo_id)
        self._log_event("INFO", "REPO_SYNC_COMPLETED", {"repo_id": repo_id, "changed": len(changed)})
        return repo_id, changed

    # Legacy _upsert_repository and _ensure_directory_chain removed in favor of Store

    def _normalize_to_relpath(self, root: Path, path: str) -> Optional[str]:
        raw = path.strip().replace("\\", "/")
        if raw.startswith("./"):
            raw = raw[2:]
        try:
            p = Path(raw)
            if p.is_absolute():
                try:
                    rel = Path(path).resolve().relative_to(root)
                    return str(rel).replace("\\", "/")
                except Exception:
                    return None
            return str(p).replace("\\", "/").strip("/")
        except Exception:
            return None


    def _load_ignore_spec(self, root: Path) -> PathSpec:
        """Load .gitignore if present."""
        gitignore = root / ".gitignore"
        patterns = [
            ".git/",
            "__pycache__/",
            "*.pyc",
            "*.db",
            "*.db-*",
            "*.sqlite",
            "*.sqlite-*",
            "vendor/",
            "database/",
            "outputs/",
            "logs/",
            ".venv/",
            "venv/",
            "node_modules/",
            "dist/",
            "build/",
            ".mypy_cache/",
            ".pytest_cache/",
            ".ruff_cache/",
        ]
        if gitignore.exists():
            with open(gitignore, "r") as f:
                patterns.extend(f.readlines())
        return PathSpec.from_lines(GitWildMatchPattern, patterns)

    def _discover_recursive(
        self,
        current_path: Path,
        root: Path,
        repo_id: str,
        parent_dir_id: Optional[str],
        spec: PathSpec,
        *,
        hash_reader: Optional[FileReader] = None,
        changed_paths: Optional[List[str]] = None,
    ):
        """Recursively index directories and files."""
        try:
            items = list(current_path.iterdir())
        except PermissionError:
            self._log_event("WARN", "DIRECTORY_ACCESS_DENIED", {"path": str(current_path)})
            return
        except Exception as e:
            self._log_event("ERROR", "DISCOVERY_ERROR", {"path": str(current_path), "error": str(e)})
            return

        for item in items:
            try:
                rel_path = item.relative_to(root)
                if spec.match_file(str(rel_path)):
                    continue

                if item.is_dir():
                    dir_id = self.store.ensure_directory_chain(repo_id, str(rel_path))
                    self._discover_recursive(
                        item,
                        root,
                        repo_id,
                        dir_id,
                        spec,
                        hash_reader=hash_reader,
                        changed_paths=changed_paths,
                    )
                    continue

                if item.is_file():
                    self._upsert_file(
                        repo_id,
                        root,
                        item,
                        parent_dir_id,
                        spec,
                        hash_reader=hash_reader,
                        changed_paths=changed_paths,
                    )
            except PermissionError:
                self._log_event("WARN", "FILE_ACCESS_DENIED", {"path": str(item)})
            except Exception as e:
                self._log_event("ERROR", "DISCOVERY_ITEM_ERROR", {"path": str(item), "error": str(e)})

    def _upsert_file(
        self,
        repo_id: str,
        root: Path,
        item: Path,
        parent_dir_id: Optional[str],
        spec: PathSpec,
        *,
        hash_reader: Optional[FileReader] = None,
        changed_paths: Optional[List[str]] = None,
    ) -> None:
        rel_path = item.relative_to(root)
        if spec.match_file(str(rel_path)):
            return

        classification = self._classify_file(item)
        stat = item.stat()
        size_bytes = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime)
        mtime_epoch = float(stat.st_mtime)

        row = self.store.get_manifest_entry(repo_id, str(rel_path))

        if row and row["last_size_bytes"] is not None and row["last_mtime"] is not None:
            if int(row["last_size_bytes"]) == int(size_bytes) and float(row["last_mtime"]) == mtime_epoch:
                return

        reader = hash_reader or FileReader(root)
        file_hash = reader.calculate_hash(str(rel_path))
        is_changed = (not row) or row["last_hash"] != file_hash
        if not is_changed:
            return

        # Capture content for persistence (limit to 5MB)
        content = None
        if classification in ('code', 'doc', 'config'):
            if size_bytes <= 5 * 1024 * 1024:
                try:
                    content = item.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

        self.store.upsert_file_and_manifest(
            {
                "id": str(uuid.uuid4()),
                "repository_id": repo_id,
                "directory_id": parent_dir_id,
                "name": item.name,
                "classification": classification,
                "size_bytes": size_bytes,
                "content": content,
                "content_hash": file_hash,
                "mtime": mtime
            },
            {
                "id": str(uuid.uuid4()),
                "repository_id": repo_id,
                "file_path": str(rel_path),
                "last_hash": file_hash,
                "last_size_bytes": int(size_bytes),
                "last_mtime": mtime_epoch
            }
        )

        if changed_paths is not None:
            changed_paths.append(str(rel_path).replace("\\", "/"))

    def _classify_file(self, file_path: Path) -> str:
        """
        Enhanced classification based on extensions and content heuristics.
        Ported from Graphify/detect.py logic.
        """
        ext = file_path.suffix.lower()
        name = file_path.name.lower()

        # Sensitive patterns (skip or mark as other/binary)
        SENSITIVE_PATTERNS = [
            r'\.env', r'\.envrc', r'\.pem$', r'\.key$', r'\.p12$', r'\.pfx$', r'\.cert$', r'\.crt$',
            r'credential', r'secret', r'passwd', r'password', r'token', r'private_key',
            r'id_rsa', r'aws_credentials', r'gcloud_credentials'
        ]
        if any(re.search(p, name) for p in SENSITIVE_PATTERNS):
            return 'other' # Security guard

        # Asset directory markers (Xcode etc)
        ASSET_DIR_MARKERS = {".imageset", ".xcassets", ".appiconset", ".colorset", ".launchimage"}
        if any(part.endswith(tuple(ASSET_DIR_MARKERS)) for part in file_path.parts):
            return 'binary'

        # Code files
        code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.cpp',
            '.c', '.h', '.hpp', '.cs', '.php', '.rb', '.swift', '.kt',
            '.scala', '.clj', '.ex', '.exs', '.erl', '.hs', '.lua', '.r',
            '.m', '.pl', '.pm', '.t', '.sql', '.sh', '.bash', '.zsh', '.v', '.sv', '.zig', '.jl'
        }
        if ext in code_extensions:
            return 'code'

        # Documentation files
        doc_extensions = {'.md', '.rst', '.txt', '.adoc', '.tex', '.pdf', '.docx', '.xlsx', '.doc', '.html'}
        if ext in doc_extensions:
            # Check for academic paper signals if .txt or .md
            if ext in ['.txt', '.md']:
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")[:3000]
                    paper_signals = [r'\barxiv\b', r'\bdoi\s*:', r'\babstract\b', r'\bproceedings\b', r'\bjournal\b', r'\[\d+\]']
                    hits = sum(1 for p in paper_signals if re.search(p, text, re.I))
                    if hits >= 3:
                        return 'doc' # Could be 'paper' but keeping to CodeCortex baseline
                except Exception:
                    pass
            return 'doc'

        # Configuration files
        config_extensions = {
            '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
            '.xml', '.properties', '.env', '.config'
        }
        if ext in config_extensions:
            return 'config'

        # Binary files
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico',
            '.mp3', '.mp4', '.wav', '.ogg', '.zip', '.tar', '.gz', '.exe',
            '.dll', '.so', '.dylib', '.bin', '.class', '.pyc', '.o', '.a'
        }
        if ext in binary_extensions:
            return 'binary'

        return 'other'

    async def initialize(self, path: str) -> str:
        """
        Initialize repository for analysis.

        @param path: Absolute path to repository root
        @return: Status message
        """
        try:
            self.repo_path = Path(path).resolve()
            self.reader = FileReader(self.repo_path)
            self.analyzer = RepoStructureAnalyzer(self.repo_path)
            repo_id = await self.sync_repository(path)
            return f"Successfully initialized repository at: {path} (ID: {repo_id})"
        except Exception as e:
            self._log_event("ERROR", "INIT_FAILED", {"path": path, "error": str(e)})
            raise

    def get_info(self) -> str:
        """
        Get information about the currently initialized repository.

        @return: Formatted repository information
        """
        if not self.repo_path:
            return "No repository initialized. Call initialize() first."

        info = [
            f"Code Repository Information:",
            f"Path: {self.repo_path}",
            f"Exists: {self.repo_path.exists()}",
            f"Is Directory: {self.repo_path.is_dir()}"
        ]

        gitignore_path = self.repo_path / '.gitignore'
        if gitignore_path.exists():
            info.append("Found .gitignore file")

        return "\n".join(info)

    def get_structure(self, sub_path: Optional[str] = None, depth: Optional[int] = None) -> str:
        """
        Get the structure of files and directories.

        @param sub_path: Optional subdirectory path
        @param depth: Maximum traversal depth (default 3)
        @return: Formatted file tree
        """
        if not self.analyzer:
            return "No repository initialized. Call initialize() first."

        if depth is None:
            depth = 3

        try:
            structure = self.analyzer.get_structure(sub_path, depth)
            return self._format_structure(structure)
        except Exception as e:
            self._log_event("ERROR", "STRUCTURE_FAILED", {"error": str(e)})
            return f"Error getting structure: {str(e)}"

    def _format_structure(self, node: FileStructure, indent: int = 0) -> str:
        """Recursively format file structure as tree."""
        prefix = "  " * indent
        if node.type == "directory":
            lines = [f"{prefix}[DIR] {node.path}/"]
            for child in (node.children or []):
                lines.append(self._format_structure(child, indent + 1))
            return "\n".join(lines)
        else:
            size_str = f" ({node.size} bytes)" if node.size else ""
            return f"{prefix}[FILE] {node.path}{size_str}"

    def read_file(self, file_path: str) -> str:
        """
        Read and display file contents.

        @param file_path: Path relative to repository root
        @return: File contents or error message
        """
        if not self.reader:
            return "No repository initialized. Call initialize() first."

        try:
            content = self.reader.read(file_path)
            if content.startswith("Error:"):
                return content

            rel_path = file_path if file_path else "root"
            return f"File: {rel_path}\nLanguage: {self._detect_language(file_path)}\n\n{content}"
        except Exception as e:
            self._log_event("ERROR", "READ_FAILED", {"path": file_path, "error": str(e)})
            return f"Error reading file {file_path}: {str(e)}"

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.sql': 'sql',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.md': 'markdown',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.vue': 'vue',
            '.svelte': 'svelte',
        }
        return lang_map.get(ext, 'text')
