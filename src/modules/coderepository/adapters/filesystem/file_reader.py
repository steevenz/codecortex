"""
Class FileReader – Single Responsibility: Safely read file contents from the repository.

:project: CodeCortex
:package: Modules.Coderepository.Adapters.Filesystem.File_reader
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""

from __future__ import annotations
from pathlib import Path

import hashlib

class FileReader:
    """
    Safely reads file contents with size and line limits.
    """
    def __init__(self, repo_path: Path):
        """
        Initialize with repository path and default limits.

        @param repo_path: Absolute path to the repository
        """
        self.repo_path = repo_path
        self.MAX_SIZE = 10 * 1024 * 1024  # Increased to 10MB for indexing
        self.MAX_LINES = 1000

    def calculate_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file."""
        full_path = (self.repo_path / file_path).resolve()
        sha256_hash = hashlib.sha256()
        with open(full_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def read(self, file_path: str) -> str:
        """
        Read a file from the repository.

        @param file_path: Path relative to repository root
        @return: File contents or error message
        """
        # Enhanced path traversal protection
        if not file_path:
            return "Error: File path cannot be empty."

        # Check for path traversal patterns
        if ".." in file_path or file_path.startswith("/") or "\\" in file_path:
            return f"Error: Path traversal detected in {file_path}"

        try:
            full_path = (self.repo_path / file_path).resolve()

            # Verify the resolved path is still within repository
            if not str(full_path).startswith(str(self.repo_path.resolve())):
                return f"Error: Path {file_path} is outside repository root."

            if not full_path.exists():
                return f"Error: File {file_path} does not exist."

            if not full_path.is_file():
                return f"Error: {file_path} is not a file."

            # Check file size
            if full_path.stat().st_size > self.MAX_SIZE:
                return f"Error: File {file_path} is too large (> 10MB)."

            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= self.MAX_LINES:
                        lines.append("\n[... File truncated due to line limit ...]")
                        break
                    lines.append(line)
                return "".join(lines)
        except PermissionError:
            return f"Error: Permission denied reading {file_path}"
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"

    def read_raw(self, file_path: str) -> bytes:
        """
        Read a file as raw bytes.

        @param file_path: Path relative to repository root
        @return: File bytes
        """
        full_path = (self.repo_path / file_path).resolve()
        if not str(full_path).startswith(str(self.repo_path)):
            raise ValueError("Access denied")

        with open(full_path, 'rb') as f:
            return f.read()
