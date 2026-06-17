"""
LogService — scan, search, cleanup, rotate, validate, and discover log files.

Enhanced with LogPathCollector for systematic log path discovery across
languages, OS platforms, web servers, and databases.

:project: CodeCortex
:package: Codelogs.Services
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Codelogs-v2.0
"""
from __future__ import annotations

import fnmatch
import gzip
import logging
import os
import platform
import re
import shutil
import stat
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("CodeCortex.Codelogs")

LOG_LEVEL_PATTERN = re.compile(
    r'\b(TRACE|DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b',
    re.IGNORECASE,
)
TIMESTAMP_PATTERNS = [
    re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?'),
    re.compile(r'\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}\s*[+-]\d{4}'),
    re.compile(r'[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}'),
    re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
]
LOG_EXTS = {".log", ".txt", ".out", ".err", ".0", ".1", ".gz", ".zip"}
ROTATED_EXTS = {".0", ".1", ".2", ".3", ".4", ".5", ".6", ".7", ".8", ".9"}


@dataclass
class LogEntry:
    path: str
    line: int
    level: str = "INFO"
    timestamp: Optional[str] = None
    message: str = ""
    score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "line": self.line,
            "level": self.level,
            "timestamp": self.timestamp,
            "message": self.message[:500],
            "score": self.score,
        }


@dataclass
class LogSearchFilter:
    query: Optional[str] = None
    log_levels: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    file_pattern: str = "*.log"
    max_results: int = 50
    offset: int = 0


@dataclass
class LogGraphData:
    error_frequency: Dict[str, int] = field(default_factory=dict)
    time_trend: Dict[str, int] = field(default_factory=dict)
    level_summary: Dict[str, int] = field(default_factory=dict)
    total_lines: int = 0
    total_files: int = 0
    errors_last_24h: int = 0
    top_error_messages: List[Dict[str, Any]] = field(default_factory=list)


