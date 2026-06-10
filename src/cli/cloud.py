"""Cloud sync CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from src.cli.common import ok, err, _remote_headers, _get_device_id, _remote_url


def _cloud_config_dir() -> Path:
    return Path.home() / ".codecortex"


def cmd_cloud_init(args_ns: argparse.Namespace) -> Dict:
    from src.core.database.cloud_sync import load_cloud_config, save_cloud_config
    cfg = load_cloud_config()
    cfg["server_url"] = args_ns.server_url or cfg.get("server_url", "")
    cfg["device_id"] = _get_device_id()
    save_cloud_config(cfg)
    return ok("Cloud sync initialized", {
        "server_url": cfg["server_url"], "device_id": cfg["device_id"],
    })


def cmd_cloud_push(args_ns: argparse.Namespace) -> Dict:
    import httpx
    from src.core.database.cloud_sync import CloudSync, load_cloud_config, save_cloud_config, _iso_now
    from src.main import create_orchestrator

    cfg = load_cloud_config()
    server_url = cfg.get("server_url", "") or _remote_url(args_ns) or ""
    if not server_url:
        return err("Server URL not configured. Use --remote or set in ~/.codecortex/cloud.json", "CLOUD_NO_URL")
    device_id = cfg.get("device_id", "") or _get_device_id()

    orch = create_orchestrator()
    try:
        since = cfg.get("last_push_at", "2000-01-01T00:00:00")
        sync = CloudSync(orch.db.conn)
        data = sync.collect_push_data(since)
        if not data:
            return ok("Nothing to push", {"records_pushed": 0})

        from scripts.server.encryption import encrypt_payload, has_keypair
        payload = {"device_id": device_id, "data": data}
        if has_keypair():
            payload = {"device_id": device_id, "ciphertext": encrypt_payload({"data": data})}

        resp = httpx.post(
            f"{server_url}/codecortex-api/v1/cloud/push",
            json=payload,
            headers=_remote_headers(), timeout=60,
        )
        result = resp.json()
        now = _iso_now()
        cfg["last_push_at"] = now
        save_cloud_config(cfg)
        return ok("Push complete", {
            "records_pushed": result.get("records_accepted", 0),
            "tables": list(data.keys()),
            "encrypted": has_keypair(),
        })
    except httpx.ConnectError:
        return err(f"Cannot connect to server at {server_url}", "CLOUD_CONNECT_ERROR", 503)
    except Exception as e:
        return err(f"Push failed: {e}", "CLOUD_ERROR", 500)
    finally:
        orch.db.close()


def cmd_cloud_pull(args_ns: argparse.Namespace) -> Dict:
    import httpx
    from src.core.database.cloud_sync import CloudSync, load_cloud_config, save_cloud_config, _iso_now
    from src.main import create_orchestrator

    cfg = load_cloud_config()
    server_url = cfg.get("server_url", "") or _remote_url(args_ns) or ""
    if not server_url:
        return err("Server URL not configured", "CLOUD_NO_URL")
    device_id = cfg.get("device_id", "") or _get_device_id()

    since = getattr(args_ns, "since", None) or cfg.get("last_pull_at", "2000-01-01T00:00:00")
    orch = create_orchestrator()
    try:
        resp = httpx.post(
            f"{server_url}/codecortex-api/v1/cloud/pull",
            json={"device_id": device_id, "since": since},
            headers=_remote_headers(), timeout=60,
        )
        result = resp.json()
        if not result.get("success"):
            return err(result.get("message", "Pull failed"), "CLOUD_PULL_ERROR")

        from scripts.server.encryption import decrypt_payload, has_keypair
        data = result.get("data", {})
        if not data and result.get("ciphertext") and has_keypair():
            decrypted = decrypt_payload(result["ciphertext"])
            if decrypted:
                data = decrypted.get("data", {})

        if not data:
            return ok("Nothing to pull", {"records_received": 0})
        sync = CloudSync(orch.db.conn)
        count = sync.apply_push_data(data, device_id)
        now = _iso_now()
        cfg["last_pull_at"] = now
        save_cloud_config(cfg)
        return ok("Pull complete", {
            "records_received": count,
            "tables": list(data.keys()),
        })
    except httpx.ConnectError:
        return err(f"Cannot connect to server at {server_url}", "CLOUD_CONNECT_ERROR", 503)
    except Exception as e:
        return err(f"Pull failed: {e}", "CLOUD_ERROR", 500)
    finally:
        orch.db.close()


def cmd_cloud_sync(args_ns: argparse.Namespace) -> Dict:
    push = cmd_cloud_push(args_ns)
    if not push.get("success"):
        return push
    pull = cmd_cloud_pull(args_ns)
    return ok("Sync complete", {
        "pushed": push.get("data", {}).get("records_pushed", 0),
        "pulled": pull.get("data", {}).get("records_received", 0),
    })


def cmd_cloud_status(args_ns: argparse.Namespace) -> Dict:
    import httpx
    from src.core.database.cloud_sync import load_cloud_config, CloudSync
    from src.main import create_orchestrator

    cfg = load_cloud_config()
    server_url = cfg.get("server_url", "") or _remote_url(args_ns) or ""
    device_id = cfg.get("device_id", "") or _get_device_id()

    orch = create_orchestrator()
    try:
        local_sync = CloudSync(orch.db.conn)
        local_status = local_sync.get_status(device_id)
        remote_status = {}
        if server_url:
            try:
                resp = httpx.get(
                    f"{server_url}/codecortex-api/v1/cloud/status",
                    params={"device_id": device_id},
                    headers=_remote_headers(), timeout=10,
                )
                remote_status = resp.json()
            except Exception:
                remote_status = {"error": "Could not reach server"}
        return ok("Cloud sync status", {
            "device_id": device_id,
            "server_url": server_url,
            "last_push_at": cfg.get("last_push_at", "never"),
            "last_pull_at": cfg.get("last_pull_at", "never"),
            "local": local_status.get("local", {}),
            "remote": remote_status,
        })
    finally:
        orch.db.close()


COMMANDS = {
    "init": cmd_cloud_init,
    "push": cmd_cloud_push,
    "pull": cmd_cloud_pull,
    "sync": cmd_cloud_sync,
    "status": cmd_cloud_status,
}


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("cloud", help="Cloud sync — git-style push/pull portable data")
    sp = p.add_subparsers(dest="cloud_action", required=True)

    i = sp.add_parser("init", help="Initialize cloud sync with server")
    i.add_argument("server_url", help="Server URL (e.g. http://server:8001)")

    sp.add_parser("push", help="Upload local portable data to server")

    pu = sp.add_parser("pull", help="Download remote data from server")
    pu.add_argument("--since", help="ISO timestamp to pull from (default: last pull)")

    sp.add_parser("sync", help="Push then pull (bi-directional sync)")

    sp.add_parser("status", help="Show sync status")
