"""
CodeCortex MCP Server — Main entry point.

:project: CodeCortex
:package: Main
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CrossStack-v1.0
"""

import os
import sys
import time
import atexit
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from mcp.server.fastmcp import FastMCP


# ════════════════════════════════════════════════════════════
# SINGLE-INSTANCE SAFEGUARD — runs BEFORE any server init
# ════════════════════════════════════════════════════════════
def _get_lockfile_dir() -> Path:
    """Return path to project data directory.

    Uses the shared get_data_dir() from core.config.database to ensure
    a single source of truth for ~/.coddy/codecortex path resolution.
    """
    from src.core.config.database import get_data_dir
    return get_data_dir()

def _get_lockfile_path() -> Path:
    """Return path to PID lockfile in project data directory."""
    return _get_lockfile_dir() / "codecortex.pid"

def _get_killedcache_path() -> Path:
    """Return path to killed-PID cache file (prevents cascade loop)."""
    return _get_lockfile_dir() / "codecortex.killed"

def _is_shared_mode() -> bool:
    """Detect if running as shared HTTP/SSE server (multi-IDE).

    In shared mode, multiple index.cjs (from different IDEs) connect
    to ONE Python backend. Python must NOT kill other Python processes
    — the index.cjs lifecycle manager handles that.

    Returns True when CODECORTEX_TRANSPORT is 'sse' or 'http'.
    """
    transport = os.environ.get("CODECORTEX_TRANSPORT", "stdio").strip().lower()
    return transport in ("sse", "http")

def _get_node_parent_pid() -> Optional[int]:
    """Return the PID of the Node.js wrapper that spawned us (if any).

    Traverses up to find the immediate node.exe parent.
    Used in shared mode to identify which index.cjs is OUR manager.
    """
    ppid = _get_process_parent_pid(os.getpid())
    if ppid is None:
        return None
    parent_name = _get_process_name(ppid)
    if parent_name and 'node' in parent_name:
        return ppid
    # Check grandparent
    gpid = _get_process_parent_pid(ppid)
    if gpid is None:
        return None
    grandparent_name = _get_process_name(gpid)
    if grandparent_name and 'node' in grandparent_name:
        return gpid
    return None

def _get_module_signature() -> str:
    """Return a signature that identifies THIS specific codecortex instance."""
    return f"codecortex-src.main-{Path(__file__).resolve().parent}"

_INSTANCE_ID: Optional[str] = None  # populated once at module load

def _get_instance_id() -> str:
    """Generate a stable instance ID for this process lifetime (SHA-256 of PID + sig + creation time).

    Cached in module global so all callers see the same ID for this process.
    """
    global _INSTANCE_ID
    if _INSTANCE_ID:
        return _INSTANCE_ID
    import hashlib, time
    raw = f"{os.getpid()}:{_get_module_signature()}:{time.time()}"
    _INSTANCE_ID = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return _INSTANCE_ID

def _get_ide_name() -> str:
    """Detect which IDE spawned this process from environment variables."""
    for var, name in [
        ("TRAE_ID", "trae"),
        ("VSCODE_NLS_CONFIG", "vscode"),
        ("TERM_PROGRAM", None),  # check value below
    ]:
        val = os.environ.get(var, "")
        if var == "TERM_PROGRAM" and val:
            lower = val.lower()
            if "cursor" in lower:
                return "cursor"
            if "vscode" in lower:
                return "vscode"
            if "trae" in lower:
                return "trae"
            return lower.split("/")[0].split(" ")[0]  # first word
        if val:
            return name
    return "unknown"

def _build_instance_identity() -> Dict[str, Any]:
    """Build full instance identity dict for lockfile.

    Structure shared by both Python (src/main.py) and Node (scripts/server/run_server.js).
    """
    import time as _time
    identity = {
        "pid": os.getpid(),
        "signature": _get_module_signature(),
        "source": "python",
        "instance_id": _get_instance_id(),
        "ide": _get_ide_name(),
        "pid_timestamp": _time.time(),
        "version": 2,  # lockfile format version
        "shared_mode": _is_shared_mode(),
        "node_parent_pid": _get_node_parent_pid(),
    }
    return identity


