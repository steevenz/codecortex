"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.services
:standard: CODDY-IdeGraph-v1.0

IdeHarvest — Harvests IDE configurations, settings, MCP configs, and extensions.
"""

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.modules.idegraph.core.logging_service import get_logger
from src.modules.idegraph.domain.engram import IDEInfo
from src.modules.idegraph.services.storage import Storage

logger = get_logger(__name__)


def _safe_read_text(path: Path, *, max_bytes: int = 2_000_000) -> Optional[str]:
    try:
        if not path.exists() or not path.is_file():
            return None
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except (PermissionError, OSError):
        return None


def _safe_read_json(path: Path, *, max_bytes: int = 5_000_000) -> Optional[Any]:
    raw = _safe_read_text(path, max_bytes=max_bytes)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _flatten_json(value: Any, *, max_depth: int = 4, prefix: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    def rec(v: Any, p: str, depth: int) -> None:
        if depth > max_depth:
            return
        if isinstance(v, dict):
            for k, vv in v.items():
                if not isinstance(k, str):
                    continue
                rec(vv, f"{p}.{k}" if p else k, depth + 1)
            return
        if isinstance(v, list):
            if len(v) <= 50:
                out[p] = v
            return
        out[p] = v
    rec(value, prefix, 0)
    return out


def _parse_extension_dir_name(dirname: str) -> Tuple[str, Optional[str], Optional[str]]:
    name = dirname
    publisher = None
    version = None
    parts = dirname.rsplit("-", 1)
    if len(parts) == 2:
        left, right = parts
        if any(ch.isdigit() for ch in right):
            name = left
            version = right
    if "." in name:
        publisher, ext = name.split(".", 1)
        name = ext
    return name, publisher, version


class IdeHarvest:
    def __init__(self, storage: Storage):
        self.storage = storage

    def harvest_workspace_settings(self, *, ide_name: str, ide_id: str, request_id: str) -> Dict[str, Any]:
        counts = {"workspaces_seen": 0, "workspace_settings_upserted": 0, "workspace_extensions_upserted": 0}
        workspaces = self.storage.list_workspaces(include_engram_count=False)
        for ws in workspaces:
            project_path = ws.get("project_path")
            workspace_key = ws.get("workspace_key")
            if not project_path or not workspace_key:
                continue
            ws_path = Path(project_path)
            if not ws_path.exists() or not ws_path.is_dir():
                continue
            counts["workspaces_seen"] += 1
            ws_instance_id = self.storage.get_any_workspace_instance_id(workspace_id=workspace_key, ide_id=ide_id)
            if ws_instance_id is None:
                ws_instance_id = self.storage.ensure_workspace_instance(
                    workspace_id=workspace_key, ide_id=ide_id,
                    ide_workspace_id=f"path:{project_path}", source_file=None,
                )
            vscode_dir = ws_path / ".vscode"
            settings_path = vscode_dir / "settings.json"
            extensions_path = vscode_dir / "extensions.json"
            settings = _safe_read_json(settings_path)
            if isinstance(settings, dict):
                if self.storage.upsert_configuration(scope=f"workspace:{workspace_key}", key="vscode_settings_json", value=settings, source_file=str(settings_path)):
                    counts["workspace_settings_upserted"] += 1
                for k, v in _flatten_json(settings, max_depth=4).items():
                    if self.storage.upsert_ide_setting(ide_id=ide_id, workspace_instance_id=ws_instance_id, key=f"workspace.vscode.{k}", value=v, source_file=str(settings_path)):
                        counts["workspace_settings_upserted"] += 1
            extensions = _safe_read_json(extensions_path)
            if extensions is not None:
                if self.storage.upsert_configuration(scope=f"workspace:{workspace_key}", key="vscode_extensions_json", value=extensions, source_file=str(extensions_path)):
                    counts["workspace_extensions_upserted"] += 1
            for code_ws in ws_path.glob("*.code-workspace"):
                doc = _safe_read_json(code_ws)
                if not isinstance(doc, dict):
                    continue
                if self.storage.upsert_configuration(scope=f"workspace:{workspace_key}", key=f"code_workspace:{code_ws.name}", value=doc, source_file=str(code_ws)):
                    counts["workspace_settings_upserted"] += 1
                settings_obj = doc.get("settings")
                if isinstance(settings_obj, dict):
                    for k, v in _flatten_json(settings_obj, max_depth=4).items():
                        if self.storage.upsert_ide_setting(ide_id=ide_id, workspace_instance_id=ws_instance_id, key=f"workspace.code_workspace.{code_ws.name}.{k}", value=v, source_file=str(code_ws)):
                            counts["workspace_settings_upserted"] += 1
        return counts

    def harvest_installations(self, *, ide_name: str, ide_type: str, installations: Iterable[Path], request_id: str) -> Dict[str, Any]:
        counts = {"installations_seen": 0, "configurations_upserted": 0, "ide_settings_upserted": 0, "ide_extensions_upserted": 0, "mcp_settings_upserted": 0}
        for inst in installations:
            counts["installations_seen"] += 1
            ide_info = IDEInfo(name=ide_name, type=ide_type, installation_path=str(inst))
            ide_id = self.storage.ensure_ide(ide_info, source=ide_name)
            user_dir = inst / "User"
            settings_path = user_dir / "settings.json"
            keybindings_path = user_dir / "keybindings.json"
            extensions_json_path = user_dir / "extensions.json"
            settings = _safe_read_json(settings_path)
            if isinstance(settings, dict):
                if self.storage.upsert_configuration(scope=f"ide:{ide_name}:user", key="settings_json", value=settings, source_file=str(settings_path)):
                    counts["configurations_upserted"] += 1
                for k, v in _flatten_json(settings, max_depth=4).items():
                    if self.storage.upsert_ide_setting(ide_id=ide_id, key=k, value=v, source_file=str(settings_path)):
                        counts["ide_settings_upserted"] += 1
                mcp_subset = {k: v for k, v in settings.items() if "mcp" in k.lower() or "modelcontextprotocol" in k.lower()}
                if mcp_subset:
                    if self.storage.upsert_mcp_settings(scope=f"{ide_name}:user", settings=mcp_subset, ide_id=ide_id, source_file=str(settings_path)):
                        counts["mcp_settings_upserted"] += 1
            keybindings = _safe_read_json(keybindings_path)
            if keybindings is not None:
                if self.storage.upsert_configuration(scope=f"ide:{ide_name}:user", key="keybindings_json", value=keybindings, source_file=str(keybindings_path)):
                    counts["configurations_upserted"] += 1
            extensions_json = _safe_read_json(extensions_json_path)
            if extensions_json is not None:
                if self.storage.upsert_configuration(scope=f"ide:{ide_name}:user", key="extensions_json", value=extensions_json, source_file=str(extensions_json_path)):
                    counts["configurations_upserted"] += 1
            for ext_dir in self._candidate_extensions_dirs(ide_name=ide_name, installation=inst):
                if not ext_dir.exists() or not ext_dir.is_dir():
                    continue
                try:
                    for child in ext_dir.iterdir():
                        if not child.is_dir():
                            continue
                        manifest = _safe_read_json(child / "package.json")
                        ext_name: Optional[str] = None
                        publisher: Optional[str] = None
                        ver: Optional[str] = None
                        metadata: Dict[str, Any] = {"dir": str(child)}
                        if isinstance(manifest, dict):
                            raw_name = manifest.get("name")
                            raw_publisher = manifest.get("publisher")
                            raw_version = manifest.get("version")
                            if isinstance(raw_name, str) and raw_name:
                                ext_name = raw_name
                            if isinstance(raw_publisher, str) and raw_publisher:
                                publisher = raw_publisher
                            if isinstance(raw_version, str) and raw_version:
                                ver = raw_version
                            for k in ("displayName", "description", "engines", "categories", "keywords"):
                                if k in manifest:
                                    metadata[k] = manifest.get(k)
                        if not ext_name:
                            parsed_name, parsed_publisher, parsed_version = _parse_extension_dir_name(child.name)
                            ext_name = parsed_name
                            publisher = publisher or parsed_publisher
                            ver = ver or parsed_version
                        if self.storage.upsert_ide_extension(ide_id=ide_id, name=ext_name, publisher=publisher, extension_version=ver, enabled=True, metadata=metadata):
                            counts["ide_extensions_upserted"] += 1
                except PermissionError:
                    pass
                except OSError:
                    pass
        return counts

    def _candidate_extensions_dirs(self, *, ide_name: str, installation: Path) -> List[Path]:
        home = Path.home()
        userprofile = os.environ.get("USERPROFILE")
        user_home = Path(userprofile) if userprofile else home
        candidates = [installation / "extensions", installation.parent / "extensions"]
        dot_dir = user_home / f".{ide_name}"
        candidates.append(dot_dir / "extensions")
        if ide_name == "cursor":
            candidates.append(user_home / ".cursor" / "extensions")
        if ide_name == "trae":
            candidates.append(user_home / ".trae" / "extensions")
        if ide_name == "windsurf":
            candidates.append(user_home / ".windsurf" / "extensions")
        candidates.append(user_home / ".vscode" / "extensions")
        uniq: List[Path] = []
        seen = set()
        for c in candidates:
            s = str(c)
            if s in seen:
                continue
            seen.add(s)
            uniq.append(c)
        return uniq
