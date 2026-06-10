"""Server lifecycle CLI commands."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

from src.cli.common import PROJECT_ROOT, ok, err


def cmd_server_status(args_ns: argparse.Namespace) -> Dict:
    import httpx
    try:
        resp = httpx.get("http://127.0.0.1:8001/status", timeout=3)
        return ok("Server is running", resp.json())
    except Exception:
        return err("Server is not running", "SERVER_OFFLINE", 503)


def cmd_server_start(args_ns: argparse.Namespace) -> Dict:
    import subprocess
    port = getattr(args_ns, "port", 8001)
    host = getattr(args_ns, "host", "127.0.0.1")
    expose = getattr(args_ns, "expose", None) or os.getenv("CODECORTEX_EXPOSE", "")
    try:
        env = os.environ.copy()
        env["CODECORTEX_PORT"] = str(port)
        env["CODECORTEX_TRANSPORT"] = "http"
        env["PYTHONPATH"] = str(PROJECT_ROOT)

        script = str(PROJECT_ROOT / "scripts" / "server" / "http.py")
        creation_flags = 0
        if os.name == "nt":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        cmd = [sys.executable, "-u", script, "--host", host, "--port", str(port)]
        if expose:
            cmd.extend(["--expose", expose])

        process = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=creation_flags,
        )
        time.sleep(2)

        import httpx
        try:
            resp = httpx.get(f"http://{host}:{port}/status", timeout=3)
            data = {"url": f"http://{host}:{port}", "status": resp.json()}
            if expose:
                data["tunnel"] = expose
            return ok("Server started", data)
        except Exception:
            return err("Server process started but not responding", "SERVER_START_ERROR", 500)
    except Exception as e:
        return err(f"Failed to start server: {e}", "SERVER_START_ERROR", 500)


def cmd_server_stop(args_ns: argparse.Namespace) -> Dict:
    import subprocess
    port = getattr(args_ns, "port", 8001)
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -State Listen | Select-Object -ExpandProperty OwningProcess -Unique"],
            capture_output=True, text=True, shell=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = [line.strip() for line in result.stdout.strip().splitlines() if line.strip().isdigit()]
            for pid in pids:
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
            return ok(f"Server stopped ({len(pids)} process(es))", {"killed_pids": pids})
        return err("No server process found", "SERVER_NOT_RUNNING", 404)
    except Exception as e:
        return err(f"Failed to stop server: {e}", "SERVER_STOP_ERROR", 500)


COMMANDS = {
    "status": cmd_server_status,
    "start": cmd_server_start,
    "stop": cmd_server_stop,
}


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("server", help="Server lifecycle management")
    sp = p.add_subparsers(dest="server_action", required=True)
    sp.add_parser("status", help="Check server status")
    s = sp.add_parser("start", help="Start HTTP server")
    s.add_argument("--port", type=int, default=8001, help="Port")
    s.add_argument("--host", default="127.0.0.1", help="Host")
    s.add_argument("--expose", help="Relay URL to expose via tunnel (e.g. https://api.codecortex.ai)")
    sp.add_parser("stop", help="Stop HTTP server").add_argument("--port", type=int, default=8001, help="Port")