def _get_python_pids_via_powershell() -> list[int]:
    """Use PowerShell Get-CimInstance to find PIDs of codecortex python processes.

    Preferred over wmic (deprecated in Win 11 24H2) and tasklist (too verbose).
    """
    script = (
        'Get-CimInstance Win32_Process -Filter "Name=\'python.exe\'" | '
        'Where-Object { $_.CommandLine -like \'*src.main*\' } | '
        'Select-Object -ExpandProperty ProcessId'
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=10,
        )
        pids = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line.isdigit():
                pids.append(int(line))
        return pids
    except Exception:
        return []


def _get_python_pids_via_tasklist() -> list[int]:
    """Fallback: use tasklist to find codecortex python PIDs (less reliable)."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        # tasklist CSV: "python.exe","1234","Console","1","xxx K"
        pids = []
        for line in result.stdout.strip().splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 2 and "python" in parts[0].lower():
                pid_str = parts[1].strip().strip('"')
                if pid_str.isdigit():
                    pids.append(int(pid_str))
        return pids
    except Exception:
        return []


def _gather_local_python_pids() -> list[int]:
    """Collect PIDs of ALL codecortex python processes running `src.main`.

    Tries PowerShell first (fastest, most reliable on modern Windows),
    falls back to tasklist if PowerShell is unavailable.
    """
    pids = _get_python_pids_via_powershell()
    if not pids:
        # Fallback for systems without PowerShell or older Windows
        pids = _get_python_pids_via_tasklist()
    return pids


def _kill_process_graceful(pid: int) -> bool:
    """Try graceful termination first, then forced kill if needed.

    Graceful: taskkill without /F  →  exit code 0 means process accepted signal
    Wait 1s → check if process still exists
    Forced:  taskkill /F /PID
    """
    import time as _time

    if sys.platform != "win32":
        # Unix: SIGTERM first, wait, SIGKILL if still alive
        try:
            os.kill(pid, 15)  # SIGTERM
            _time.sleep(1)
            # Check if alive
            try:
                os.kill(pid, 0)  # Still alive? SIGKILL
                os.kill(pid, 9)
                return True
            except OSError:
                return True  # Dead after SIGTERM
        except PermissionError:
            return False
        except ProcessLookupError:
            return True  # Already dead
        except Exception:
            return False

    # Windows: graceful kill first
    try:
        # Stage 1: graceful (taskkill without /F)
        subprocess.run(
            ["taskkill", "/PID", str(pid)],
            capture_output=True, text=True, timeout=10,
        )
        # Give it time to release DB locks
        _time.sleep(1.5)

        # Stage 2: verify dead
        check = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        if str(pid) not in check.stdout:
            return True  # Process is gone

        # Stage 3: forced kill
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True, text=True, timeout=10,
        )
        _time.sleep(0.5)
        return True
    except Exception:
        # Last resort: direct forced kill
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, text=True, timeout=10,
            )
            _time.sleep(0.5)
            return True
        except Exception:
            return False


def _get_process_parent_pid(pid: int) -> Optional[int]:
    """Get parent process ID via PowerShell Get-CimInstance."""
    script = (
        f'$p = Get-CimInstance Win32_Process -Filter "ProcessId={pid}"; '
        f'if ($p) {{ $p.ParentProcessId }}'
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=5,
        )
        ppid = result.stdout.strip()
        if ppid.isdigit():
            return int(ppid)
        return None
    except Exception:
        return None


def _get_process_name(pid: int) -> Optional[str]:
    """Get process executable name via PowerShell Get-CimInstance."""
    script = (
        f'$p = Get-CimInstance Win32_Process -Filter "ProcessId={pid}"; '
        f'if ($p) {{ $p.Name }}'
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=5,
        )
        name = result.stdout.strip()
        return name.lower() if name else None
    except Exception:
        return None


def _is_process_alive(pid: int) -> bool:
    """Check if a process is still alive."""
    try:
        check = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        return str(pid) in check.stdout
    except Exception:
        return False


def _get_process_creation_time(pid: int) -> Optional[float]:
    """Get process creation timestamp (epoch) via PowerShell."""
    script = (
        f'$p = Get-CimInstance Win32_Process -Filter "ProcessId={pid}"; '
        f'if ($p) {{ [Management.ManagementDateTimeConverter]::ToDateTime($p.CreationDate) | '
        f'Get-Date -UFormat %s }}'
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=5,
        )
        ts = result.stdout.strip()
        if ts:
            return float(ts)
        return None
    except Exception:
        return None


def _is_process_younger_than(pid: int, seconds: float = 3.0) -> bool:
    """Check if a process started less than `seconds` ago.

    Prevents cascade killing when multiple Python processes
    start simultaneously (e.g. shared server candidate pool).
    """
    import time as _time
    created = _get_process_creation_time(pid)
    if created is None:
        return False  # Can't determine → treat as old
    return (_time.time() - created) < seconds


def _is_spawned_by_node(pid: int) -> bool:
    """Check if a process was spawned by a Node.js wrapper.

    Traverses up the process tree (max 3 levels) looking for node.exe.
    A Python process spawned by run_server.js or index.cjs will have
    node.exe as its direct parent or grandparent.

    Returns True if the process is a legitimate IDE‑spawned instance.
    """
    current = pid
    for _ in range(3):  # Check parent, grandparent, great-grandparent
        ppid = _get_process_parent_pid(current)
        if ppid is None or ppid == 0:
            return False  # Can't trace further
        if ppid == current:
            return False  # Self-loop (shouldn't happen)
        parent_name = _get_process_name(ppid)
        if parent_name and 'node' in parent_name:
            # Verify the node parent is still alive
            if _is_process_alive(ppid):
                return True
            else:
                return False  # Node parent is dead → orphan
        current = ppid
    return False


# ════════════════════════════════════════════════════════════
# KILLED-PID CACHE — prevents cascade loop
# ════════════════════════════════════════════════════════════
_KILLED_CACHE_MAX_AGE = 30.0  # seconds — PIDs killed more than 30s ago are eligible for re-kill

def _read_killed_cache() -> Dict[int, float]:
    """Read killed-PID cache file. Returns {pid: kill_timestamp}."""
    cache_path = _get_killedcache_path()
    if not cache_path.exists():
        return {}
    try:
        import json
        data = json.loads(cache_path.read_text())
        if not isinstance(data, dict):
            return {}
        # Convert string keys back to int PIDs, filter expired
        import time as _time
        now = _time.time()
        result = {}
        for k, v in data.items():
            try:
                pid = int(k)
                age = now - v
                if age < _KILLED_CACHE_MAX_AGE:
                    result[pid] = v
            except (ValueError, TypeError):
                pass
        return result
    except Exception:
        return {}

def _write_killed_cache(killed: Dict[int, float]) -> None:
    """Write killed-PID cache file (atomic overwrite)."""
    cache_path = _get_killedcache_path()
    try:
        import json
        # Prune expired entries before writing
        import time as _time
        now = _time.time()
        pruned = {str(k): v for k, v in killed.items() if (now - v) < _KILLED_CACHE_MAX_AGE}
        cache_path.write_text(json.dumps(pruned))
    except Exception:
        pass


def _safe_kill_and_wait(killed_any: bool) -> bool:
    """Post-kill wait to ensure OS releases resources (file locks, ports, DB WAL).

    Returns True if wait happened, False if nothing to wait for.
    """
    import time as _time
    if not killed_any:
        return False
    # SQLite WAL recovery + OS handle cleanup needs a real pause
    _time.sleep(1.5)
    return True


def _safeguard_instance() -> None:
    """Self-kill safeguard that prevents multi-IDE process conflicts.

    Runs synchronously at module load time.

    MODES:
      - stdio mode (default): Full kill-loop for stale Python PIDs.
        Used when running standalone (e.g., run_server.js).
      - shared mode (HTTP/SSE): Skip kill-loop, just write lockfile identity.
        Used when multiple index.cjs share ONE Python backend.
        Lifecycle managed by index.cjs's file-lock + reference counting.

    Strategy (shared mode):
    1. Init logging (console→stderr + file→~/.coddy/codecortex/logs/)
    2. Write JSON lockfile with full instance identity
    3. Register atexit cleanup
    4. DO NOT kill other Python PIDs — index.cjs manages lifecycle

    Strategy (stdio mode):
    1. Init logging
    2. Load killed-PID cache to prevent cascade loops
    3. Find ALL local python.exe processes running `src.main`
    4. Kill stale/orphan instances (graceful → forced escalation)
    5. Check lockfile for any missed PID
    6. Write JSON lockfile with full instance identity
    7. Register atexit cleanup

    Instance identity fields (shared with Node in lockfile):
      pid, signature, source, instance_id, ide, pid_timestamp, version,
      shared_mode (bool), node_parent_pid (int | null)
    """
    import time as _time
    import json as _json

    # ── Phase 0: Init logging (safe: console→stderr, file→~/.coddy/codecortex/logs/) ──
    try:
        from src.core.logging import Logger as _LogSetup
        _LogSetup.setup(os.getenv("CODECORTEX_LOG_LEVEL", "INFO"))
    except Exception:
        pass
    _log = logging.getLogger("CodeCortex.Main.Safeguard")

    pid_file = _get_lockfile_path()
    current_pid = os.getpid()
    identity = _build_instance_identity()
    shared_mode = identity.get("shared_mode", False)

    killed_any = False

    _log.info(
        "Instance starting: PID=%s ID=%s IDE=%s mode=%s%s",
        current_pid,
        identity["instance_id"],
        identity["ide"],
        "shared" if shared_mode else "stdio",
        f" node_parent={identity['node_parent_pid']}" if identity.get("node_parent_pid") else "",
    )

    # ────────────────────────────────────────────────────────────
    # SHARED MODE: Skip kill-loop, let index.cjs manage lifecycle
    # ────────────────────────────────────────────────────────────
    if shared_mode:
        try:
            pid_file.write_text(_json.dumps(identity, indent=2))
            _log.info(
                "Service lock (shared): PID=%s instance=%s IDE=%s file=%s",
                current_pid, identity["instance_id"], identity["ide"], pid_file,
            )
        except OSError as e:
            _log.warning("Cannot write lockfile: %s", e)

        def _shared_cleanup():
            try:
                if pid_file.exists():
                    content = pid_file.read_text().strip()
                    try:
                        data = _json.loads(content)
                        if isinstance(data, dict) and data.get("pid") == os.getpid():
                            pid_file.unlink(missing_ok=True)
                    except Exception:
                        if content.startswith(str(os.getpid())):
                            pid_file.unlink(missing_ok=True)
            except Exception:
                pass

        atexit.register(_shared_cleanup)
        return

    # ────────────────────────────────────────────────────────────
    # STDIO MODE: Full safeguard with kill-loop
    # ────────────────────────────────────────────────────────────

    killed_cache = _read_killed_cache()
    newly_killed: Dict[int, float] = {}
    node_parent_pid = identity.get("node_parent_pid")

    # PHASE 1: Scan for ALL codecortex python PIDs
    all_pids = _gather_local_python_pids()
    for pid in all_pids:
        if pid == current_pid:
            continue

        if pid in killed_cache:
            _log.info(
                "Skipping PID=%s — already killed recently (%.1fs ago)",
                pid, _time.time() - killed_cache[pid],
            )
            continue
        if node_parent_pid and pid == node_parent_pid:
            _log.info("Skipping PID=%s — our Node parent", pid)
            continue
        if _is_process_younger_than(pid, seconds=3.0):
            _log.info("Skipping PID=%s — too young (<3s)", pid)
            continue
        if _is_spawned_by_node(pid):
            _log.info("Skipping PID=%s — child of node.exe", pid)
            continue

        _log.info("Killing stale instance PID=%s", pid)
        if _kill_process_graceful(pid):
            killed_any = True
            newly_killed[pid] = _time.time()
            _log.info("Killed stale PID=%s", pid)

    if newly_killed:
        killed_cache.update(newly_killed)
        _write_killed_cache(killed_cache)

    _safe_kill_and_wait(killed_any)

    # PHASE 2: Check lockfile for any missed PID
    if pid_file.exists() and not killed_any:
        try:
            old_content = pid_file.read_text().strip()
            old_data = _json.loads(old_content)
            old_pid = old_data.get("pid") if isinstance(old_data, dict) else None
        except Exception:
            try:
                old_pid = int(old_content.split("\n")[0].strip())
            except (ValueError, IndexError, OSError):
                old_pid = None

        if old_pid and old_pid != current_pid:
            if old_pid in killed_cache:
                _log.info("Lockfile PID=%s — already killed, skipping", old_pid)
            elif node_parent_pid and old_pid == node_parent_pid:
                _log.info("Lockfile PID=%s — our Node parent, skipping", old_pid)
            elif _is_process_younger_than(old_pid, seconds=3.0):
                _log.info("Lockfile PID=%s — too young, skipping", old_pid)
            elif _is_spawned_by_node(old_pid):
                _log.info("Lockfile PID=%s — child of node.exe, skipping", old_pid)
            elif _is_process_alive(old_pid):
                _log.info("Lockfile stale PID=%s still alive — killing", old_pid)
                _kill_process_graceful(old_pid)
                killed_any = True
                newly_killed[old_pid] = _time.time()
                killed_cache[old_pid] = _time.time()
                _write_killed_cache(killed_cache)
                _safe_kill_and_wait(killed_any)

    # PHASE 3: Write lockfile
    try:
        pid_file.write_text(_json.dumps(identity, indent=2))
        _log.info(
            "Service lock: PID=%s instance=%s IDE=%s file=%s",
            current_pid, identity["instance_id"], identity["ide"], pid_file,
        )
    except OSError as e:
        _log.warning("Cannot write lockfile: %s", e)

    # PHASE 4: Register atexit cleanup
    def _cleanup():
        try:
            if pid_file.exists():
                content = pid_file.read_text().strip()
                try:
                    data = _json.loads(content)
                    if isinstance(data, dict) and data.get("pid") == os.getpid():
                        pid_file.unlink(missing_ok=True)
                except Exception:
                    if content.startswith(str(os.getpid())):
                        pid_file.unlink(missing_ok=True)
        except Exception:
            pass

    atexit.register(_cleanup)


# Run safeguard BEFORE anything else
_safeguard_instance()

from src.core import api_response, new_request_id
from src.core.logging import Logger, get_logger
from src.core.logging.event_logger import log_event
from src.core.database import DatabaseManager
from src.core.utils.validators import validate_path, validate_uuid, validate_max_depth
from src.core.utils.path import normalize_relpath as _normalize_relpath
from src.modules.coderepository import Repository, Git, Svn
from src.modules.coderepository.adapters.filesystem.sqlite_store import SQLiteCodeRepositoryStore
from src.modules.codeindex import Indexer
from src.modules.codegraph import Graph
from src.modules.codeanalysis.core.code_service import CodeService
from src.modules.filesystem.core.service import Filesystem
from src.modules.coderefactor import Refactor
from src.modules.codetester.services.qa import QA
from src.core.telemetry import get_tracer_provider  # OpenTelemetry tracing (lazy init)

# Initialize FastMCP Server
mcp = FastMCP("CodeCortex")

# Initialize logging
Logger.setup(log_level="INFO")
logger = get_logger(__name__)

class CortexOrchestrator:
    """
    Main orchestrator for CodeCortex.

    Standardizes the flow between Repository, CodeIndex, CodeGraph, and Graphify.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db = DatabaseManager(db_path)
        self._ensure_schema()
        self.repo_store = SQLiteCodeRepositoryStore(self.db)
        self.repo_service = Repository(self.repo_store)
        self.graph_service = Graph(self.db)
        self.index_service = Indexer(self.db, codegraph_service=self.graph_service)
        self.graph_service.code_index_service = self.index_service
        self.git_service = Git(self.repo_store)
        self.svn_service = Svn()
        self.qa_service = QA(self.db)
        self.fs_service = Filesystem(
            self.db, self.repo_store,
            graph_service=self.graph_service,
            index_service=self.index_service,
            git_service=self.git_service,
            svn_service=self.svn_service,
            qa_service=self.qa_service,
        )
        self.refactor_service = Refactor(self.db, self.fs_service, self.git_service, self.graph_service)
        self.code_service = CodeService(self)
        # Auto-update service: background version checker (daemon thread)
        try:
            from src.core.update import CodeCortexUpdater
            self.update_service = CodeCortexUpdater(auto_start=True)
        except Exception as e:
            self.logger.warning("Auto-update service failed to start: %s", e)
            self.update_service = None
        self.logger = get_logger(f"{__name__}.Orchestrator")

    def _ensure_schema(self) -> None:
        """Create database tables if they do not exist (idempotent)."""
        from src.core.database.orm import BaseModel, SessionManager
        SessionManager(str(self.db._db_path)).create_tables(BaseModel)
        # Ensure vcs_url uniqueness index for cross-device identity
        self.db.conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_repositories_vcs_url
            ON repositories(vcs_url) WHERE vcs_url IS NOT NULL AND vcs_url != ''
        """)
        # Ensure deleted_at column exists (ORM model has it, raw SQL create may miss it)
        try:
            self.db.conn.execute("ALTER TABLE repositories ADD COLUMN deleted_at DATETIME")
        except Exception:
            pass
        # Ensure missing columns on legacy files table
        _FILE_MISSING_COLS = {
            "relative_path": "TEXT",
            "directory_id": "TEXT",
            "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            "deleted_at": "DATETIME",
            "language": "TEXT DEFAULT 'unknown'",
        }
        existing = {r[1] for r in self.db.conn.execute("PRAGMA table_info(files)").fetchall()}
        for col, coltype in _FILE_MISSING_COLS.items():
            if col not in existing:
                try:
                    self.db.conn.execute(f"ALTER TABLE files ADD COLUMN {col} {coltype}")
                except Exception:
                    pass
        _SYMBOL_MISSING_COLS = {
            "parent_id": "TEXT",
        }
        existing = {r[1] for r in self.db.conn.execute("PRAGMA table_info(symbols)").fetchall()}
        for col, coltype in _SYMBOL_MISSING_COLS.items():
            if col not in existing:
                try:
                    self.db.conn.execute(f"ALTER TABLE symbols ADD COLUMN {col} {coltype}")
                except Exception:
                    pass
        # Ensure missing tables used by raw SQL queries
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                repository_id TEXT NOT NULL,
                target_code TEXT,
                category TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.conn.execute("CREATE INDEX IF NOT EXISTS idx_insights_repo ON insights(repository_id)")
        self.db.conn.execute("CREATE INDEX IF NOT EXISTS idx_insights_category ON insights(category)")
        # Path mapping tables for remote server cross-device support
        from src.core.database.path_mapping import PATH_MAPPING_DDL
        for ddl in PATH_MAPPING_DDL:
            self.db.conn.execute(ddl)
        self.db.conn.commit()
        # SideCortex cross-IDE tables (sc_ prefix)
        from src.core.database.sidecortex_schema import ensure_sidecortex_tables
        ensure_sidecortex_tables(self.db.conn)

    def get_repo_id(self, path: str) -> Optional[str]:
        """Resolve a physical path to its repo ID. Falls back to remote_url matching for cross-device."""
        import subprocess, os
        root = Path(path).resolve()
        row = self.db.conn.execute("SELECT id FROM repositories WHERE root_path = ?", (str(root),)).fetchone()
        if row:
            return row['id']
        remote_url = None
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                remote_url = result.stdout.strip()
        except Exception:
            pass
        if remote_url:
            row = self.db.conn.execute(
                "SELECT id FROM repositories WHERE vcs_url = ? AND vcs_url IS NOT NULL AND vcs_url != ''",
                (remote_url,),
            ).fetchone()
            return row['id'] if row else None
        return None

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: Optional[str] = None):
        log_event(level, event_code, context, request_id=request_id, logger=self.logger)

    async def analyze(
        self,
        root_path: str,
        request_id: Optional[str] = None,
        dry_run: bool = True,
        max_depth: Optional[int] = None,
        include_codemap: bool = False,
        max_repos: int = 50
    ) -> Dict[str, Any]:
        """
        Execute the full intelligence pipeline with production guards.

        Args:
            root_path: Absolute path to the repository.
            request_id: Optional tracing ID for observability.
            dry_run: If True (default), skip DB mutations and analyze existing data.
                     Set False to perform a full refresh of the index before analysis.
            max_depth: Optional recursion limit for file discovery.
            include_codemap: If True, includes a structured symbol map in the response.
            max_repos: Quota limit for concurrent repository analysis.

        Returns:
            Dict with repository_id, analysis, codemap, and mode.
        """
        self._log_event("INFO", "ANALYSIS_STARTED", {"root_path": root_path, "dry_run": dry_run, "max_depth": max_depth}, request_id)
        try:
            repo_id = self.get_repo_id(root_path)

            if not dry_run:
                # 1. Physical Discovery (Mutating)
                repo_id = await self.repo_service.sync_repository(root_path, request_id=request_id, max_depth=max_depth)

                # 2. Semantic Indexing (AST) + Graph Sync (Mutating)
                await self.index_service.index_repository(repo_id, request_id=request_id)
            else:
                if not repo_id:
                    raise ValueError(f"Repository at {root_path} has not been initialized. Please run with dry_run=False first to create the initial index.")

            # 3. Architectural Analysis (Unified CodeGraph - Read-only)
            analysis = await self.graph_service.build_comprehensive_report(repo_id, request_id=request_id)

            # 4. Optional Codemap (Read-only)
            codemap = None
            if include_codemap:
                codemap = await self._build_codemap(repo_id)

            self._log_event("INFO", "ANALYSIS_COMPLETED", {"repository_id": repo_id, "dry_run": dry_run}, request_id)
            return {
                "repository_id": repo_id,
                "analysis": analysis,
                "codemap": codemap,
                "mode": "dry_run" if dry_run else "full_refresh"
            }
        except Exception as e:
            self._log_event("ERROR", "ANALYSIS_FAILED", {"error": str(e)}, request_id)
            raise

    async def _build_codemap(self, repo_id: str) -> Dict[str, Any]:
        """Internal helper to build a structured map of folders, files, and symbols."""
        def _execute():
            # 1. Get all directories
            dirs = self.db.conn.execute(
                "SELECT id, relative_path FROM directories WHERE repository_id = ? ORDER BY relative_path",
                (repo_id,)
            ).fetchall()

            # 2. Get all files
            files = self.db.conn.execute(
                "SELECT id, name, directory_id FROM files WHERE repository_id = ?",
                (repo_id,)
            ).fetchall()

            # 3. Get all key symbols (classes and functions)
            symbols = self.db.conn.execute(
                "SELECT id, name, symbol_type, file_id FROM symbols WHERE repository_id = ? AND symbol_type IN ('class', 'function')",
                (repo_id,)
            ).fetchall()

            # Map construction
            tree = {}
            file_symbols = {}
            for s in symbols:
                f_id = s['file_id']
                if f_id not in file_symbols: file_symbols[f_id] = []
                file_symbols[f_id].append({"id": s['id'], "name": s['name'], "type": s['symbol_type']})

            dir_files = {}
            for f in files:
                d_id = f['directory_id']
                if d_id not in dir_files: dir_files[d_id] = []
                dir_files[d_id].append({
                    "id": f['id'],
                    "name": f['name'],
                    "symbols": file_symbols.get(f['id'], [])
                })

            for d in dirs:
                tree[d['relative_path'] or "."] = dir_files.get(d['id'], [])
            return tree

        return await self.graph_service.run_in_thread(_execute)

# --- MCP Tool Wrapper ---
def _ok(message: str, data: Any, request_id: str) -> Dict[str, Any]:
    return api_response(success=True, status_code=200, message=message, data=data, request_id=request_id)

def _err(message: str, error_code: str, request_id: str, status_code: int = 400) -> Dict[str, Any]:
    return api_response(success=False, status_code=status_code, message=message, data=None, request_id=request_id, error_code=error_code)

# --- Tool Registration ---
# 5 unified MCP tools — all domain capabilities accessed via action+args dispatch.
# - codecortex:repository    (13 actions: init, inspect, analyze, sync, audit, ...)
# - codecortex:filesystem    (11 actions: read, write, delete, copy, move, search, ...)
# - codecortex:codebase      (8 actions: analyze, search, audit, graph, index, ...)
# - codecortex:scaffolder    (7 actions: list_stacks, get_stack, validate_name, ...)
# - codecortex:knowledge     (4 actions: extract, query, status, relationships)

from src.api.tools import register_tools as register_api_tools
from src.api.resources import register_resources as register_api_resources
from src.modules.knowledgegraph.api.tools import register_tools as register_knowledge_tools
from src.modules.idegraph.api.tools import register_tools as register_idegraph_tools

def create_orchestrator(db_path: Optional[str] = None) -> CortexOrchestrator:
    """
    Factory function to create orchestrator instances.

    Follows CODDY modular-standard.md requirement for DI and no global state.
    Each tool handler creates its own orchestrator instance, ensuring proper
    lifecycle management and testability.
    """
    return CortexOrchestrator(db_path)

# Unified API Tools Only (4 tools — action+args dispatch to all capabilities)
# All domain capabilities are accessed through these 4 tools via ActionRouter.
# Individual domain tools (code_analyze, graph_search, etc.) are NOT registered
# as MCP tools — they remain as internal service modules callable by ActionRouter
# and CLI.
register_api_tools(mcp, create_orchestrator)

# Register Knowledge Graph tool (5th tool)
register_knowledge_tools(mcp, create_orchestrator)

# Register IDE Graph tool (6th tool)
register_idegraph_tools(mcp, create_orchestrator)

# Register MCP Resources (codecortex:// URIs)
register_api_resources(mcp, create_orchestrator)

# Total: 6 unified MCP tools + 4 resources

if __name__ == "__main__":
    import sys

    # Initialize logging: console (stdout, JSON) + rotating file (~/.coddy/codecortex/logs/codecortex.log)
    try:
        from src.core.logging import Logger
        Logger.setup(os.getenv("CODECORTEX_LOG_LEVEL", "INFO"))
    except Exception:
        pass  # best-effort

    transport = os.getenv("CODECORTEX_TRANSPORT", "stdio").strip().lower()

    if transport in ("sse", "http"):
        # Launching the FastAPI wrapper (defined in http_server.py)
        # We import it here to avoid circular dependencies
        from scripts.server.http import main as run_server
        run_server()
    else:
        # Standard MCP Stdio transport
        mcp.run()
