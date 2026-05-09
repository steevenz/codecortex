#!/usr/bin/env python
"""
CodeCortex Server Manager - Enhanced Multi-Agent Shared Server Controller

Enhanced version with better error handling and async support.

Author: Steeven Andrian Salim — Senior Principal Architect

Usage:
    python scripts/server/manage.py status          # Check server status
    python scripts/server/manage.py start           # Start shared server
    python scripts/server/manage.py stop            # Stop shared server
    python scripts/server/manage.py restart         # Restart server
    python scripts/server/manage.py logs            # View server logs

Environment Variables:
    CODECORTEX_PORT - Server port (default: 8001)
    CODECORTEX_HOST - Server host (default: 127.0.0.1)
"""
from __future__ import annotations

import sys
import os
import asyncio
import argparse
import subprocess
import time
from pathlib import Path
from typing import Optional

# Fix Windows console encoding for emoji/unicode output
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root and scripts/server to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from discover import CortexServerDiscovery, CortexServerPool

VERSION = "2.0.0"

def show_banner():
    """Display the CodeCortex banner with author info."""
    print(f"\n  CODECORTEX INTELLIGENCE SERVER {VERSION}")
    print("  Crafted By Steeven Andrian Salim - https://github.com/steevenz\n")


class CortexServerManager:
    """Enhanced server manager with better error handling and async support."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or PROJECT_ROOT
        self.port = int(os.getenv("CODECORTEX_PORT", "8001"))
        self.discovery = CortexServerDiscovery()

    def get_status(self, verbose: bool = False) -> bool:
        """Check if CodeCortex server is running."""
        show_banner()
        print("🔍 Checking CodeCortex server status...")

        servers = asyncio.run(self.discovery.scan(verbose=verbose))

        if servers:
            print(f"\n✅ CodeCortex Server is RUNNING")
            for s in servers:
                uptime = s.get_uptime()
                uptime_str = f"{uptime:.1f}s" if uptime else "Unknown"
                print(f"   📍 {s.url}")
                print(f"      Port: {s.port}")
                print(f"      Healthy: {s.is_healthy}")
                print(f"      Uptime: {uptime_str}")
                print(f"      Connections: {s.connection_count}")
            print(f"\n   AI Agents can connect to: {servers[0].url}")
            return True
        else:
            print("\n❌ CodeCortex Server is NOT running")
            print("   Start with: python scripts/server/manage.py start")
            return False

    def start_server(self, detach: bool = False) -> int:
        """Start CodeCortex server in shared mode."""
        print("🚀 Starting CodeCortex Shared Server...")

        # Check if already running
        servers = asyncio.run(self.discovery.scan())

        if servers:
            print(f"✅ Server already running at {servers[0].url}")
            return 0

        # Start new server
        pool = CortexServerPool(auto_start=True, preferred_port=self.port)

        try:
            url = asyncio.run(pool.initialize())
            print(f"\n✅ CodeCortex Server started at {url}")
            print(f"\n📝 Multi-Agent Connection Info:")
            print(f"   SSE Endpoint: {url}/codecortex-api/v1/sync")
            print(f"   Health Check: {url}/status")
            print(f"   All AI agents should use this URL")
            print(f"\n⚠️  Press Ctrl+C to stop")

            # Keep running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Shutting down...")
                asyncio.run(pool.shutdown())
                return 0

        except Exception as e:
            print(f"\n❌ Failed to start server: {e}")
            return 1

    def stop_server(self) -> int:
        """Stop running CodeCortex server."""
        show_banner()
        print("🛑 Stopping CodeCortex Server...")

        try:
            # Find and kill LISTENING process(es) bound to the configured port.
            command = (
                f'Get-NetTCPConnection -LocalPort {self.port} -State Listen '
                '| Select-Object -ExpandProperty OwningProcess -Unique'
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                shell=False
            )

            if result.returncode == 0 and result.stdout:
                lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
                killed_count = 0
                for line in lines:
                    pid = line
                    if pid.isdigit():
                        print(f"   Found process PID: {pid}")
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, text=True)
                        print(f"   ✅ Stopped process {pid}")
                        killed_count += 1

                if killed_count > 0:
                    print(f"\n✅ CodeCortex Server stopped ({killed_count} process(es))")
                    return 0
                else:
                    print("\n⚠️  No CodeCortex server processes found")
                    return 1
            else:
                print("\n⚠️  No CodeCortex server processes found")
                return 1

        except Exception as e:
            print(f"⚠️  Error stopping server: {e}")
            return 1

    def restart_server(self) -> int:
        """Restart CodeCortex server."""
        show_banner()
        print("🔄 Restarting CodeCortex Server...")
        self.stop_server()
        time.sleep(2)
        return self.start_server()

    def view_logs(self, tail: int = 50) -> int:
        """View server logs."""
        show_banner()
        log_path = self.project_root / "outputs" / "logs" / "codecortex_service.log"

        if not log_path.exists():
            # Fallback to database/logs
            log_path = self.project_root / "database" / "logs" / "codecortex_service.log"

        if not log_path.exists():
            print(f"❌ Log file not found at expected locations:")
            print(f"   - {self.project_root / 'outputs' / 'logs' / 'codecortex_service.log'}")
            print(f"   - {self.project_root / 'database' / 'logs' / 'codecortex_service.log'}")
            return 1

        print(f"📋 Viewing last {tail} lines from {log_path}\n")

        try:
            command = f"Get-Content -Tail {tail} -Wait '{log_path}'"
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
            )
            return result.returncode
        except KeyboardInterrupt:
            print("\n\n📋 Log viewing stopped")
            return 0
        except Exception as e:
            print(f"❌ Failed to view logs: {e}")
            return 1


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CodeCortex Server Manager - Enhanced Multi-Agent Shared Server Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/server/manage.py status
  python scripts/server/manage.py start
  python scripts/server/manage.py stop
  python scripts/server/manage.py restart
  python scripts/server/manage.py logs
        """
    )

    parser.add_argument(
        "command",
        choices=["status", "start", "stop", "restart", "logs"],
        help="Command to execute"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--tail",
        type=int,
        default=50,
        help="Number of log lines to show (default: 50)"
    )

    args = parser.parse_args()

    manager = CortexServerManager()

    commands = {
        "status": lambda: 0 if manager.get_status(args.verbose) else 1,
        "start": lambda: manager.start_server(),
        "stop": lambda: manager.stop_server(),
        "restart": lambda: manager.restart_server(),
        "logs": lambda: manager.view_logs(args.tail),
    }

    try:
        exit_code = commands[args.command]()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
