"""
CodeCortex CLI — Codelogs domain (log management, search, discovery, graph).

Usage:
  codecortex log scan [--path <project_root>] [--search-paths <csv>]
  codecortex log search <query> [--level ERROR] [--date-from <iso>]
  codecortex log graph [--days 7] [--mode error-frequency|time-trend|summary|anomalies|files|health]
  codecortex log discover [--search-paths <csv>] [--no-lang-detect] [--no-os-detect]
  codecortex log cleanup [--days 30] [--apply]
  codecortex log rotate [--max-size 50] [--keep 5] [--apply]
  codecortex log validate <path_to_log_file>

:project: CodeCortex
:package: Codelogs.Api.CLI
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Codelogs-v2.0
"""
from __future__ import annotations

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional

DOMAIN = "log"
ALIASES = ["logs", "logging"]
LOG_COMMANDS: Dict[str, Any] = {}


def output(data: Any, pretty: bool = True) -> None:
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


def _get_service(path: str) -> Any:
    from src.modules.codelogs.services.log_service import LogService
    svc = LogService()
    if path:
        svc.set_project_root(path)
    elif os.environ.get("CODECORTEX_PROJECT_ROOT"):
        svc.set_project_root(os.environ["CODECORTEX_PROJECT_ROOT"])
    elif _find_project_root():
        svc.set_project_root(_find_project_root())
    return svc


def _get_graph_service(path: str) -> Any:
    from src.modules.codelogs.services.loggraph_service import LogGraphService
    svc = LogGraphService()
    if path:
        svc.log_service.set_project_root(path)
    elif os.environ.get("CODECORTEX_PROJECT_ROOT"):
        svc.log_service.set_project_root(os.environ["CODECORTEX_PROJECT_ROOT"])
    elif _find_project_root():
        svc.log_service.set_project_root(_find_project_root())
    return svc


def _find_project_root() -> Optional[str]:
    cwd = os.getcwd()
    for parent in [cwd] + [os.path.dirname(cwd)]:
        if os.path.isdir(os.path.join(parent, "logs")) or os.path.isdir(os.path.join(parent, "outputs", "logs")):
            return parent
    return None


def cmd_scan(args_ns: argparse.Namespace) -> Dict[str, Any]:
    path = getattr(args_ns, "path", None) or getattr(args_ns, "log_path", None)
    search_paths = getattr(args_ns, "search_paths", None)
    try:
        svc = _get_service(path)
        files = svc.scan_logs(search_paths=search_paths)
        auto_indexed = svc._auto_index_attempted and bool(svc._auto_discovered_roots)
        info = {
            "total_files": len(files),
            "project_root": svc._project_root,
            "files": files,
        }
        if auto_indexed:
            info["auto_indexed"] = True
            info["auto_discovered_roots"] = svc._auto_discovered_roots
        return ok(f"Found {len(files)} log files" + (" (auto-indexed)" if auto_indexed else ""), info)
    except Exception as e:
        return err(str(e), "CODELOGS_SCAN_ERROR")


def cmd_search(args_ns: argparse.Namespace) -> Dict[str, Any]:
    from src.modules.codelogs.services.log_service import LogSearchFilter
    path = getattr(args_ns, "path", None) or getattr(args_ns, "log_path", None)
    search_paths = getattr(args_ns, "search_paths", None)
    query = getattr(args_ns, "query", None)
    if not query:
        return err("query is required", "CODELOGS_400")
    try:
        svc = _get_service(path)
        levels = getattr(args_ns, "level", None)
        level_list = levels.split(",") if levels else None
        filt = LogSearchFilter(
            query=query,
            log_levels=level_list,
            date_from=getattr(args_ns, "date_from", None),
            date_to=getattr(args_ns, "date_to", None),
            file_pattern=getattr(args_ns, "file_pattern", "*.log"),
            max_results=getattr(args_ns, "max_results", 50),
            offset=getattr(args_ns, "offset", 0),
        )
        entries = svc.search(filt, search_paths=search_paths)
        auto_indexed = svc._auto_index_attempted and bool(svc._auto_discovered_roots)
        info = {
            "total_results": len(entries),
            "entries": [e.to_dict() for e in entries],
        }
        if auto_indexed:
            info["auto_indexed"] = True
            info["auto_discovered_roots"] = svc._auto_discovered_roots
        return ok(f"Found {len(entries)} log entries" + (" (auto-indexed)" if auto_indexed else ""), info)
    except Exception as e:
        return err(str(e), "CODELOGS_SEARCH_ERROR")


