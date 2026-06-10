"""Remote server path mapping CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from src.cli.common import ok, err, _remote_headers, _get_device_id, _remote_url


def cmd_remote_path_map(args_ns: argparse.Namespace) -> Dict:
    import httpx
    url = _remote_url(args_ns)
    if not url:
        return err("--remote URL required. Use --remote http://server:8001", "REMOTE_REQUIRED")
    device_path = str(Path(args_ns.device_path).resolve())
    server_path = str(Path(args_ns.server_path).resolve())
    try:
        resp = httpx.post(f"{url}/codecortex-api/v1/path-map", json={
            "device_id": _get_device_id(),
            "device_path": device_path,
            "server_path": server_path,
        }, headers=_remote_headers(), timeout=10)
        return ok("Path mapping registered", resp.json())
    except Exception as e:
        return err(f"Remote mapping failed: {e}", "REMOTE_ERROR")


def cmd_remote_list(args_ns: argparse.Namespace) -> Dict:
    import httpx
    url = _remote_url(args_ns)
    if not url:
        return err("--remote URL required", "REMOTE_REQUIRED")
    try:
        resp = httpx.get(f"{url}/codecortex-api/v1/path-mappings",
                         params={"device_id": _get_device_id()},
                         headers=_remote_headers(), timeout=10)
        return ok("Path mappings", resp.json())
    except Exception as e:
        return err(f"Remote list failed: {e}", "REMOTE_ERROR")


def cmd_remote_unmap(args_ns: argparse.Namespace) -> Dict:
    import httpx
    url = _remote_url(args_ns)
    if not url:
        return err("--remote URL required", "REMOTE_REQUIRED")
    try:
        resp = httpx.delete(f"{url}/codecortex-api/v1/path-map/{args_ns.mapping_id}",
                            headers=_remote_headers(), timeout=10)
        return ok("Mapping removed", resp.json())
    except Exception as e:
        return err(f"Remote unmap failed: {e}", "REMOTE_ERROR")


def cmd_remote_resolve(args_ns: argparse.Namespace) -> Dict:
    import httpx
    url = _remote_url(args_ns)
    if not url:
        return err("--remote URL required", "REMOTE_REQUIRED")
    device_path = str(Path(args_ns.device_path).resolve())
    try:
        resp = httpx.post(f"{url}/codecortex-api/v1/resolve-path", json={
            "device_id": _get_device_id(),
            "device_path": device_path,
        }, headers=_remote_headers(), timeout=10)
        return ok("Path resolution", resp.json())
    except Exception as e:
        return err(f"Resolve failed: {e}", "REMOTE_ERROR")


COMMANDS = {
    "path-map": cmd_remote_path_map,
    "list": cmd_remote_list,
    "unmap": cmd_remote_unmap,
    "resolve": cmd_remote_resolve,
}


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("remote", help="Remote server — path mapping and execution")
    p.add_argument("--remote", help="Server URL (default: $CODECORTEX_REMOTE)")
    sp = p.add_subparsers(dest="remote_action", required=True)

    m = sp.add_parser("path-map", help="Register device-to-server path mapping")
    m.add_argument("device_path", help="Local path on this device")
    m.add_argument("server_path", help="Corresponding path on the server")
    m.add_argument("--remote", help="Server URL")

    sp.add_parser("list", help="List path mappings").add_argument("--remote", help="Server URL")

    u = sp.add_parser("unmap", help="Remove a path mapping")
    u.add_argument("mapping_id", help="Mapping ID to remove")
    u.add_argument("--remote", help="Server URL")

    r = sp.add_parser("resolve", help="Resolve a device path to server path")
    r.add_argument("device_path", help="Local path to resolve")
    r.add_argument("--remote", help="Server URL")
