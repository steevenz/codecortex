"""
Df.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Df
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import os
import subprocess
import fnmatch
from collections import defaultdict

from src.core import ApiError

from src.core.utils.path import norm_path as _norm


def _format_size(size_bytes: int, unit: str) -> Tuple[float, str]:
    if unit == "bytes":
        return float(size_bytes), "bytes"
    if unit == "kb":
        return size_bytes / 1024, "kb"
    if unit == "mb":
        return size_bytes / (1024 * 1024), "mb"
    if unit == "gb":
        return size_bytes / (1024 * 1024 * 1024), "gb"
    if unit == "auto":
        if size_bytes < 1024:
            return float(size_bytes), "bytes"
        elif size_bytes < 1024 * 1024:
            return size_bytes / 1024, "kb"
        elif size_bytes < 1024 * 1024 * 1024:
            return size_bytes / (1024 * 1024), "mb"
        else:
            return size_bytes / (1024 * 1024 * 1024), "gb"
    return float(size_bytes), "bytes"


def _should_exclude(rel_path: str, exclude_patterns: List[str]) -> bool:
    if not exclude_patterns:
        return False
    for pat in exclude_patterns:
        p = pat.replace("\\", "/")
        if fnmatch.fnmatch(rel_path, p) or fnmatch.fnmatch(rel_path, p + "/*"):
            return True
        if "/" not in p and ("/" + p) in rel_path:
            continue
    return False


class DiskUsage:
    """Disk usage analyzer with VCS integration for Git and SVN."""

    @classmethod
    def analyze(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get("target", "")
        recursive = params.get("recursive", True)
        depth = params.get("depth")
        unit = params.get("unit", "auto")
        include_hidden = params.get("include_hidden", False)
        exclude_patterns = params.get("exclude_patterns") or []
        vcs_integration = params.get("vcs_integration", "none")
        aggregate_by = params.get("aggregate_by", "file")
        max_items = min(params.get("max_items", 100), 5000)

        target_path = Path(target).resolve()
        if not target_path.exists():
            raise ApiError(f"Target path does not exist: {target}", status_code=404, error_code="FS_007")

        if target_path.is_file():
            st = target_path.stat()
            size_val, unit_used = _format_size(st.st_size, unit)
            key = f"size_{unit_used}"
            return {
                "status_code": 200,
                "message": "Disk usage calculated",
                "data": {
                    "target": _norm(str(target_path)),
                    "type": "file",
                    "recursive": False,
                    "unit": unit_used,
                    "total_size": round(size_val, 2),
                    key: round(size_val, 2),
                    "total_items": 1,
                    "breakdown": [{"path": _norm(str(target_path)), "type": "file", key: round(size_val, 2), "items": 1}],
                },
            }

        vcs_mode = vcs_integration if vcs_integration in ("git", "svn") else None

        if vcs_mode == "git":
            result = cls._analyze_git(target_path, unit, include_hidden, exclude_patterns, aggregate_by, max_items)
            result["target"] = _norm(str(target_path))
            result["vcs"] = "git"
            result["recursive"] = recursive
            result["depth"] = depth
            return {
                "status_code": 200,
                "message": "Disk usage with Git analysis",
                "data": result,
            }

        if vcs_mode == "svn":
            result = cls._analyze_svn(target_path, unit, include_hidden, exclude_patterns, aggregate_by, max_items)
            result["target"] = _norm(str(target_path))
            result["vcs"] = "svn"
            result["recursive"] = recursive
            result["depth"] = depth
            return {
                "status_code": 200,
                "message": "Disk usage with SVN analysis",
                "data": result,
            }

        result = cls._analyze_fs(target_path, recursive, depth, unit, include_hidden, exclude_patterns, aggregate_by, max_items)
        result["target"] = _norm(str(target_path))
        result["recursive"] = recursive
        result["depth"] = depth
        return {
            "status_code": 200,
            "message": "Disk usage calculated",
            "data": result,
        }

    @classmethod
    def _analyze_fs(cls, target: Path, recursive: bool, depth: Optional[int],
                    unit: str, include_hidden: bool, exclude_patterns: List[str],
                    aggregate_by: str, max_items: int) -> Dict[str, Any]:
        extension_sizes: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))

        def _walk(path: Path, current_depth: int = 0) -> Tuple[List[Dict[str, Any]], int, int]:
            local_entries: List[Dict[str, Any]] = []
            local_size = 0
            local_count = 0
            if depth is not None and current_depth > depth:
                return local_entries, local_size, local_count
            try:
                for entry in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name)):
                    if not include_hidden and entry.name.startswith("."):
                        continue
                    rel = _norm(str(entry.relative_to(target)))
                    if _should_exclude(rel, exclude_patterns):
                        continue
                    if entry.is_dir():
                        if recursive:
                            sub_entries, sub_size, sub_count = _walk(entry, current_depth + 1)
                            size_val, unit_used = _format_size(sub_size, unit)
                            key = f"size_{unit_used}"
                            local_entries.append({
                                "path": rel + "/",
                                "type": "directory",
                                key: round(size_val, 2),
                                "items": sub_count,
                            })
                            local_entries.extend(sub_entries)
                            local_size += sub_size
                            local_count += sub_count
                    elif entry.is_file():
                        try:
                            sz = entry.stat().st_size
                        except OSError:
                            sz = 0
                        local_size += sz
                        local_count += 1
                        ext = entry.suffix.lower() or "(no extension)"
                        cur_size, cur_count = extension_sizes[ext]
                        extension_sizes[ext] = (cur_size + sz, cur_count + 1)
                        size_val, unit_used = _format_size(sz, unit)
                        key = f"size_{unit_used}"
                        local_entries.append({
                            "path": rel,
                            "type": "file",
                            key: round(size_val, 2),
                            "items": 1,
                        })
            except PermissionError:
                pass
            return local_entries, local_size, local_count

        entries, total_size, total_items = _walk(target)

        total_val, unit_used = _format_size(total_size, unit)
        total_key = f"total_size_{unit_used}"
        size_key = f"size_{unit_used}"

        data: Dict[str, Any] = {
            "unit": unit_used,
            total_key: round(total_val, 2),
            "total_items": total_items,
        }

        if aggregate_by == "extension":
            ext_list = [
                {"extension": ext, size_key: round(sz / (1024**["bytes", "kb", "mb", "gb", "auto"].index(unit_used) if unit_used in ("bytes", "kb", "mb", "gb") else 2), 2), "files": cnt, "percentage": round(sz / total_size * 100, 1) if total_size else 0}
                for ext, (sz, cnt) in sorted(extension_sizes.items(), key=lambda x: x[1][0], reverse=True)[:max_items]
            ]
            data["aggregate_by"] = "extension"
            data["breakdown"] = ext_list
        else:
            sorted_entries = sorted(entries, key=lambda e: e.get(size_key, 0), reverse=True)[:max_items]
            data["breakdown"] = sorted_entries

        import mimetypes
        largest = sorted(entries, key=lambda e: e.get(size_key, 0), reverse=True)[:min(10, max_items)]
        total_val_for_pct = data.get(total_key, 0)
        data["largest_files"] = [
            {
                "path": e["path"],
                size_key: e[size_key],
                "file_type": (mimetypes.guess_type(e["path"])[0] or "application/octet-stream"),
                "percentage_of_total": round(e[size_key] / total_val_for_pct * 100, 1) if total_val_for_pct else 0,
            }
            for e in largest if e["type"] == "file"
        ]

        return data

    @classmethod
    def _analyze_git(cls, target: Path, unit: str, include_hidden: bool,
                     exclude_patterns: List[str], aggregate_by: str, max_items: int) -> Dict[str, Any]:
        from src.modules.filesystem.adapters.git import DiskGit

        git_root = DiskGit.find_root(target)
        if not git_root:
            return {"vcs": "git", "error": "Not a git repository"}

        cwd = str(git_root)
        tracked: List[Path] = []
        untracked: List[Path] = []
        ignored: List[Path] = []

        try:
            ls_files = subprocess.run(
                ["git", "ls-files"],
                cwd=cwd, capture_output=True, text=True, timeout=30,
            )
            if ls_files.returncode == 0:
                for line in ls_files.stdout.splitlines():
                    p = (git_root / line).resolve()
                    if p.exists():
                        tracked.append(p)
        except Exception:
            pass

        try:
            untracked_proc = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=cwd, capture_output=True, text=True, timeout=30,
            )
            if untracked_proc.returncode == 0:
                for line in untracked_proc.stdout.splitlines():
                    p = (git_root / line).resolve()
                    if p.exists():
                        untracked.append(p)
        except Exception:
            pass

        try:
            ignored_proc = subprocess.run(
                ["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
                cwd=cwd, capture_output=True, text=True, timeout=30,
            )
            if ignored_proc.returncode == 0:
                for line in ignored_proc.stdout.splitlines():
                    p = (git_root / line).resolve()
                    if p.exists() and p not in untracked:
                        ignored.append(p)
        except Exception:
            pass

        branch = ""
        commit = ""
        try:
            br = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=cwd, capture_output=True, text=True, timeout=5,
            )
            if br.returncode == 0:
                branch = br.stdout.strip()
            co = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=cwd, capture_output=True, text=True, timeout=5,
            )
            if co.returncode == 0:
                commit = co.stdout.strip()
        except Exception:
            pass

        return cls._compute_vcs_breakdown(
            target, git_root, unit, include_hidden, exclude_patterns,
            aggregate_by, max_items, tracked, untracked, ignored,
            branch=branch, commit=commit,
        )

    @classmethod
    def _analyze_svn(cls, target: Path, unit: str, include_hidden: bool,
                     exclude_patterns: List[str], aggregate_by: str, max_items: int) -> Dict[str, Any]:
        from src.modules.filesystem.adapters.svn import DiskSvn

        svn_root = DiskSvn.find_root(target)
        if not svn_root:
            return {"vcs": "svn", "error": "Not an SVN working copy"}

        cwd = str(svn_root)
        versioned: List[Path] = []
        unversioned: List[Path] = []
        ignored: List[Path] = []

        try:
            stat_proc = subprocess.run(
                ["svn", "status", "--no-ignore", "--non-interactive"],
                cwd=cwd, capture_output=True, text=True, timeout=30,
            )
            if stat_proc.returncode == 0:
                for line in stat_proc.stdout.splitlines():
                    line = line.strip()
                    if not line or len(line) < 8:
                        continue
                    sc = line[0]
                    fp = line[7:].strip()
                    p = (svn_root / fp).resolve()
                    if not p.exists():
                        continue
                    if sc == " " or sc == "M" or sc == "A" or sc == "D" or sc == "R" or sc == "C":
                        versioned.append(p)
                    elif sc == "?":
                        unversioned.append(p)
                    elif sc == "I":
                        ignored.append(p)
                    elif sc == "!":
                        versioned.append(p)
                    else:
                        versioned.append(p)
        except Exception:
            pass

        url = ""
        revision = ""
        try:
            info = subprocess.run(
                ["svn", "info", "--show-item", "url"],
                cwd=cwd, capture_output=True, text=True, timeout=5,
            )
            if info.returncode == 0:
                url = info.stdout.strip()
            rev = subprocess.run(
                ["svn", "info", "--show-item", "revision"],
                cwd=cwd, capture_output=True, text=True, timeout=5,
            )
            if rev.returncode == 0:
                revision = rev.stdout.strip()
        except Exception:
            pass

        return cls._compute_vcs_breakdown(
            target, svn_root, unit, include_hidden, exclude_patterns,
            aggregate_by, max_items, versioned, unversioned, ignored,
            url=url, revision=revision,
        )

    @classmethod
    def _compute_vcs_breakdown(
        cls, target: Path, vcs_root: Path, unit: str, include_hidden: bool,
        exclude_patterns: List[str], aggregate_by: str, max_items: int,
        tracked: List[Path], untracked: List[Path], ignored: List[Path],
        **extra: str,
    ) -> Dict[str, Any]:
        target_rel = target.resolve()
        vcs_root_str = str(vcs_root)

        def _filter(paths: List[Path]) -> List[Path]:
            result = []
            for p in paths:
                p_str = str(p)
                if not p_str.startswith(vcs_root_str):
                    continue
                if not include_hidden and os.path.basename(p_str).startswith("."):
                    continue
                rel = _norm(os.path.relpath(p_str, vcs_root_str))
                if _should_exclude(rel, exclude_patterns):
                    continue
                result.append(p)
            return result

        tracked = _filter(tracked)
        untracked = _filter(untracked)
        ignored = _filter(ignored)

        def _calc(paths: List[Path]) -> Tuple[int, int]:
            total = 0
            count = 0
            for p in paths:
                try:
                    total += p.stat().st_size
                    count += 1
                except OSError:
                    pass
            return total, count

        tracked_size, tracked_count = _calc(tracked)
        untracked_size, untracked_count = _calc(untracked)
        ignored_size, ignored_count = _calc(ignored)

        total_size = tracked_size + untracked_size + ignored_size
        total_items = tracked_count + untracked_count + ignored_count

        total_val, unit_used = _format_size(total_size, unit)
        tracked_val, _ = _format_size(tracked_size, unit)
        untracked_val, _ = _format_size(untracked_size, unit)
        ignored_val, _ = _format_size(ignored_size, unit)

        size_key = f"size_{unit_used}"

        data: Dict[str, Any] = {
            **extra,
            "unit": unit_used,
            f"total_size_{unit_used}": round(total_val, 2),
            "total_items": total_items,
            "vcs_breakdown": {
                "tracked": {size_key: round(tracked_val, 2), "files": tracked_count},
                "untracked": {size_key: round(untracked_val, 2), "files": untracked_count},
                "ignored": {size_key: round(ignored_val, 2), "files": ignored_count},
            },
        }

        if aggregate_by == "vcs_status":
            cat_map = [
                ("tracked", tracked, tracked_val),
                ("untracked", untracked, untracked_val),
                ("ignored", ignored, ignored_val),
            ]
            details = []
            for status, paths, _ in cat_map:
                sub_total = 0
                sub_count = 0
                dir_sizes: Dict[str, int] = {}
                for p in paths:
                    try:
                        sz = p.stat().st_size
                        sub_total += sz
                        sub_count += 1
                        parent = _norm(os.path.relpath(str(p.parent), vcs_root_str))
                        dir_sizes[parent] = dir_sizes.get(parent, 0) + sz
                    except OSError:
                        pass
                top_dirs = sorted(dir_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
                for d, sz in top_dirs:
                    dv, _ = _format_size(sz, unit)
                    details.append({"status": status, "path": d + "/", size_key: round(dv, 2)})
                sv, _ = _format_size(sub_total, unit)
                for p in sorted(paths, key=lambda x: x.stat().st_size if x.exists() else 0, reverse=True)[:3]:
                    try:
                        sz = p.stat().st_size
                        pv, _ = _format_size(sz, unit)
                        if not any(d["path"] == _norm(os.path.relpath(str(p), vcs_root_str)) for d in details):
                            details.append({"status": status, "path": _norm(os.path.relpath(str(p), vcs_root_str)), size_key: round(pv, 2)})
                    except OSError:
                        pass
            data["details"] = details[:max_items]

            if untracked_count > 0:
                data["suggestion"] = (
                    f"Untracked files consume {round(untracked_val, 2)} {unit_used}. "
                    f"Consider adding to .gitignore or committing."
                )

        elif aggregate_by == "extension":
            ext_sizes: Dict[str, Tuple[int, int, str]] = defaultdict(lambda: (0, 0, ""))
            for status, paths, _ in [("tracked", tracked, tracked_val), ("untracked", untracked, untracked_val), ("ignored", ignored, ignored_val)]:
                for p in paths:
                    try:
                        sz = p.stat().st_size
                        ext = p.suffix.lower() or "(no extension)"
                        cur_sz, cur_cnt, cur_st = ext_sizes[ext]
                        ext_sizes[ext] = (cur_sz + sz, cur_cnt + 1, cur_st or status)
                    except OSError:
                        pass
            ext_list = [
                {"extension": ext, size_key: round(sz / (1024**["bytes", "kb", "mb", "gb"].index(unit_used) if unit_used in ("bytes", "kb", "mb", "gb") else 1), 2), "files": cnt, "percentage": round(sz / total_size * 100, 1) if total_size else 0}
                for ext, (sz, cnt, _) in sorted(ext_sizes.items(), key=lambda x: x[1][0], reverse=True)[:max_items]
            ]
            data["aggregate_by"] = "extension"
            data["breakdown"] = ext_list
        else:
            all_items: List[Dict[str, Any]] = []
            status_map = defaultdict(set)
            for p in tracked:
                status_map[str(p)].add("tracked")
            for p in untracked:
                status_map[str(p)].add("untracked")
            for p in ignored:
                status_map[str(p)].add("ignored")
            seen_dirs: set = set()
            for paths, status in [(tracked, "tracked"), (untracked, "untracked"), (ignored, "ignored")]:
                for p in paths:
                    try:
                        sz = p.stat().st_size
                        sv, _ = _format_size(sz, unit)
                        rel = _norm(os.path.relpath(str(p), vcs_root_str))
                        all_items.append({
                            "path": rel,
                            "status": status,
                            size_key: round(sv, 2),
                        })
                    except OSError:
                        pass
            sorted_items = sorted(all_items, key=lambda x: x.get(size_key, 0), reverse=True)[:max_items]
            data["breakdown"] = sorted_items

        import mimetypes as _mt
        total_val_for_pct = data.get(f"total_size_{unit_used}", 0)
        all_paths = [(str(p), p) for p in tracked + untracked + ignored]
        largest_raw = sorted(all_paths, key=lambda x: x[1].stat().st_size if x[1].exists() else 0, reverse=True)[:min(10, max_items)]
        data["largest_files"] = []
        for rel_path, p in largest_raw:
            try:
                sz = p.stat().st_size
                sv, _ = _format_size(sz, unit)
                rel = _norm(os.path.relpath(str(p), vcs_root_str))
                pct = round(sv / total_val_for_pct * 100, 1) if total_val_for_pct else 0
                data["largest_files"].append({
                    "path": rel,
                    size_key: round(sv, 2),
                    "file_type": (_mt.guess_type(str(p))[0] or "application/octet-stream"),
                    "percentage_of_total": pct,
                })
            except OSError:
                pass

        return data