class LogPathCollector:
    """Systematic log path discovery across languages, OS, servers, and databases.

    Algorithm:
    1. Initialize search_paths = []
    2. Add custom paths from user request (comma-separated)
    3. Add Coddy CodeWorks standard project paths
    4. Add common log paths
    5. Add paths from codebase language detection
    6. Add paths from OS detection
    7. Add paths from web server detection
    8. Add paths from database detection
    9. Process all paths with grep, glob, and regex
    """

    # ── Coddy CodeWorks Standard Paths ─────────────────────────────────
    CODDY_STANDARD_PATHS = [
        "outputs/logs",
        "outputs/logs/development",
        "outputs/logs/sandbox",
        "outputs/logs/production",
        "outputs/debugs",
    ]

    # ── Common Log Paths ──────────────────────────────────────────────
    COMMON_LOG_PATHS = [
        "logs",
        "log",
        "storage/logs",
        "storage/log",
        "var/log",
        "runtime/logs",
        "tmp/logs",
    ]

    # ── Language-Specific Log Paths ────────────────────────────────────
    LANGUAGE_PATHS: Dict[str, List[str]] = {
        "php": [
            "storage/logs",
            "var/log",
            "runtime/logs",
        ],
        "python": [
            "logs",
            "outputs/logs",
            "var/log",
        ],
        "javascript": [
            "logs",
            "outputs/logs",
            ".next/logs",
        ],
        "typescript": [
            "logs",
            "outputs/logs",
            "dist/logs",
        ],
        "java": [
            "logs",
            "tomcat/logs",
            "wildfly/standalone/log",
            "jboss/server/default/log",
            "target/logs",
        ],
        "kotlin": [
            "logs",
            "build/logs",
        ],
        "go": [
            "logs",
            "var/log",
        ],
        "rust": [
            "logs",
            "var/log",
        ],
        "ruby": [
            "log",
            "logs",
            "tmp/log",
        ],
        "csharp": [
            "logs",
            "App_Data/logs",
            "bin/logs",
        ],
        "dart": [
            "logs",
            "build/logs",
        ],
        "swift": [
            "logs",
            "build/logs",
        ],
    }

    # ── OS-Specific Log Paths ──────────────────────────────────────────
    OS_PATHS: Dict[str, List[str]] = {
        "linux": [
            "/var/log",
            "/var/log/syslog",
            "/var/log/messages",
            "/var/log/auth.log",
            "/var/log/secure",
            "/var/log/kern.log",
            "/var/log/dmesg",
            "/var/log/daemon.log",
            "/var/log/debug",
            "/var/log/boot.log",
            "/var/log/cron",
            "/var/log/mail.log",
            "/var/log/user.log",
            "/var/log/lastlog",
            "/var/log/faillog",
            "/var/log/wtmp",
            "/var/log/btmp",
        ],
        "windows": [
            os.path.join("C:", os.sep, "Windows", "Logs"),
            os.path.join("C:", os.sep, "Windows", "System32", "LogFiles"),
            os.path.join("C:", os.sep, "Windows", "System32", "winevt", "Logs"),
            os.path.join("C:", os.sep, "ProgramData", "Microsoft", "Windows", "Logs"),
            os.path.join("C:", os.sep, "inetpub", "logs", "LogFiles"),
            os.path.join(os.environ.get("TEMP", "C:\\Temp"), "logs"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "logs"),
            os.path.join(os.environ.get("APPDATA", ""), "logs"),
        ],
        "darwin": [
            "/var/log",
            os.path.join("~", "Library", "Logs"),
            os.path.join("~", "Library", "Application Support", "logs"),
            "/Library/Logs",
            "~/Library/Logs",
        ],
    }

    # ── Web Server Log Paths ───────────────────────────────────────────
    SERVER_PATHS: Dict[str, List[str]] = {
        "nginx": [
            "/var/log/nginx",
            "/var/log/nginx/access.log",
            "/var/log/nginx/error.log",
            "/usr/local/nginx/logs",
            "/opt/nginx/logs",
        ],
        "apache": [
            "/var/log/apache2",
            "/var/log/httpd",
            "/var/log/apache",
            "/usr/local/apache/logs",
            "/opt/apache/logs",
            "/etc/httpd/logs",
        ],
        "iis": [
            os.path.join("C:", os.sep, "inetpub", "logs", "LogFiles"),
        ],
        "tomcat": [
            "tomcat/logs",
            "apache-tomcat/logs",
            "/var/log/tomcat",
            "/usr/local/tomcat/logs",
        ],
        "caddy": [
            "/var/log/caddy",
        ],
    }

    # ── Database Log Paths ─────────────────────────────────────────────
    DATABASE_PATHS: Dict[str, List[str]] = {
        "mysql": [
            "/var/log/mysql",
            "/var/log/mysql/error.log",
            "/var/log/mysqld.log",
            "/var/log/mariadb",
            os.path.join("C:", os.sep, "ProgramData", "MySQL", "MySQL Server", "Data"),
        ],
        "postgresql": [
            "/var/log/postgresql",
            "/var/log/postgresql/postgresql.log",
            os.path.join("C:", os.sep, "Program Files", "PostgreSQL", "data", "pg_log"),
        ],
        "mongodb": [
            "/var/log/mongodb",
            "/var/log/mongodb/mongod.log",
        ],
        "redis": [
            "/var/log/redis",
            "/var/log/redis/redis-server.log",
        ],
        "elasticsearch": [
            "/var/log/elasticsearch",
            "logs/elasticsearch",
        ],
        "mssql": [
            os.path.join("C:", os.sep, "Program Files", "Microsoft SQL Server", "MSSQL", "Log"),
        ],
    }

    # ── Local Dev Tool Paths (Laragon, WAMP, XAMPP, MAMP, etc.) ──────
    LOCAL_DEV_TOOL_PATHS: Dict[str, List[str]] = {
        "laragon": [
            os.path.join("C:", os.sep, "laragon", "logs"),
            os.path.join("C:", os.sep, "laragon", "bin", "nginx", "logs"),
            os.path.join("C:", os.sep, "laragon", "bin", "apache", "logs"),
            os.path.join("C:", os.sep, "laragon", "tmp", "logs"),
        ],
        "wamp": [
            os.path.join("C:", os.sep, "wamp", "logs"),
            os.path.join("C:", os.sep, "wamp64", "logs"),
        ],
        "xampp": [
            os.path.join("C:", os.sep, "xampp", "apache", "logs"),
            os.path.join("C:", os.sep, "xampp", "nginx", "logs"),
            os.path.join("C:", os.sep, "xampp", "tomcat", "logs"),
            os.path.join("C:", os.sep, "xampp", "mysql", "data"),
            os.path.join("C:", os.sep, "xampp", "phpMyAdmin", "logs"),
            os.path.join("/", "Applications", "XAMPP", "xamppfiles", "logs"),
        ],
        "mamp": [
            os.path.join("C:", os.sep, "MAMP", "logs"),
            os.path.join("C:", os.sep, "MAMP", "apache", "logs"),
            os.path.join("C:", os.sep, "MAMP", "mysql", "data"),
            os.path.join("/", "Applications", "MAMP", "logs"),
            os.path.join("/", "Applications", "MAMP", "apache", "logs"),
            os.path.expanduser(os.path.join("~", "Library", "Logs", "MAMP")),
        ],
        "laravel_valet": [
            os.path.expanduser(os.path.join("~", ".config", "valet", "Log")),
            os.path.expanduser(os.path.join("~", "Library", "Logs", "Valet")),
        ],
        "laravel_sail": [
            os.path.join("logs", "sail"),
            os.path.join("storage", "logs", "sail"),
        ],
        "docker": [
            os.path.join("logs", "docker"),
            os.path.join("storage", "logs", "docker"),
            os.path.join("var", "log", "docker"),
        ],
        "laragon_alt_drives": [],  # populated dynamically in detect
    }

    LOCAL_DEV_TOOL_DETECT_SIGNALS: Dict[str, List[str]] = {
        "laragon": [
            os.path.join("C:", os.sep, "laragon", "laragon.exe"),
            os.path.join("C:", os.sep, "laragon", "usr", "bin", "laragon.exe"),
        ],
        "wamp": [
            os.path.join("C:", os.sep, "wamp", "wampmanager.exe"),
            os.path.join("C:", os.sep, "wamp64", "wampmanager.exe"),
        ],
        "xampp": [
            os.path.join("C:", os.sep, "xampp", "xampp-control.exe"),
            os.path.join("C:", os.sep, "xampp", "xampp_start.exe"),
            os.path.join("/", "Applications", "XAMPP"),
        ],
        "mamp": [
            os.path.join("C:", os.sep, "MAMP", "MAMP.exe"),
            os.path.join("/", "Applications", "MAMP", "MAMP.app"),
        ],
        "laravel_valet": [
            os.path.expanduser(os.path.join("~", ".config", "valet")),
            os.path.expanduser(os.path.join("~", ".composer", "vendor", "laravel", "valet")),
        ],
    }

    # ── File patterns for log discovery ────────────────────────────────
    LOG_FILE_GLOBS = [
        "*.log",
        "*.log.*",
        "*.log.gz",
        "*.out",
        "*.err",
        "*.txt",
        "access.log*",
        "error.log*",
        "application.log*",
        "debug.log*",
        "runtime.log*",
        "audit.log*",
        "security.log*",
        "performance.log*",
        "setup.log*",
        "test.log*",
        "thirdparty.log*",
        "syslog*",
        "messages*",
        "auth.log*",
        "catalina.*",
        "localhost.*",
        "*.access.log",
        "*.error.log",
    ]

    SEARCH_FOLDER_NAMES = ["log", "logs", "logging"]

    def __init__(self, project_root: Optional[str] = None):
        self._project_root: Optional[str] = None
        if project_root:
            self.set_project_root(project_root)

    def set_project_root(self, path: str) -> None:
        resolved = Path(path).resolve()
        if not resolved.is_dir():
            raise ValueError(f"Not a valid directory: {path}")
        self._project_root = str(resolved)

    def collect_paths(
        self,
        custom_paths: Optional[str] = None,
        detect_language: bool = True,
        detect_os: bool = True,
        detect_servers: bool = True,
        detect_databases: bool = True,
        detect_dev_tools: bool = True,
    ) -> List[str]:
        """Systematic log path collection algorithm (9 phases)."""
        search_paths: List[str] = []

        # Phase 1: Custom paths from user
        if custom_paths:
            for p in custom_paths.split(","):
                p = p.strip()
                if p:
                    search_paths.append(p)

        # Phase 2: Coddy CodeWorks standard paths
        for rel in self.CODDY_STANDARD_PATHS:
            search_paths.append(rel)

        # Phase 3: Common log paths
        search_paths.extend(self.COMMON_LOG_PATHS)

        # Phase 4: Codebase language detection
        if detect_language and self._project_root:
            langs = self._detect_languages()
            for lang in langs:
                lang_paths = self.LANGUAGE_PATHS.get(lang, [])
                search_paths.extend(lang_paths)

        # Phase 5: OS-specific paths
        if detect_os:
            os_name = self._detect_os()
            os_paths = self.OS_PATHS.get(os_name, [])
            search_paths.extend(os_paths)

        # Phase 6: Web server detection
        if detect_servers and self._project_root:
            servers = self._detect_servers()
            for server in servers:
                server_paths = self.SERVER_PATHS.get(server, [])
                search_paths.extend(server_paths)

        # Phase 7: Database detection
        if detect_databases and self._project_root:
            databases = self._detect_databases()
            for db in databases:
                db_paths = self.DATABASE_PATHS.get(db, [])
                search_paths.extend(db_paths)

        # Phase 8: Local dev tool detection (Laragon, WAMP, XAMPP, MAMP, etc.)
        if detect_dev_tools:
            dev_tool_paths = self._detect_local_dev_tool_paths()
            search_paths.extend(dev_tool_paths)

        # Phase 9: Deduplicate and normalize all paths
        search_paths = self._expand_and_dedup(search_paths)
        return search_paths

    def _detect_languages(self) -> List[str]:
        """Detect programming languages used in the project."""
        if not self._project_root:
            return []
        lang_signals: Dict[str, List[str]] = {
            "php": ["*.php", "composer.json", "artisan"],
            "python": ["*.py", "setup.py", "pyproject.toml", "requirements.txt", "Pipfile"],
            "javascript": ["*.js", "package.json", "node_modules"],
            "typescript": ["*.ts", "*.tsx", "tsconfig.json", "package.json"],
            "java": ["*.java", "pom.xml", "build.gradle", "build.gradle.kts"],
            "kotlin": ["*.kt", "*.kts", "build.gradle.kts", "pom.xml"],
            "go": ["*.go", "go.mod", "go.sum"],
            "rust": ["*.rs", "Cargo.toml"],
            "ruby": ["*.rb", "Gemfile", "Rakefile"],
            "csharp": ["*.cs", "*.csproj", "*.sln"],
            "dart": ["*.dart", "pubspec.yaml"],
            "swift": ["*.swift", "Package.swift"],
        }
        detected: List[str] = []
        for lang, signals in lang_signals.items():
            for pattern in signals:
                if pattern.startswith("*."):
                    ext = pattern[1:]
                    found = list(Path(self._project_root).rglob(pattern))
                    if len(found) > 3:
                        detected.append(lang)
                        break
                else:
                    fpath = os.path.join(self._project_root, pattern)
                    if os.path.isfile(fpath):
                        detected.append(lang)
                        break
        return detected

    def _detect_os(self) -> str:
        """Detect the operating system."""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        if system == "darwin":
            return "darwin"
        return "linux"

    def _detect_servers(self) -> List[str]:
        """Detect web servers configured in the project."""
        if not self._project_root:
            return []
        detected: List[str] = []
        root = self._project_root

        # Check nginx configs
        nginx_sites = ["/etc/nginx", "/usr/local/nginx/conf"]
        nginx_project = list(Path(root).rglob("nginx*.conf")) + \
                        list(Path(root).rglob("*.nginx.conf")) + \
                        list(Path(root).rglob("site-*")) if os.path.isdir(root) else []
        if nginx_project or any(os.path.isdir(p) for p in nginx_sites):
            detected.append("nginx")

        # Check apache
        apache_dirs = ["/etc/apache2", "/etc/httpd"]
        apache_project = list(Path(root).rglob(".htaccess")) + \
                          list(Path(root).rglob("apache*.conf")) if os.path.isdir(root) else []
        if apache_project or any(os.path.isdir(p) for p in apache_dirs):
            detected.append("apache")

        # Check tomcat
        tomcat_dirs = ["tomcat", "apache-tomcat"]
        tomcat_project = [d for d in tomcat_dirs if os.path.isdir(os.path.join(root, d))]
        if tomcat_project or any(os.path.isdir(p) for p in
                                 ["/var/log/tomcat", "/usr/local/tomcat"]):
            detected.append("tomcat")

        # Check caddy
        if os.path.isfile(os.path.join(root, "Caddyfile")):
            detected.append("caddy")

        return detected

    def _detect_databases(self) -> List[str]:
        """Detect databases used in the project."""
        if not self._project_root:
            return []
        detected: List[str] = []
        root = self._project_root

        db_signals: Dict[str, List[str]] = {
            "mysql": ["my.cnf", "my.ini", "*.sql", "migrations"],
            "postgresql": ["postgresql.conf", "pg_hba.conf", "*.sql", "migrations"],
            "mongodb": ["mongod.conf", "*.bson"],
            "redis": ["redis.conf"],
            "elasticsearch": ["elasticsearch.yml", "elasticsearch.yaml"],
        }

        for db, signals in db_signals.items():
            for pattern in signals:
                fpath = os.path.join(root, pattern) if not pattern.startswith("*.") else None
                if fpath and os.path.isfile(fpath):
                    detected.append(db)
                    break
                elif pattern.startswith("*."):
                    ext = pattern[1:]
                    found = list(Path(root).rglob(pattern))[:5] if os.path.isdir(root) else []
                    if found:
                        detected.append(db)
                        break
        return detected

    def _detect_local_dev_tools(self) -> List[str]:
        """Detect local development environment tools installed on the system.

        Checks for Laragon, WAMP, XAMPP, MAMP, Laravel Valet presence
        by looking for their executable/config files.
        Returns list of detected tool names.
        """
        detected: List[str] = []
        for tool_name, signals in self.LOCAL_DEV_TOOL_DETECT_SIGNALS.items():
            for signal_path in signals:
                expanded = os.path.expanduser(signal_path)
                if os.path.exists(expanded):
                    detected.append(tool_name)
                    break
        return detected

    def _detect_local_dev_tool_paths(self) -> List[str]:
        """Get log paths for all detected local dev tools on this system.

        Also scans alternate drives on Windows for Laragon (D:, E:, etc.).
        """
        paths: List[str] = []
        detected = self._detect_local_dev_tools()

        for tool in detected:
            tool_paths = self.LOCAL_DEV_TOOL_PATHS.get(tool, [])
            paths.extend(tool_paths)

        # Special: scan alternate drives for Laragon on Windows
        if self._detect_os() == "windows" and (
            "laragon" in detected or "wamp" in detected or "xampp" in detected
        ):
            import string
            detected_root_names = []
            if "laragon" in detected:
                detected_root_names.append("laragon")
            if "wamp" in detected or "wamp64" in detected:
                detected_root_names.append("wamp")
                detected_root_names.append("wamp64")
            if "xampp" in detected:
                detected_root_names.append("xampp")

            for drive_letter in string.ascii_uppercase:
                drive = f"{drive_letter}:\\"
                if drive == "C:\\":
                    continue
                for root_name in detected_root_names:
                    candidate = os.path.join(drive, root_name)
                    if os.path.isdir(candidate):
                        # Found on alternate drive
                        alt_root = os.path.join(drive, root_name, "logs")
                        if os.path.isdir(alt_root):
                            paths.append(alt_root)
                        # Also check sub-component logs
                        for sub in ["apache", "nginx", "mysql", "tmp", "bin"]:
                            sub_log = os.path.join(drive, root_name, "bin", sub, "logs") if sub != "tmp" else os.path.join(drive, root_name, "tmp", "logs")
                            if sub == "tmp":
                                sub_log = os.path.join(drive, root_name, "tmp", "logs")
                            elif sub == "mysql":
                                sub_log = os.path.join(drive, root_name, "bin", "mysql", "data")
                            else:
                                sub_log = os.path.join(drive, root_name, "bin", sub, "logs")
                            if os.path.isdir(sub_log):
                                paths.append(sub_log)

        return paths

    def _expand_and_dedup(self, paths: List[str]) -> List[str]:
        """Expand paths relative to project root, deduplicate, and filter."""
        expanded: List[str] = []
        seen: Set[str] = set()

        for p in paths:
            # Normalize path separators
            normalized = os.path.normpath(p) if not p.startswith(("/", "C:")) else p

            # Resolve relative paths against project root
            if self._project_root and not os.path.isabs(normalized):
                resolved = os.path.normpath(os.path.join(self._project_root, normalized))
            else:
                resolved = normalized

            if resolved in seen:
                continue
            seen.add(resolved)
            expanded.append(resolved)

        return expanded

    def discover_log_files(
        self,
        custom_paths: Optional[str] = None,
        max_depth: int = 10,
        max_results: int = 500,
        detect_language: bool = True,
        detect_os: bool = True,
        detect_servers: bool = True,
        detect_databases: bool = True,
        detect_dev_tools: bool = True,
    ) -> List[Dict[str, Any]]:
        """Discover actual log files using the systematic path collection algorithm.

        Uses grep-like scanning (os.walk), glob, and regex to find all log files
        across discovered paths.
        """
        all_paths = self.collect_paths(
            custom_paths=custom_paths,
            detect_language=detect_language,
            detect_os=detect_os,
            detect_servers=detect_servers,
            detect_databases=detect_databases,
            detect_dev_tools=detect_dev_tools,
        )

        results: List[Dict[str, Any]] = []
        seen_paths: Set[str] = set()

        # Strategy 1: Walk through discovered directories
        for search_root in all_paths:
            if not os.path.isdir(search_root):
                continue
            try:
                for r, dirs, files in os.walk(search_root):
                    depth = r.replace(search_root, "").count(os.sep)
                    if depth > max_depth:
                        dirs.clear()
                        continue
                    for fname in files:
                        if not self._is_log_file(fname):
                            continue
                        fpath = os.path.join(r, fname)
                        if fpath in seen_paths:
                            continue
                        seen_paths.add(fpath)
                        try:
                            st = os.stat(fpath)
                            rel = os.path.relpath(fpath, self._project_root) if self._project_root else fpath
                            results.append({
                                "path": rel,
                                "abs_path": fpath,
                                "size_bytes": st.st_size,
                                "size_display": self._format_size(st.st_size),
                                "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                                "created": datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat(),
                                "ext": os.path.splitext(fname)[1].lower(),
                                "discovery_method": "directory_walk",
                            })
                            if len(results) >= max_results:
                                return results
                        except Exception:
                            continue
            except (PermissionError, OSError):
                continue

        # Strategy 2: Glob for *.log files under project root (catch-all)
        if self._project_root and len(results) < max_results:
            for root, dirs, files in os.walk(self._project_root):
                depth = root.replace(self._project_root, "").count(os.sep)
                if depth > max_depth * 2:
                    dirs.clear()
                    continue
                # Skip hidden dirs, node_modules, vendor, .git
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                           ("node_modules", "vendor", ".git", "__pycache__", "venv", ".venv", ".env")]
                for fname in files:
                    if not self._is_log_file(fname):
                        continue
                    fpath = os.path.join(root, fname)
                    if fpath in seen_paths:
                        continue
                    seen_paths.add(fpath)
                    try:
                        st = os.stat(fpath)
                        rel = os.path.relpath(fpath, self._project_root) if self._project_root else fpath
                        results.append({
                            "path": rel,
                            "abs_path": fpath,
                            "size_bytes": st.st_size,
                            "size_display": self._format_size(st.st_size),
                            "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                            "created": datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat(),
                            "ext": os.path.splitext(fname)[1].lower(),
                            "discovery_method": "glob_catch_all",
                        })
                        if len(results) >= max_results:
                            return results
                    except Exception:
                        continue

        return results

    def _is_log_file(self, fname: str) -> bool:
        ext = os.path.splitext(fname)[1].lower()
        if ext in LOG_EXTS:
            return True
        if ext in ROTATED_EXTS:
            base = os.path.splitext(fname)[0]
            base_ext = os.path.splitext(base)[1].lower()
            return base_ext in LOG_EXTS
        return False

    def _format_size(self, size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class LogService:
    """Core log service with enhanced discovery and multi-path scanning.

    Auto-indexing: when no log roots are found, triggers automatic log discovery
    using LogPathCollector to find log files across the project tree,
    including language-specific, OS-specific, server, and database paths.
    Discovered roots are cached for the session lifetime.
    """

    ALLOWED_LOG_ROOTS = {"logs", os.path.join("outputs", "logs"),
                         os.path.join("storage", "logs"), "log",
                         os.path.join("outputs", "debugs")}

    def __init__(self, project_root: Optional[str] = None):
        self._project_root: Optional[str] = None
        self._path_collector: Optional[LogPathCollector] = None
        self._auto_discovered_roots: Optional[List[str]] = None
        self._auto_index_attempted: bool = False
        if project_root:
            self.set_project_root(project_root)

    @property
    def path_collector(self) -> LogPathCollector:
        if self._path_collector is None:
            self._path_collector = LogPathCollector(self._project_root)
        return self._path_collector

    def set_project_root(self, path: str) -> None:
        resolved = Path(path).resolve()
        if not resolved.is_dir():
            raise ValueError(f"Not a valid directory: {path}")
        self._project_root = str(resolved)
        if self._path_collector:
            self._path_collector.set_project_root(self._project_root)
        self._auto_discovered_roots = None
        self._auto_index_attempted = False

    def _get_log_roots(self, search_paths: Optional[str] = None) -> List[str]:
        """Get log roots, including all discovered paths if search_paths given."""
        if search_paths:
            roots: List[str] = []
            for p in search_paths.split(","):
                p = p.strip()
                if not p:
                    continue
                if os.path.isabs(p):
                    if os.path.isdir(p):
                        roots.append(os.path.normpath(p))
                elif self._project_root:
                    candidate = os.path.join(self._project_root, p)
                    if os.path.isdir(candidate):
                        roots.append(os.path.normpath(candidate))
            for rel in self.ALLOWED_LOG_ROOTS:
                if self._project_root:
                    candidate = os.path.join(self._project_root, rel)
                    if os.path.isdir(candidate) and os.path.normpath(candidate) not in roots:
                        roots.append(os.path.normpath(candidate))
            return roots

        if not self._project_root:
            return []
        roots = []
        for rel in self.ALLOWED_LOG_ROOTS:
            candidate = os.path.join(self._project_root, rel)
            if os.path.isdir(candidate):
                roots.append(os.path.normpath(candidate))
        return roots

    def _ensure_log_roots(self, search_paths: Optional[str] = None) -> List[str]:
        """Get log roots with auto-indexing fallback when data is empty.

        If no roots found via standard paths, triggers automatic log discovery
        across the project tree using LogPathCollector. Discovered roots are
        cached to avoid repeated discovery in a single session.
        """
        roots = self._get_log_roots(search_paths)
        if roots:
            return roots

        if not self._project_root:
            return []

        if self._auto_index_attempted:
            return self._auto_discovered_roots or []

        self._auto_index_attempted = True
        logger.info("codelogs|auto_index|triggered|project=%s", self._project_root)

        try:
            discovered = self.path_collector.discover_log_files(
                max_results=500,
                detect_language=True,
                detect_os=True,
                detect_servers=True,
                detect_databases=True,
                detect_dev_tools=True,
            )
            if discovered:
                parent_dirs: Set[str] = set()
                for f in discovered:
                    parent = os.path.dirname(f.get("abs_path", ""))
                    if parent and os.path.isdir(parent):
                        parent_dirs.add(os.path.normpath(parent))
                if parent_dirs:
                    self._auto_discovered_roots = sorted(parent_dirs)
                    logger.info("codelogs|auto_index|found|roots=%d|files=%d",
                                len(self._auto_discovered_roots), len(discovered))
                    return self._auto_discovered_roots
        except Exception as e:
            logger.warning("codelogs|auto_index|error=%s", str(e)[:120])

        self._auto_discovered_roots = []
        return []

    def _validate_path(self, path: str) -> str:
        resolved = os.path.normpath(os.path.abspath(path))
        roots = self._get_log_roots()
        allowed = False
        for root in roots:
            if resolved.startswith(root):
                allowed = True
                break
        if not allowed:
            raise PermissionError(
                f"Access denied: {path} is outside allowed log directories."
            )
        return resolved

    def _is_log_file(self, fname: str) -> bool:
        ext = os.path.splitext(fname)[1].lower()
        if ext in LOG_EXTS:
            return True
        if ext in ROTATED_EXTS:
            base = os.path.splitext(fname)[0]
            base_ext = os.path.splitext(base)[1].lower()
            return base_ext in LOG_EXTS or base_ext in LOG_EXTS
        return False

    def _parse_log_level(self, line: str) -> str:
        m = LOG_LEVEL_PATTERN.search(line)
        if not m:
            return "INFO"
        level = m.group(1).upper()
        if level == "WARNING":
            return "WARN"
        if level == "FATAL":
            return "CRITICAL"
        return level

    def _parse_timestamp(self, line: str) -> Optional[str]:
        for pat in TIMESTAMP_PATTERNS:
            m = pat.search(line)
            if m:
                return m.group(0)
        return None

    def _read_log_file(self, fpath: str, max_size_mb: int = 10) -> Optional[List[str]]:
        try:
            size = os.path.getsize(fpath)
            if size > max_size_mb * 1024 * 1024:
                logger.debug("codelogs|skip_large|path=%s|size=%d", fpath, size)
                return None
            if fpath.endswith(".gz"):
                with gzip.open(fpath, "rt", encoding="utf-8", errors="replace") as f:
                    return f.readlines()
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                return f.readlines()
        except Exception as e:
            logger.debug("codelogs|read_error|path=%s|error=%s", fpath, str(e)[:80])
            return None

    def scan_logs(self, recursive: bool = True, max_depth: int = 10,
                  search_paths: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scan all log directories and return file metadata.

        Auto-indexes when no log roots are found (auto-discovery).
        """
        roots = self._ensure_log_roots(search_paths)
        if not roots:
            logger.warning("codelogs|scan|no_log_roots|project=%s", self._project_root)
            return []

        results: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for root in roots:
            for r, dirs, files in os.walk(root):
                depth = r.replace(root, "").count(os.sep)
                if depth > max_depth:
                    dirs.clear()
                    continue
                for fname in files:
                    if not self._is_log_file(fname):
                        continue
                    fpath = os.path.join(r, fname)
                    if fpath in seen:
                        continue
                    seen.add(fpath)
                    try:
                        st = os.stat(fpath)
                        rel = os.path.relpath(fpath, self._project_root) if self._project_root else fpath
                        results.append({
                            "path": rel,
                            "size_bytes": st.st_size,
                            "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                            "created": datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat(),
                            "ext": os.path.splitext(fname)[1].lower(),
                        })
                    except Exception:
                        continue
        return results

    def search(self, filt: LogSearchFilter,
               search_paths: Optional[str] = None) -> List[LogEntry]:
        """Search log files with filters for level, time range, and text.

        Auto-indexes when no log roots are found (auto-discovery).
        """
        roots = self._ensure_log_roots(search_paths)
        if not roots:
            return []

        query_lower = filt.query.lower() if filt.query else None
        level_set = {l.upper() for l in filt.log_levels} if filt.log_levels else None
        results: List[LogEntry] = []
        file_pats = [p.strip() for p in filt.file_pattern.split(",")] if filt.file_pattern else ["*.log"]

        for root in roots:
            for r, dirs, files in os.walk(root):
                for fname in files:
                    if not self._is_log_file(fname):
                        continue
                    if not any(fnmatch.fnmatch(fname, p) for p in file_pats):
                        continue
                    fpath = os.path.join(r, fname)
                    rel_path = os.path.relpath(fpath, self._project_root) if self._project_root else fpath
                    lines = self._read_log_file(fpath)
                    if lines is None:
                        continue
                    for lineno, line in enumerate(lines, 1):
                        stripped = line.strip()
                        if not stripped:
                            continue
                        timestamp = self._parse_timestamp(stripped)
                        level = self._parse_log_level(stripped)
                        if level_set and level not in level_set:
                            continue
                        if query_lower and query_lower not in stripped.lower():
                            continue
                        if filt.date_from or filt.date_to:
                            ts = timestamp or ""
                            if filt.date_from and ts < filt.date_from:
                                continue
                            if filt.date_to and ts > filt.date_to:
                                continue
                        results.append(LogEntry(
                            path=rel_path,
                            line=lineno,
                            level=level,
                            timestamp=timestamp,
                            message=stripped,
                            score=1.0 if level in ("ERROR", "CRITICAL", "FATAL") else 0.7,
                        ))
                        if len(results) >= filt.max_results + filt.offset:
                            break
                    if len(results) >= filt.max_results + filt.offset:
                        break
                if len(results) >= filt.max_results + filt.offset:
                    break

        results.sort(key=lambda e: (
            0 if e.level in ("ERROR", "CRITICAL", "FATAL") else 1,
            e.timestamp or "",
        ), reverse=False)

        paginated = results[filt.offset:filt.offset + filt.max_results]
        return paginated

    def validate(self, fpath: str) -> Dict[str, Any]:
        resolved = self._validate_path(fpath)
        if not os.path.isfile(resolved):
            return {"valid": False, "error": f"Not a file: {fpath}", "file": fpath}
        lines = self._read_log_file(resolved)
        if lines is None:
            return {"valid": False, "error": "Could not read file (too large or unreadable)", "file": fpath}
        total = 0
        valid = 0
        levels: Counter = Counter()
        ts_count = 0
        errors: List[str] = []
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            total += 1
            ts = self._parse_timestamp(stripped)
            level = self._parse_log_level(stripped)
            levels[level] += 1
            if ts:
                ts_count += 1
            line_valid = True
            if stripped.startswith("[") and "]" in stripped:
                bracket_content = stripped[1:stripped.index("]")]
                if not ts and not re.match(r'[\w\s/:.-]+', bracket_content):
                    line_valid = False
            if line_valid:
                valid += 1
            else:
                if len(errors) < 10:
                    errors.append(f"Line {lineno}: malformed format")
        ratio = valid / max(total, 1)
        return {
            "valid": ratio >= 0.5,
            "confidence": round(ratio, 3),
            "file": fpath,
            "total_lines": total,
            "valid_lines": valid,
            "levels_found": dict(levels.most_common()),
            "lines_with_timestamps": ts_count,
            "errors": errors[:10] if errors else None,
        }

    def cleanup(self, days: int = 30, dry_run: bool = True,
                search_paths: Optional[str] = None) -> Dict[str, Any]:
        """Remove old log files. Auto-indexes when no log roots are found."""
        roots = self._ensure_log_roots(search_paths)
        if not roots:
            return {"message": "No log directories found", "removed": 0, "dry_run": dry_run}
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        removed = 0
        freed_bytes = 0
        removed_files: List[str] = []
        for root in roots:
            for r, dirs, files in os.walk(root):
                for fname in files:
                    fpath = os.path.join(r, fname)
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(fpath), tz=timezone.utc)
                        if mtime < cutoff:
                            fsize = os.path.getsize(fpath)
                            rel = os.path.relpath(fpath, self._project_root) if self._project_root else fpath
                            if dry_run:
                                logger.info("codelogs|cleanup|dry_run|remove|path=%s|age_days=%d",
                                             rel, (datetime.now(tz=timezone.utc) - mtime).days)
                            else:
                                os.remove(fpath)
                                logger.info("codelogs|cleanup|removed|path=%s|size=%d", rel, fsize)
                            removed += 1
                            freed_bytes += fsize
                            removed_files.append(rel)
                    except Exception as e:
                        logger.debug("codelogs|cleanup|error|path=%s|error=%s", fpath, str(e)[:80])
        return {
            "message": f"Would remove {removed} files ({freed_bytes} bytes freed)" if dry_run
                       else f"Removed {removed} files ({freed_bytes} bytes freed)",
            "dry_run": dry_run,
            "removed": removed,
            "freed_bytes": freed_bytes,
            "files": removed_files[:100] if removed_files else None,
            "max_age_days": days,
        }

    def rotate(self, max_size_mb: int = 50, keep: int = 5, dry_run: bool = True,
               search_paths: Optional[str] = None) -> Dict[str, Any]:
        """Rotate oversized log files. Auto-indexes when no log roots are found."""
        roots = self._ensure_log_roots(search_paths)
        if not roots:
            return {"message": "No log directories found", "rotated": 0, "dry_run": dry_run}
        rotated = 0
        rotated_files: List[str] = []
        for root in roots:
            for r, dirs, files in os.walk(root):
                for fname in files:
                    if not self._is_log_file(fname) or fname.endswith(".gz"):
                        continue
                    fpath = os.path.join(r, fname)
                    try:
                        size = os.path.getsize(fpath)
                        if size < max_size_mb * 1024 * 1024:
                            continue
                        rel = os.path.relpath(fpath, self._project_root) if self._project_root else fpath
                        base, ext = os.path.splitext(fpath)
                        if not dry_run:
                            for i in range(keep - 1, 0, -1):
                                older = f"{base}.{i}{ext}"
                                newer = f"{base}.{i - 1}{ext}"
                                if os.path.exists(newer):
                                    if os.path.exists(older):
                                        os.remove(older)
                                    shutil.move(newer, older)
                            shutil.move(fpath, f"{base}.1{ext}")
                        rotated += 1
                        rotated_files.append(rel)
                    except Exception as e:
                        logger.debug("codelogs|rotate|error|path=%s|error=%s", fpath, str(e)[:80])
        return {
            "message": f"Would rotate {rotated} files" if dry_run
                       else f"Rotated {rotated} files",
            "dry_run": dry_run,
            "rotated": rotated,
            "files": rotated_files[:100] if rotated_files else None,
            "max_size_mb": max_size_mb,
            "keep": keep,
        }
