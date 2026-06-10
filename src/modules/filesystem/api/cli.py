from __future__ import annotations
import argparse
import asyncio
import fnmatch
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict

DOMAIN = "filesystem"
ALIASES = ["fs"]


# ── Helpers ──────────────────────────────────────────────────────────

def output(data: Any, pretty: bool = True) -> None:
    """Print JSON to stdout as UTF-8 bytes (avoids Windows cp1252 issues)."""
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    text = json.dumps(data, **kwargs, default=str)
    buf = sys.stdout.buffer
    buf.write(text.encode("utf-8", errors="replace"))
    buf.write(b"\n")
    buf.flush()


def ok(message: str, data: Any = None) -> Dict[str, Any]:
    return {"success": True, "status_code": 200, "message": message, "data": data}


def err(message: str, code: str = "CLI_ERROR", status: int = 400) -> Dict[str, Any]:
    return {"success": False, "status_code": status, "message": message, "data": None, "error_code": code}


# ── Async Runner ──────────────────────────────────────────────────────────

def run_async(coro):
    """Safely run a coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


# ── Command Handlers ──────────────────────────────────────────────────

def cmd_fs_read(args_ns: argparse.Namespace) -> Dict:
    from src.modules.filesystem.adapters.reader import DiskReader
    try:
        reader = DiskReader()
        result = reader.read(str(Path(args_ns.path).resolve()))
        if "error" in result:
            return err(result["error"], "FS_READ_ERROR")
        return ok("File read successfully", result)
    except Exception as e:
        return err(f"Read failed: {e}", "FS_READ_ERROR")


def cmd_fs_write(args_ns: argparse.Namespace) -> Dict:
    from src.modules.filesystem.adapters.writer import DiskWriter
    try:
        writer = DiskWriter()
        permissions = getattr(args_ns, "permissions", None)
        params = {
            "path": str(Path(args_ns.path).resolve()),
            "content": args_ns.content,
            "encoding": getattr(args_ns, "encoding", "utf8"),
            "write_mode": getattr(args_ns, "mode", "create"),
            "create_parents": not getattr(args_ns, "no_create_parents", False),
            "backup_existing": getattr(args_ns, "backup", False),
            "atomic_write": not getattr(args_ns, "no_atomic", False),
            "permissions": int(permissions, 8) if permissions else None,
        }
        result = writer.write(params)
        if "error" in result:
            return err(result["error"], "FS_WRITE_ERROR")
        return ok("File written", result)
    except Exception as e:
        return err(f"Write failed: {e}", "FS_WRITE_ERROR")


def cmd_fs_delete(args_ns: argparse.Namespace) -> Dict:
    import shutil
    try:
        path = str(Path(args_ns.path).resolve())
        if not os.path.exists(path):
            return err(f"Path not found: {path}", "FS_DELETE_ERROR", 404)
        recursive = getattr(args_ns, "recursive", False)
        force = getattr(args_ns, "force", False)
        dry_run = getattr(args_ns, "dry_run", False)
        if dry_run:
            is_dir = os.path.isdir(path)
            return ok("[dry-run] Would delete", {
                "path": path,
                "type": "directory" if is_dir else "file",
                "recursive": recursive,
                "dry_run": True,
            })
        if os.path.isdir(path):
            if recursive:
                shutil.rmtree(path, ignore_errors=force)
            else:
                os.rmdir(path)
        else:
            os.remove(path)
        return ok("Deleted", {"path": path})
    except Exception as e:
        return err(f"Delete failed: {e}", "FS_DELETE_ERROR")


def cmd_fs_copy(args_ns: argparse.Namespace) -> Dict:
    import shutil
    try:
        src = str(Path(args_ns.src).resolve())
        dst = str(Path(args_ns.dest).resolve())
        if not os.path.exists(src):
            return err(f"Source not found: {src}", "FS_COPY_ERROR", 404)
        overwrite = getattr(args_ns, "overwrite", False)
        preserve = getattr(args_ns, "preserve", False)
        dry_run = getattr(args_ns, "dry_run", False)
        if dry_run:
            return ok("[dry-run] Would copy", {"from": src, "to": dst, "dry_run": True})
        if os.path.exists(dst) and not overwrite:
            return err(f"Destination exists: {dst}", "FS_COPY_ERROR", 409)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=overwrite,
                            copy_function=shutil.copy2 if preserve else shutil.copy)
        else:
            copy_fn = shutil.copy2 if preserve else shutil.copy
            copy_fn(src, dst)
        return ok("Copied", {"from": src, "to": dst, "preserve": preserve})
    except Exception as e:
        return err(f"Copy failed: {e}", "FS_COPY_ERROR")


def cmd_fs_move(args_ns: argparse.Namespace) -> Dict:
    import shutil
    try:
        src = str(Path(args_ns.src).resolve())
        dst = str(Path(args_ns.dest).resolve())
        if not os.path.exists(src):
            return err(f"Source not found: {src}", "FS_MOVE_ERROR", 404)
        overwrite = getattr(args_ns, "overwrite", False)
        dry_run = getattr(args_ns, "dry_run", False)
        if dry_run:
            return ok("[dry-run] Would move", {"from": src, "to": dst, "dry_run": True})
        if os.path.exists(dst) and not overwrite:
            return err(f"Destination exists: {dst}", "FS_MOVE_ERROR", 409)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        return ok("Moved", {"from": src, "to": dst})
    except Exception as e:
        return err(f"Move failed: {e}", "FS_MOVE_ERROR")


def cmd_fs_mkdir(args_ns: argparse.Namespace) -> Dict:
    import os
    try:
        path = str(Path(args_ns.path).resolve())
        mode_str = getattr(args_ns, "mode", None)
        mode = int(mode_str, 8) if mode_str else 0o777
        os.makedirs(path, mode=mode, exist_ok=getattr(args_ns, "parents", False))
        return ok("Directory created", {"path": path, "mode": oct(mode)})
    except Exception as e:
        return err(f"Mkdir failed: {e}", "FS_MKDIR_ERROR")


def cmd_fs_search(args_ns: argparse.Namespace) -> Dict:
    from src.modules.filesystem.adapters.search import DiskSearch
    try:
        exclude_raw = getattr(args_ns, "exclude", None)
        params = {
            "root_path": str(Path(args_ns.root).resolve()),
            "recursive": not getattr(args_ns, "no_recursive", False),
            "max_results": getattr(args_ns, "max_results", 100),
            "max_depth": getattr(args_ns, "max_depth", None),
            "file_pattern": getattr(args_ns, "pattern", None),
            "file_regex": getattr(args_ns, "file_regex", None),
            "content_regex": getattr(args_ns, "content", None),
            "content_regex_flags": getattr(args_ns, "content_flags", ""),
            "include_hidden": getattr(args_ns, "hidden", False),
            "follow_symlinks": getattr(args_ns, "follow_symlinks", False),
            "exclude_patterns": exclude_raw.split(",") if exclude_raw else None,
            "replace_text": getattr(args_ns, "replace", None),
            "dry_run": getattr(args_ns, "dry_run", True),
        }
        params = {k: v for k, v in params.items() if v is not None}
        result = DiskSearch().search(params)
        return ok(f"Found {len(result.get('results', result.get('files', [])))} matches", result)
    except Exception as e:
        return err(f"Search failed: {e}", "FS_SEARCH_ERROR")


def cmd_fs_list(args_ns: argparse.Namespace) -> Dict:
    import fnmatch
    path = str(Path(args_ns.path).resolve())
    if not os.path.exists(path):
        return err(f"Path not found: {path}", "FS_LIST_ERROR", 404)
    recursive = getattr(args_ns, "recursive", False)
    pattern = getattr(args_ns, "pattern", None)
    include_hidden = getattr(args_ns, "hidden", False)
    show_meta = getattr(args_ns, "meta", False)
    items = []
    if recursive:
        for root, dirs, files in os.walk(path):
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if not include_hidden and f.startswith("."):
                    continue
                if pattern and not fnmatch.fnmatch(f, pattern):
                    continue
                rel = str(Path(root).relative_to(path) / f)
                if show_meta:
                    try:
                        st = (Path(root) / f).stat()
                        items.append({"path": rel, "size": st.st_size, "mtime": st.st_mtime, "type": "file"})
                    except OSError:
                        items.append({"path": rel, "type": "file"})
                else:
                    items.append(rel)
            for d in dirs:
                rel = str(Path(root).relative_to(path) / d)
                if show_meta:
                    items.append({"path": rel, "type": "directory"})
                else:
                    items.append(rel)
    else:
        with os.scandir(path) as it:
            for e in it:
                if not include_hidden and e.name.startswith("."):
                    continue
                if pattern and not fnmatch.fnmatch(e.name, pattern):
                    continue
                if show_meta:
                    try:
                        st = e.stat()
                        items.append({"path": e.name, "size": st.st_size, "mtime": st.st_mtime,
                                       "type": "directory" if e.is_dir() else "file"})
                    except OSError:
                        items.append({"path": e.name, "type": "directory" if e.is_dir() else "file"})
                else:
                    items.append(e.name)
    return ok(f"Listed {len(items)} entries", {
        "path": path, "recursive": recursive, "items": sorted(items, key=lambda x: x["path"] if isinstance(x, dict) else x), "count": len(items),
    })


def cmd_fs_watch(args_ns: argparse.Namespace) -> Dict:
    from src.modules.filesystem.adapters.watch import DiskWatcher
    try:
        target = str(Path(args_ns.target).resolve())
        params = {
            "target": target,
            "recursive": getattr(args_ns, "recursive", True),
            "since": getattr(args_ns, "since", None),
            "include_ignored": getattr(args_ns, "include_ignored", False),
            "format": getattr(args_ns, "format", "simple"),
            "max_changes": getattr(args_ns, "max_changes", 100),
            "timeout_seconds": getattr(args_ns, "timeout", 60),
            "events": ["create", "modify", "delete", "rename", "attribute"],
        }
        result = DiskWatcher.watch(params)
        data = result.get("data", result)
        count = len(data.get("changes", [])) if isinstance(data, dict) else 0
        return ok(f"Detected {count} changes", data)
    except Exception as e:
        return err(f"Watch failed: {e}", "FS_WATCH_ERROR")


def cmd_fs_tree(args_ns: argparse.Namespace) -> Dict:
    from src.modules.filesystem.adapters.tree import DiskTree
    try:
        path = str(Path(args_ns.path).resolve())
        exclude = getattr(args_ns, "exclude", None)
        include_hidden = getattr(args_ns, "include_hidden", False)
        params = {
            "path": path,
            "max_depth": getattr(args_ns, "max_depth", 6),
            "include_hidden": include_hidden,
        }
        result = DiskTree.get_tree(params)
        tree = result.get("data", result)
        if exclude:
            import fnmatch
            def _prune(node):
                if not isinstance(node, dict):
                    return node
                if fnmatch.fnmatch(node.get("name", ""), exclude):
                    return None
                children = node.get("children", [])
                node["children"] = [c for c in (_prune(ch) for ch in children) if c is not None]
                return node
            tree = _prune(tree) or tree
        return ok("Filesystem tree", tree)
    except Exception as e:
        return err(f"Tree failed: {e}", "FS_TREE_ERROR")


def cmd_fs_usage(args_ns: argparse.Namespace) -> Dict:
    from src.modules.filesystem.adapters.df import DiskUsage
    try:
        exclude_raw = getattr(args_ns, "exclude", None)
        params = {
            "target": str(Path(args_ns.path).resolve()),
            "recursive": True,
            "depth": getattr(args_ns, "depth", 10),
            "unit": getattr(args_ns, "unit", "auto"),
            "include_hidden": getattr(args_ns, "hidden", False),
            "exclude_patterns": exclude_raw.split(",") if exclude_raw else [],
            "vcs_integration": getattr(args_ns, "vcs", "none"),
            "aggregate_by": getattr(args_ns, "aggregate_by", "file"),
            "max_items": getattr(args_ns, "max_items", 100),
        }
        result = DiskUsage.analyze(params)
        return ok("Usage analysis", result.get("data", result))
    except Exception as e:
        return err(f"Usage failed: {e}", "FS_USAGE_ERROR")


def cmd_fs_audit(args_ns: argparse.Namespace) -> Dict:
    from src.modules.filesystem.adapters.audit import DiskAudit
    try:
        severity_raw = getattr(args_ns, "severity", None)
        exclude_raw = getattr(args_ns, "exclude", None)
        params = {
            "target": str(Path(args_ns.path).resolve()),
            "recursive": not getattr(args_ns, "no_recursive", False),
            "severity": severity_raw.split(",") if severity_raw else ["critical", "high", "medium", "low"],
            "check_permissions": not getattr(args_ns, "no_permissions", False),
            "check_hidden": not getattr(args_ns, "no_hidden", False),
            "max_file_size_mb": getattr(args_ns, "max_file_size_mb", 100),
            "exclude_patterns": exclude_raw.split(",") if exclude_raw else [".git", ".svn", "node_modules"],
            "limit": getattr(args_ns, "limit", 200),
        }
        result = DiskAudit.audit(params)
        return ok("Filesystem audit", result.get("data", result))
    except Exception as e:
        return err(f"Audit failed: {e}", "FS_AUDIT_ERROR")


# ── Commands Registry ────────────────────────────────────────────────

FS_COMMANDS = {
    "read": cmd_fs_read,
    "write": cmd_fs_write,
    "delete": cmd_fs_delete,
    "copy": cmd_fs_copy,
    "move": cmd_fs_move,
    "mkdir": cmd_fs_mkdir,
    "list": cmd_fs_list,
    "search": cmd_fs_search,
    "watch": cmd_fs_watch,
    "tree": cmd_fs_tree,
    "usage": cmd_fs_usage,
    "audit": cmd_fs_audit,
}


# ── Parser ───────────────────────────────────────────────────────────

def build_parser(subparsers) -> None:
    p = subparsers.add_parser("filesystem", aliases=["fs"], help="Filesystem operations")
    sp = p.add_subparsers(dest="fs_action", required=True)

    sp.add_parser("read", help="Read a file or directory").add_argument("path", help="Path to file/dir")

    w = sp.add_parser("write", help="Write content to a file")
    w.add_argument("path", help="Path to file")
    w.add_argument("content", help="Content to write")
    w.add_argument("--mode", choices=["create", "overwrite", "append"], default="create", help="Write mode")
    w.add_argument("--encoding", choices=["utf8", "base64"], default="utf8", help="Content encoding")
    w.add_argument("--backup", action="store_true", help="Backup existing file before overwrite")
    w.add_argument("--no-atomic", action="store_true", help="Disable atomic write (temp file + rename)")
    w.add_argument("--no-create-parents", action="store_true", help="Do not create parent directories")
    w.add_argument("--permissions", help="Unix permissions in octal (e.g. 644)")

    d = sp.add_parser("delete", help="Delete a file or directory")
    d.add_argument("path", help="Path to delete")
    d.add_argument("--recursive", action="store_true", help="Recursive delete (for directories)")
    d.add_argument("--force", action="store_true", help="Force delete")
    d.add_argument("--dry-run", action="store_true", help="Preview deletion without executing")

    c = sp.add_parser("copy", help="Copy file or directory")
    c.add_argument("src", help="Source path")
    c.add_argument("dest", help="Destination path")
    c.add_argument("--overwrite", action="store_true", help="Overwrite destination")
    c.add_argument("--preserve", action="store_true", help="Preserve timestamps and permissions")
    c.add_argument("--dry-run", action="store_true", help="Preview copy without executing")

    m = sp.add_parser("move", help="Move file or directory")
    m.add_argument("src", help="Source path")
    m.add_argument("dest", help="Destination path")
    m.add_argument("--overwrite", action="store_true", help="Overwrite destination")
    m.add_argument("--dry-run", action="store_true", help="Preview move without executing")

    mk = sp.add_parser("mkdir", help="Create directory")
    mk.add_argument("path", help="Directory path")
    mk.add_argument("--parents", action="store_true", help="Create parent directories")
    mk.add_argument("--mode", help="Directory permissions in octal (e.g. 755, default: 777)")

    se = sp.add_parser("search", help="Search files by pattern and/or content")
    se.add_argument("root", help="Root path to search")
    se.add_argument("--pattern", help="File glob pattern (e.g. *.py)")
    se.add_argument("--file-regex", dest="file_regex", help="Regex pattern for filenames")
    se.add_argument("--content", help="Content regex pattern")
    se.add_argument("--content-flags", dest="content_flags", default="", help="Regex flags (e.g. 'i' for case-insensitive)")
    se.add_argument("--max-depth", type=int, help="Max directory depth")
    se.add_argument("--max-results", type=int, default=100, help="Max results")
    se.add_argument("--no-recursive", action="store_true", help="Non-recursive")
    se.add_argument("--hidden", action="store_true", help="Include hidden files")
    se.add_argument("--follow-symlinks", action="store_true", help="Follow symbolic links")
    se.add_argument("--exclude", help="Comma-separated glob patterns to exclude")
    se.add_argument("--replace", help="Replace matched content with this text")
    se.add_argument("--apply", dest="dry_run", action="store_false", default=True, help="Apply replacements (default: dry-run preview)")

    li = sp.add_parser("list", help="List directory contents")
    li.add_argument("path", help="Directory path")
    li.add_argument("--recursive", action="store_true", help="Recursive listing")
    li.add_argument("--pattern", help="File glob pattern")
    li.add_argument("--hidden", action="store_true", help="Include hidden files/dirs")
    li.add_argument("--meta", action="store_true", help="Include metadata (size, mtime, type)")

    w = sp.add_parser("watch", help="Poll filesystem for changes (VCS-aware)")
    w.add_argument("target", help="Directory to watch")
    w.add_argument("--since", help="ISO 8601 timestamp, 'git:<rev>', or 'svn:<rev>'")
    w.add_argument("--format", choices=["simple", "detailed"], default="simple", help="Output format")
    w.add_argument("--max-changes", type=int, default=100, dest="max_changes", help="Max changes to report")
    w.add_argument("--timeout", type=int, default=60, help="Scan timeout in seconds")
    w.add_argument("--include-ignored", action="store_true", help="Include VCS-ignored files")
    w.add_argument("--no-recursive", dest="recursive", action="store_false", default=True, help="Non-recursive")

    tp = sp.add_parser("tree", help="Show directory tree")
    tp.add_argument("path", help="Path")
    tp.add_argument("--max-depth", type=int, default=6, help="Maximum traversal depth")
    tp.add_argument("--exclude", help="Exclude pattern (glob)")
    tp.add_argument("--hidden", dest="include_hidden", action="store_true", help="Include hidden files/dirs")

    up = sp.add_parser("usage", help="Analyze disk usage with optional VCS integration")
    up.add_argument("path", help="Path")
    up.add_argument("--unit", choices=["bytes", "kb", "mb", "gb", "auto"], default="auto", help="Size unit")
    up.add_argument("--depth", type=int, default=10, help="Max subdirectory depth")
    up.add_argument("--vcs", choices=["none", "git", "svn"], default="none", help="VCS integration")
    up.add_argument("--aggregate-by", choices=["file", "extension", "vcs_status"], default="file", dest="aggregate_by", help="Aggregation mode")
    up.add_argument("--max-items", type=int, default=100, dest="max_items", help="Max items to report")
    up.add_argument("--hidden", action="store_true", help="Include hidden files")
    up.add_argument("--exclude", help="Comma-separated glob patterns to exclude")

    ap = sp.add_parser("audit", help="Filesystem security audit")
    ap.add_argument("path", help="Path")
    ap.add_argument("--severity", help="Comma-separated severity levels (critical,high,medium,low)")
    ap.add_argument("--no-recursive", action="store_true", help="Non-recursive scan")
    ap.add_argument("--no-permissions", action="store_true", help="Skip permission checks")
    ap.add_argument("--no-hidden", action="store_true", help="Exclude hidden files from audit")
    ap.add_argument("--max-file-size-mb", type=int, default=100, dest="max_file_size_mb", help="Max file size to inspect (MB)")
    ap.add_argument("--exclude", help="Comma-separated glob patterns to exclude")
    ap.add_argument("--limit", type=int, default=200, help="Max findings to report")
