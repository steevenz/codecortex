"""
Filesystem Configuration and Utilities.

Provides secure file operations with audit logging,
backup management, and performance monitoring.

:project: CodeCortex
:package: Filesystem.Config
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: FS-SEC-v1.0
"""

from __future__ import annotations

import os
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class FilesystemConfig:
    """Configuration for filesystem operations."""
    
    MAX_FILE_SIZE = 100 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'.py', '.js', '.ts', '.json', '.md', '.txt', '.yaml', '.yml', '.toml', '.cfg', '.ini'}
    SENSITIVE_EXTENSIONS = {'.env', '.key', '.pem', '.p12', '.pfx', '.sql', '.log'}
    ENCRYPTED_EXTENSIONS = {'.enc', '.encrypted'}
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or os.getcwd()).resolve()
        self.log_path = self.base_path / "logs" / "filesystem.log"
        self.backup_path = self.base_path / "database" / "backups"
        self._setup_logging()
    
    def _setup_logging(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(self.log_path)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
    
    def is_safe_path(self, path: Path) -> bool:
        """Check if path is within allowed base path."""
        try:
            path.resolve().relative_to(self.base_path)
            return True
        except ValueError:
            return False
    
    def is_sensitive(self, path: Path) -> bool:
        """Check if file contains sensitive data."""
        return path.suffix in self.SENSITIVE_EXTENSIONS or path.name in {'.env', 'credentials.json'}
    
    def compute_hash(self, path: Path) -> str:
        """Compute SHA256 hash of file."""
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()


FILESYSTE_CONFIG = FilesystemConfig()