def cmd_graph(args_ns: argparse.Namespace) -> Dict[str, Any]:
    path = getattr(args_ns, "path", None) or getattr(args_ns, "log_path", None)
    search_paths = getattr(args_ns, "search_paths", None)
    mode = getattr(args_ns, "mode", "summary")
    days = getattr(args_ns, "days", 7)
    file_pat = getattr(args_ns, "file_pattern", "*.log")
    max_files = getattr(args_ns, "max_files", 50)
    try:
        svc = _get_graph_service(path)
        kwargs: Dict[str, Any] = dict(days=days, file_pattern=file_pat,
                                       max_files=max_files, search_paths=search_paths)

        mode_map = {
            "error-frequency": lambda: svc.error_frequency(**kwargs),
            "time-trend": lambda: svc.time_trend(
                **kwargs, granularity=getattr(args_ns, "granularity", "hourly")),
            "summary": lambda: svc.summary(**kwargs),
            "anomalies": lambda: svc.anomalies(**kwargs),
            "files": lambda: svc.files(**kwargs),
            "health": lambda: svc.health(**kwargs),
        }

        handler = mode_map.get(mode, mode_map["summary"])
        data = handler()
        return ok(f"Log graph data for last {days} days (mode: {mode})", data)
    except Exception as e:
        return err(str(e), "CODELOGS_GRAPH_ERROR")


def cmd_discover(args_ns: argparse.Namespace) -> Dict[str, Any]:
    """Discover log files across all detected paths using systematic collection."""
    path = getattr(args_ns, "path", None) or getattr(args_ns, "log_path", None)
    search_paths = getattr(args_ns, "search_paths", None)
    max_results = getattr(args_ns, "max_results", 200)
    detect_lang = not getattr(args_ns, "no_lang_detect", False)
    detect_os = not getattr(args_ns, "no_os_detect", False)
    detect_servers = not getattr(args_ns, "no_server_detect", False)
    detect_databases = not getattr(args_ns, "no_db_detect", False)
    detect_dev_tools = not getattr(args_ns, "no_dev_tool_detect", False)
    try:
        svc = _get_graph_service(path)
        data = svc.discover(
            custom_paths=search_paths,
            detect_language=detect_lang,
            detect_os=detect_os,
            detect_servers=detect_servers,
            detect_databases=detect_databases,
            detect_dev_tools=detect_dev_tools,
            max_results=max_results,
        )
        return ok(f"Discovered {data.get('total_files', 0)} log files", data)
    except Exception as e:
        return err(str(e), "CODELOGS_DISCOVER_ERROR")


def cmd_cleanup(args_ns: argparse.Namespace) -> Dict[str, Any]:
    path = getattr(args_ns, "path", None) or getattr(args_ns, "log_path", None)
    search_paths = getattr(args_ns, "search_paths", None)
    days = getattr(args_ns, "days", 30)
    dry_run = not getattr(args_ns, "apply", False)
    try:
        svc = _get_service(path)
        result = svc.cleanup(days=days, dry_run=dry_run, search_paths=search_paths)
        return ok(result["message"], result)
    except Exception as e:
        return err(str(e), "CODELOGS_CLEANUP_ERROR")


def cmd_rotate(args_ns: argparse.Namespace) -> Dict[str, Any]:
    path = getattr(args_ns, "path", None) or getattr(args_ns, "log_path", None)
    max_size = getattr(args_ns, "max_size", 50)
    keep = getattr(args_ns, "keep", 5)
    dry_run = not getattr(args_ns, "apply", False)
    try:
        svc = _get_service(path)
        result = svc.rotate(max_size_mb=max_size, keep=keep, dry_run=dry_run)
        return ok(result["message"], result)
    except Exception as e:
        return err(str(e), "CODELOGS_ROTATE_ERROR")


def cmd_validate(args_ns: argparse.Namespace) -> Dict[str, Any]:
    path = getattr(args_ns, "path", None) or getattr(args_ns, "log_path", None)
    fpath = getattr(args_ns, "file", None)
    if not fpath:
        return err("file path is required", "CODELOGS_400")
    try:
        svc = _get_service(path)
        result = svc.validate(fpath)
        return ok("Validation complete" if result["valid"] else "Validation failed", result)
    except Exception as e:
        return err(str(e), "CODELOGS_VALIDATE_ERROR")


def cmd_info(args_ns: argparse.Namespace) -> Dict[str, Any]:
    path = getattr(args_ns, "path", None) or getattr(args_ns, "log_path", None)
    try:
        svc = _get_service(path)
        roots = svc._get_log_roots()
        collector = svc.path_collector
        langs = collector._detect_languages() if svc._project_root else []
        servers = collector._detect_servers() if svc._project_root else []
        databases = collector._detect_databases() if svc._project_root else []
        return ok("Log system info", {
            "project_root": svc._project_root,
            "allowed_log_roots": list(svc.ALLOWED_LOG_ROOTS),
            "active_roots": roots,
            "detected_languages": langs,
            "detected_servers": servers,
            "detected_databases": databases,
            "operating_system": collector._detect_os(),
        })
    except Exception as e:
        return err(str(e), "CODELOGS_INFO_ERROR")


LOG_COMMANDS["scan"] = cmd_scan
LOG_COMMANDS["search"] = cmd_search
LOG_COMMANDS["graph"] = cmd_graph
LOG_COMMANDS["discover"] = cmd_discover
LOG_COMMANDS["cleanup"] = cmd_cleanup
LOG_COMMANDS["rotate"] = cmd_rotate
LOG_COMMANDS["validate"] = cmd_validate
LOG_COMMANDS["info"] = cmd_info


