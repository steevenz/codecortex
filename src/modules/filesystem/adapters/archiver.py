"""
Archiver.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Archiver
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from pathlib import Path
import zipfile
import tarfile
import os
import time

from src.core import ApiError

ARCHIVE_EXT_MAP = {
    ".zip": "zip",
    ".tar": "tar",
    ".tar.gz": "tar.gz",
    ".tgz": "tar.gz",
    ".tar.bz2": "tar.bz2",
    ".tbz2": "tar.bz2",
    ".tar.xz": "tar.xz",
    ".txz": "tar.xz",
}

ARCHIVE_FORMATS = {"zip", "tar", "tar.gz", "tar.bz2", "tar.xz"}


import mimetypes

from src.core.utils.path import norm_path as _norm


def _detect_format(archive_path: str, explicit_format: Optional[str] = None) -> Optional[str]:
    if explicit_format and explicit_format in ARCHIVE_FORMATS:
        return explicit_format
    p = archive_path.lower()
    for ext, fmt in sorted(ARCHIVE_EXT_MAP.items(), key=lambda x: -len(x[0])):
        if p.endswith(ext):
            return fmt
    return None


class DiskArchiver:
    """Archive operations: list contents, extract, and create archives.
    Supports ZIP (zipfile) and TAR (tarfile) formats — both built-in.
    """

    @staticmethod
    def execute(params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action", "")
        archive_path = params.get("archive_path", "")
        dry_run = params.get("dry_run", False)
        overwrite = params.get("overwrite", False)

        if not archive_path:
            raise ApiError("archive_path is required for archive operation", status_code=400, error_code="FS_004")
        if not action:
            raise ApiError("action (list/extract/create) is required for archive operation", status_code=400, error_code="FS_004")

        fmt = _detect_format(archive_path, params.get("format"))
        if not fmt:
            raise ApiError(
                f"Cannot detect archive format from: {archive_path}. Supported: zip, tar, tar.gz, tar.bz2, tar.xz",
                status_code=400,
                error_code="FS_004",
            )

        abs_archive = str(Path(archive_path).resolve())

        if action == "list":
            return DiskArchiver._list(abs_archive, fmt)
        elif action == "extract":
            target_dir = params.get("target_dir", "")
            if not target_dir:
                raise ApiError("target_dir is required for extract", status_code=400, error_code="FS_004")
            abs_target = str(Path(target_dir).resolve())
            if dry_run:
                return DiskArchiver._dry_run_extract(abs_archive, fmt, abs_target)
            return DiskArchiver._extract(abs_archive, fmt, abs_target, overwrite)
        elif action == "create":
            target_dir = params.get("target_dir", "")
            files_to_add = params.get("files_to_add")
            compression = params.get("compression_level", 6)
            if dry_run:
                return DiskArchiver._dry_run_create(abs_archive, fmt, target_dir, files_to_add)
            return DiskArchiver._create(abs_archive, fmt, target_dir, files_to_add, compression, overwrite)
        else:
            raise ApiError(f"Unknown archive action: {action}. Use: list, extract, create", status_code=400, error_code="FS_004")

    @staticmethod
    def _list(archive_path: str, fmt: str) -> Dict[str, Any]:
        if not os.path.isfile(archive_path):
            raise ApiError(f"Archive not found: {archive_path}", status_code=404, error_code="FS_004")

        entries: List[Dict[str, Any]] = []
        total_size = 0

        try:
            if fmt == "zip":
                with zipfile.ZipFile(archive_path, "r") as zf:
                    for info in zf.infolist():
                        entry: Dict[str, Any] = {"name": _norm(info.filename)}
                        if not info.filename.endswith("/"):
                            entry["type"] = "file"
                            entry["size"] = info.file_size
                            entry["compressed_size"] = info.compress_size
                            total_size += info.file_size
                            ext = Path(info.filename).suffix.lower()
                            entry["file_type"] = mimetypes.guess_type(info.filename)[0] or "application/octet-stream"
                            if info.date_time:
                                try:
                                    entry["modified"] = time.strftime(
                                        "%Y-%m-%dT%H:%M:%SZ", info.date_time
                                    )
                                except Exception:
                                    pass
                        else:
                            entry["type"] = "directory"
                        entries.append(entry)
            else:
                mode_map = {
                    "tar": "r:",
                    "tar.gz": "r:gz",
                    "tar.bz2": "r:bz2",
                    "tar.xz": "r:xz",
                }
                mode = mode_map.get(fmt, "r:")
                with tarfile.open(archive_path, mode) as tf:
                    for info in tf.getmembers():
                        entry: Dict[str, Any] = {
                            "name": _norm(info.name),
                            "type": "directory" if info.isdir() else "file",
                        }
                        if info.isfile():
                            entry["size"] = info.size
                            total_size += info.size
                            ext = Path(info.name).suffix.lower()
                            entry["file_type"] = mimetypes.guess_type(info.name)[0] or "application/octet-stream"
                        if info.mtime:
                            try:
                                entry["modified"] = time.strftime(
                                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(info.mtime)
                                )
                            except Exception:
                                pass
                        entries.append(entry)

            compression_ratio = round(total_size / os.path.getsize(archive_path), 2) if os.path.getsize(archive_path) else None
            return {
                "status_code": 200,
                "message": f"Archive listing: {len(entries)} entries",
                "data": {
                    "operation": "archive",
                    "action": "list",
                    "archive_path": _norm(archive_path),
                    "format": fmt,
                    "total_entries": len(entries),
                    "total_size_bytes": total_size,
                    "archive_size_bytes": os.path.getsize(archive_path),
                    "compression_ratio": compression_ratio,
                    "entries": entries,
                },
            }
        except (zipfile.BadZipFile, tarfile.TarError, FileNotFoundError) as e:
            raise ApiError(f"Failed to read archive: {e}", status_code=400, error_code="FS_004")

    @staticmethod
    def _extract(archive_path: str, fmt: str, target_dir: str, overwrite: bool) -> Dict[str, Any]:
        if not os.path.isfile(archive_path):
            raise ApiError(f"Archive not found: {archive_path}", status_code=404, error_code="FS_004")

        os.makedirs(target_dir, exist_ok=True)
        target_path = Path(target_dir).resolve()
        extracted = 0
        skipped = 0
        conflicts: List[str] = []

        try:
            if fmt == "zip":
                with zipfile.ZipFile(archive_path, "r") as zf:
                    for info in zf.infolist():
                        dest = target_path / info.filename
                        resolved = dest.resolve()
                        if not str(resolved).startswith(str(target_path)):
                            raise ApiError(f"Path traversal detected: {info.filename}", status_code=400, error_code="FS_004")
                        if dest.exists() and not overwrite:
                            conflicts.append(str(dest))
                            skipped += 1
                            continue
                        extracted += 1
                    if conflicts:
                        raise ApiError(
                            f"Extraction aborted: {len(conflicts)} file(s) already exist. First conflict: {_norm(conflicts[0])}",
                            status_code=409,
                            error_code="FS_004",
                            details={
                                "conflict_path": _norm(conflicts[0]),
                                "total_conflicts": len(conflicts),
                                "suggestion": "Set overwrite=true to overwrite existing files",
                            },
                        )
                    zf.extractall(path=target_dir)
            else:
                mode_map = {
                    "tar": "r:",
                    "tar.gz": "r:gz",
                    "tar.bz2": "r:bz2",
                    "tar.xz": "r:xz",
                }
                mode = mode_map.get(fmt, "r:")
                with tarfile.open(archive_path, mode) as tf:
                    for info in tf.getmembers():
                        dest = target_path / info.name
                        resolved = dest.resolve()
                        if not str(resolved).startswith(str(target_path)):
                            raise ApiError(f"Path traversal detected: {info.name}", status_code=400, error_code="FS_004")
                        if dest.exists() and not overwrite:
                            conflicts.append(str(dest))
                            skipped += 1
                            continue
                        extracted += 1
                    if conflicts:
                        raise ApiError(
                            f"Extraction aborted: {len(conflicts)} file(s) already exist. First conflict: {_norm(conflicts[0])}",
                            status_code=409,
                            error_code="FS_004",
                            details={
                                "conflict_path": _norm(conflicts[0]),
                                "total_conflicts": len(conflicts),
                                "suggestion": "Set overwrite=true to overwrite existing files",
                            },
                        )
                    tf.extractall(path=target_dir)

            extracted_files: List[Dict[str, Any]] = []
            if fmt == "zip":
                with zipfile.ZipFile(archive_path, "r") as zf:
                    for info in zf.infolist():
                        if not info.filename.endswith("/"):
                            dest = target_path / info.filename
                            if dest.exists():
                                extracted_files.append({
                                    "name": _norm(info.filename),
                                    "size_bytes": info.file_size,
                                    "file_type": mimetypes.guess_type(info.filename)[0] or "application/octet-stream",
                                })
            else:
                mode_map = {"tar": "r:", "tar.gz": "r:gz", "tar.bz2": "r:bz2", "tar.xz": "r:xz"}
                mode = mode_map.get(fmt, "r:")
                with tarfile.open(archive_path, mode) as tf:
                    for info in tf.getmembers():
                        if info.isfile():
                            extracted_files.append({
                                "name": _norm(info.name),
                                "size_bytes": info.size,
                                "file_type": mimetypes.guess_type(info.name)[0] or "application/octet-stream",
                            })

            return {
                "status_code": 200,
                "message": f"Extracted {extracted} entries to {_norm(target_dir)}",
                "data": {
                    "operation": "archive",
                    "action": "extract",
                    "archive_path": _norm(archive_path),
                    "target_dir": _norm(target_dir),
                    "format": fmt,
                    "total_entries": extracted,
                    "skipped_entries": skipped if not conflicts else 0,
                    "overwrite": overwrite,
                    "extracted_files": extracted_files[:100],
                },
            }
        except (zipfile.BadZipFile, tarfile.TarError, Exception) as e:
            raise ApiError(f"Extraction failed: {e}", status_code=400, error_code="FS_004")

    @staticmethod
    def _create(archive_path: str, fmt: str, target_dir: str,
                files_to_add: Optional[List[str]], compression: int, overwrite: bool) -> Dict[str, Any]:
        if os.path.exists(archive_path) and not overwrite:
            raise ApiError(
                f"Archive already exists: {archive_path}. Set overwrite=true to overwrite.",
                status_code=409,
                error_code="FS_004",
            )

        sources: List[str] = []
        if files_to_add:
            sources = files_to_add
        elif target_dir:
            sources = [target_dir]
        else:
            raise ApiError("Either target_dir or files_to_add is required for create", status_code=400, error_code="FS_004")

        resolved_sources = [str(Path(s).resolve()) for s in sources]
        abs_archive = str(Path(archive_path).resolve())
        total_added = 0
        total_uncompressed = 0

        parent = Path(archive_path).parent
        os.makedirs(str(parent), exist_ok=True)

        def _iter_files():
            for src in resolved_sources:
                src_path = Path(src)
                if src_path.is_dir():
                    for fp in src_path.rglob("*"):
                        if fp.is_file() and str(fp.resolve()) != abs_archive:
                            yield fp, str(fp.relative_to(src_path.parent))
                elif src_path.is_file():
                    if str(src_path.resolve()) != abs_archive:
                        yield src_path, src_path.name

        try:
            if fmt == "zip":
                compression_level = max(0, min(9, compression))
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=compression_level) as zf:
                    for file_path, arcname in _iter_files():
                        zf.write(str(file_path), arcname)
                        total_added += 1
                        total_uncompressed += file_path.stat().st_size
                compressed = os.path.getsize(archive_path)
            else:
                mode_map = {
                    "tar": "w:",
                    "tar.gz": "w:gz",
                    "tar.bz2": "w:bz2",
                    "tar.xz": "w:xz",
                }
                mode = mode_map.get(fmt, "w:")
                with tarfile.open(archive_path, mode) as tf:
                    for file_path, arcname in _iter_files():
                        tf.add(str(file_path), arcname)
                        total_added += 1
                        total_uncompressed += file_path.stat().st_size
                compressed = os.path.getsize(archive_path)

            compression_ratio = round(total_uncompressed / compressed, 2) if compressed else None
            size_change_pct = round((compressed - total_uncompressed) / total_uncompressed * 100, 1) if total_uncompressed else 0
            return {
                "status_code": 200,
                "message": f"Archive created with {total_added} files",
                "data": {
                    "operation": "archive",
                    "action": "create",
                    "archive_path": _norm(archive_path),
                    "format": fmt,
                    "total_files_added": total_added,
                    "total_compressed_size_bytes": compressed,
                    "total_uncompressed_size_bytes": total_uncompressed,
                    "compression_ratio": compression_ratio,
                    "size_change_percent": size_change_pct,
                },
            }
        except Exception as e:
            raise ApiError(f"Archive creation failed: {e}", status_code=400, error_code="FS_004")

    @staticmethod
    def _dry_run_extract(archive_path: str, fmt: str, target_dir: str) -> Dict[str, Any]:
        if not os.path.isfile(archive_path):
            raise ApiError(f"Archive not found: {archive_path}", status_code=404, error_code="FS_004")

        entries: List[str] = []
        total_estimated_size = 0
        file_types: Dict[str, int] = {}
        try:
            if fmt == "zip":
                with zipfile.ZipFile(archive_path, "r") as zf:
                    for info in zf.infolist():
                        entries.append(info.filename)
                        if not info.filename.endswith("/"):
                            total_estimated_size += info.file_size
                            ext = Path(info.filename).suffix.lower()
                            file_types[ext] = file_types.get(ext, 0) + 1
            else:
                mode_map = {"tar": "r:", "tar.gz": "r:gz", "tar.bz2": "r:bz2", "tar.xz": "r:xz"}
                mode = mode_map.get(fmt, "r:")
                with tarfile.open(archive_path, mode) as tf:
                    for info in tf.getmembers():
                        entries.append(info.name)
                        if info.isfile():
                            total_estimated_size += info.size
                            ext = Path(info.name).suffix.lower()
                            file_types[ext] = file_types.get(ext, 0) + 1
        except Exception:
            pass

        return {
            "status_code": 200,
            "message": f"DRY RUN: would extract {len(entries)} entries to {_norm(target_dir)}",
            "data": {
                "operation": "archive",
                "action": "extract",
                "archive_path": _norm(archive_path),
                "target_dir": _norm(target_dir),
                "format": fmt,
                "total_entries": len(entries),
                "entries_preview": entries[:50],
                "dry_run": True,
                "estimated_extracted_size_bytes": total_estimated_size,
                "file_type_breakdown": file_types,
            },
        }

    @staticmethod
    def _dry_run_create(archive_path: str, fmt: str, target_dir: str,
                        files_to_add: Optional[List[str]]) -> Dict[str, Any]:
        exists = os.path.exists(archive_path)
        sources: List[str] = files_to_add or ([target_dir] if target_dir else [])

        total_estimated_uncompressed = 0
        file_count = 0
        file_types: Dict[str, int] = {}

        def _iter_files():
            for src in sources:
                src_path = Path(src)
                if src_path.is_dir():
                    for fp in src_path.rglob("*"):
                        if fp.is_file():
                            yield fp
                elif src_path.is_file():
                    yield src_path

        for fp in _iter_files():
            try:
                sz = fp.stat().st_size
                total_estimated_uncompressed += sz
                file_count += 1
                ext = fp.suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
            except OSError:
                pass

        compression_estimates = {"zip": 0.6, "tar": 1.0, "tar.gz": 0.5, "tar.bz2": 0.4, "tar.xz": 0.35}
        estimated_compression = compression_estimates.get(fmt, 0.6)
        estimated_compressed = int(total_estimated_uncompressed * estimated_compression)

        return {
            "status_code": 200,
            "message": f"DRY RUN: would create {fmt} archive with {file_count} files",
            "data": {
                "operation": "archive",
                "action": "create",
                "archive_path": _norm(archive_path),
                "format": fmt,
                "estimated_files_to_add": file_count,
                "estimated_uncompressed_size_bytes": total_estimated_uncompressed,
                "estimated_compressed_size_bytes": estimated_compressed,
                "estimated_compression_ratio": estimated_compression,
                "file_type_breakdown": file_types,
                "archive_exists": exists,
                "dry_run": True,
            },
        }
