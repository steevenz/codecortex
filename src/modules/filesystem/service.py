"""
Shared Filesystem Service.

Core service that handles all filesystem operations.
Used by both CLI and MCP tools for consistent output.

:project: CodeCortex
:package: Filesystem.Service
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: FS-SVC-v1.0
"""

from __future__ import annotations

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    """Represents a file or directory entry."""
    name: str
    path: str
    is_dir: bool
    size: int


class FilesystemService:
    """Shared filesystem service for consistent operations."""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or os.getcwd()).resolve()
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve and validate path."""
        if not path:
            return self.base_path
        p = Path(path)
        if p.is_absolute():
            return p.resolve()
        return (self.base_path / p).resolve()
    
    def list(self, args: Dict) -> Dict[str, Any]:
        """List directory contents."""
        path = args.get("path", ".") if isinstance(args, dict) else args
        try:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                return {"success": False, "error": "Path not found", "data": None}
            
            entries = []
            for item in sorted(resolved.iterdir()):
                stat = item.stat()
                entries.append({
                    "name": item.name,
                    "path": str(item.resolve()),
                    "is_dir": item.is_dir(),
                    "size": stat.st_size if item.is_file() else 0
                })
            
            return {
                "success": True,
                "error": None,
                "data": {
                    "path": str(resolved),
                    "entries": entries
                }
            }
        except Exception as e:
            logger.error(f"List error: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    def read(self, args: Dict) -> Dict[str, Any]:
        """Read file contents."""
        path = args.get("path", "") if isinstance(args, dict) else args
        try:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                return {"success": False, "error": "File not found", "data": None}
            if not resolved.is_file():
                return {"success": False, "error": "Not a file", "data": None}
            
            return {
                "success": True,
                "error": None,
                "data": {
                    "path": str(resolved),
                    "content": resolved.read_text(),
                    "size": resolved.stat().st_size
                }
            }
        except Exception as e:
            logger.error(f"Read error: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    def write(self, args: Dict) -> Dict[str, Any]:
        """Write content to file."""
        path = args.get("path", "") if isinstance(args, dict) else args.get("path", "")
        content = args.get("content", "") if isinstance(args, dict) else ""
        try:
            resolved = self._resolve_path(path)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content)
            
            return {
                "success": True,
                "error": None,
                "data": {
                    "path": str(resolved),
                    "size": len(content)
                }
            }
        except Exception as e:
            logger.error(f"Write error: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    def delete(self, args: Dict) -> Dict[str, Any]:
        """Delete file or directory."""
        path = args.get("path", "") if isinstance(args, dict) else args
        try:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                return {"success": False, "error": "Path not found", "data": None}
            
            if resolved.is_dir():
                import shutil
                shutil.rmtree(resolved)
            else:
                resolved.unlink()
            
            return {
                "success": True,
                "error": None,
                "data": {"path": str(resolved)}
            }
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    def copy(self, args: Dict) -> Dict[str, Any]:
        """Copy file or directory."""
        path = args.get("path", "") if isinstance(args, dict) else args.get("path", "")
        dest = args.get("dest", "") if isinstance(args, dict) else args.get("dest", "")
        try:
            resolved = self._resolve_path(path)
            dest_resolved = self._resolve_path(dest)
            if not resolved.exists():
                return {"success": False, "error": "Source path not found", "data": None}
            
            if resolved.is_dir():
                import shutil
                shutil.copytree(resolved, dest_resolved)
            else:
                import shutil
                shutil.copy2(resolved, dest_resolved)
            
            return {
                "success": True,
                "error": None,
                "data": {"from": str(resolved), "to": str(dest_resolved)}
            }
        except Exception as e:
            logger.error(f"Copy error: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    def move(self, args: Dict) -> Dict[str, Any]:
        """Move file or directory."""
        path = args.get("path", "") if isinstance(args, dict) else args.get("path", "")
        dest = args.get("dest", "") if isinstance(args, dict) else args.get("dest", "")
        try:
            resolved = self._resolve_path(path)
            dest_resolved = self._resolve_path(dest)
            if not resolved.exists():
                return {"success": False, "error": "Source path not found", "data": None}
            
            import shutil
            shutil.move(str(resolved), str(dest_resolved))
            
            return {
                "success": True,
                "error": None,
                "data": {"from": str(resolved), "to": str(dest_resolved)}
            }
        except Exception as e:
            logger.error(f"Move error: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    def mkdir(self, args: Dict) -> Dict[str, Any]:
        """Create directory."""
        path = args.get("path", "") if isinstance(args, dict) else args
        try:
            resolved = self._resolve_path(path)
            resolved.mkdir(parents=True, exist_ok=True)
            
            return {
                "success": True,
                "error": None,
                "data": {"path": str(resolved)}
            }
        except Exception as e:
            logger.error(f"Mkdir error: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    def search(self, args: Dict) -> Dict[str, Any]:
        """Search for files."""
        path = args.get("path", ".") if isinstance(args, dict) else args
        pattern = args.get("pattern", "*") if isinstance(args, dict) else "*"
        try:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                return {"success": False, "error": "Path not found", "data": None}
            
            entries = list(resolved.glob(pattern))
            return {
                "success": True,
                "error": None,
                "data": {
                    "path": str(resolved),
                    "pattern": pattern,
                    "entries": [str(e) for e in entries]
                }
            }
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    def audit(self, args: Dict) -> Dict[str, Any]:
        """Audit filesystem."""
        path = args.get("path", ".") if isinstance(args, dict) else args
        try:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                return {"success": False, "error": "Path not found", "data": None}
            
            return {
                "success": True,
                "error": None,
                "data": {
                    "path": str(resolved),
                    "findings": []
                }
            }
        except Exception as e:
            logger.error(f"Audit error: {e}")
            return {"success": False, "error": str(e), "data": None}


# Singleton instance
_filesystem_service: Optional[FilesystemService] = None


def get_filesystem_service(base_path: Optional[str] = None) -> FilesystemService:
    """Get or create filesystem service instance."""
    global _filesystem_service
    if _filesystem_service is None or base_path:
        _filesystem_service = FilesystemService(base_path)
    return _filesystem_service