def build_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "log", aliases=["logs", "logging"],
        help="Log management — scan, search, visualize, discover, cleanup, rotate, validate",
    )
    sp = p.add_subparsers(dest="log_action", required=True)

    # scan
    scan_p = sp.add_parser("scan", help="Scan log directories for files")
    scan_p.add_argument("--path", "-p", dest="path", help="Project root path")
    scan_p.add_argument("--log-path", dest="log_path", help="Alias for --path")
    scan_p.add_argument("--search-paths", dest="search_paths",
                        help="Comma-separated additional paths to scan for logs")

    # search
    search_p = sp.add_parser("search", help="Search log entries with filters")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--level", "-l", help="Comma-separated log levels (ERROR, WARN, INFO, DEBUG)")
    search_p.add_argument("--date-from", dest="date_from", help="Start date (ISO format)")
    search_p.add_argument("--date-to", dest="date_to", help="End date (ISO format)")
    search_p.add_argument("--file-pattern", dest="file_pattern", default="*.log", help="Log file pattern (default: *.log)")
    search_p.add_argument("--max-results", "-n", type=int, default=50, dest="max_results", help="Max results (default: 50)")
    search_p.add_argument("--offset", type=int, default=0, help="Pagination offset")
    search_p.add_argument("--path", "-p", dest="path", help="Project root path")
    search_p.add_argument("--search-paths", dest="search_paths",
                          help="Comma-separated additional paths to search for logs")

    # graph
    graph_p = sp.add_parser("graph", aliases=["loggraph"],
                            help="Log visualization and statistics")
    graph_p.add_argument("--mode", "-m", default="summary",
                         choices=["error-frequency", "time-trend", "summary",
                                  "anomalies", "files", "health"],
                         help="Visualization mode (default: summary)")
    graph_p.add_argument("--days", "-d", type=int, default=7, help="Time window in days (default: 7)")
    graph_p.add_argument("--granularity", "-g", default="hourly", choices=["hourly", "daily"],
                         help="Time trend granularity (default: hourly)")
    graph_p.add_argument("--file-pattern", dest="file_pattern", default="*.log", help="Log file pattern")
    graph_p.add_argument("--max-files", dest="max_files", type=int, default=50, help="Max files to scan")
    graph_p.add_argument("--path", "-p", dest="path", help="Project root path")
    graph_p.add_argument("--search-paths", dest="search_paths",
                          help="Comma-separated additional paths to search for logs")

    # discover
    disc_p = sp.add_parser("discover", help="Discover log files via systematic path collection")
    disc_p.add_argument("--path", "-p", dest="path", help="Project root path")
    disc_p.add_argument("--search-paths", dest="search_paths",
                        help="Comma-separated additional paths to search")
    disc_p.add_argument("--max-results", type=int, default=200, dest="max_results",
                        help="Max files to return")
    disc_p.add_argument("--no-lang-detect", action="store_true", dest="no_lang_detect",
                        help="Skip language detection")
    disc_p.add_argument("--no-os-detect", action="store_true", dest="no_os_detect",
                        help="Skip OS detection")
    disc_p.add_argument("--no-server-detect", action="store_true", dest="no_server_detect",
                        help="Skip server detection")
    disc_p.add_argument("--no-db-detect", action="store_true", dest="no_db_detect",
                        help="Skip database detection")
    disc_p.add_argument("--no-dev-tool-detect", action="store_true", dest="no_dev_tool_detect",
                        help="Skip local dev tool detection (Laragon, WAMP, XAMPP, MAMP, etc.)")

    # cleanup
    cleanup_p = sp.add_parser("cleanup", help="Remove old log files")
    cleanup_p.add_argument("--days", "-d", type=int, default=30, help="Max age in days (default: 30)")
    cleanup_p.add_argument("--apply", action="store_true", help="Actually remove files (default: dry-run)")
    cleanup_p.add_argument("--path", "-p", dest="path", help="Project root path")
    cleanup_p.add_argument("--search-paths", dest="search_paths",
                           help="Comma-separated additional paths to clean")

    # rotate
    rotate_p = sp.add_parser("rotate", help="Rotate oversized log files")
    rotate_p.add_argument("--max-size", "-s", type=int, default=50, dest="max_size",
                          help="Max file size in MB before rotation (default: 50)")
    rotate_p.add_argument("--keep", "-k", type=int, default=5, help="Number of rotated backups to keep (default: 5)")
    rotate_p.add_argument("--apply", action="store_true", help="Actually rotate files (default: dry-run)")
    rotate_p.add_argument("--path", "-p", dest="path", help="Project root path")

    # validate
    validate_p = sp.add_parser("validate", help="Validate a log file format")
    validate_p.add_argument("file", help="Path to log file to validate")
    validate_p.add_argument("--path", "-p", dest="path", help="Project root path")

    # info
    info_p = sp.add_parser("info", help="Show configured log directories and detection info")
    info_p.add_argument("--path", "-p", dest="path", help="Project root path")
