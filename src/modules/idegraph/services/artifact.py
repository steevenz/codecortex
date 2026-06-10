"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.services
:standard: Aegis-IdeGraph-v1.0

Artifact — Scans all known AI tool storage locations and harvests
conversations, configurations, plans, and digital artifacts.
"""

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

KNOWN_IDE_PATHS = {
    "trae": {"appdata": "Trae", "dot": ".trae"},
    "cursor": {"appdata": "Cursor", "dot": ".cursor"},
    "windsurf": {"appdata": "Windsurf", "dot": ".windsurf"},
    "codebuddy": {"appdata": "CodeBuddy", "dot": ".codebuddy"},
    "kiro": {"appdata": "Kiro", "dot": ".kiro"},
    "opencode": {"appdata": "opencode", "dot": ".opencode"},
    "opencode_desktop": {"dot": ".opencode-desktop"},
    "claude": {"dot": ".claude"},
    "gemini": {"dot": ".gemini"},
    "codex": {"dot": ".codex"},
    "continue": {"dot": ".continue"},
    "kilocode": {"dot": ".kilocode"},
    "qwen": {"dot": ".qwen"},
    "kimi": {"dot": ".kimi"},
    "verdent": {"dot": ".verdent"},
    "antigravity": {"dot": ".antigravity"},
}

ARTIFACT_EXTENSIONS = {".md", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".log", ".txt"}


class Artifact:
    def harvest_all(self) -> Dict[str, Any]:
        results = {}
        results["ides"] = self._scan_ide_installations()
        results["sqlite_dbs"] = self._scan_sqlite_databases()
        results["config_artifacts"] = self._scan_config_artifacts()
        results["session_files"] = self._scan_session_files()
        return results

    def _scan_ide_installations(self) -> Dict[str, List[str]]:
        found = {}
        for ide, paths in KNOWN_IDE_PATHS.items():
            locations = []
            if "appdata" in paths:
                apd = Path(os.environ.get("APPDATA", str(Path.home() / "AppData/Roaming")))
                candidate = apd / paths["appdata"]
                if candidate.exists():
                    locations.append(str(candidate))
            if "dot" in paths:
                candidate = Path.home() / paths["dot"]
                if candidate.exists():
                    locations.append(str(candidate))
            if locations:
                found[ide] = locations
        return found

    def _scan_sqlite_databases(self) -> List[Dict[str, Any]]:
        dbs = []
        home = Path.home()
        apd = Path(os.environ.get("APPDATA", str(home / "AppData/Roaming")))
        lcl = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData/Local")))
        search_roots = [
            apd / "Trae", apd / "Cursor", apd / "Windsurf",
            apd / "CodeBuddy", apd / "Kiro",
            home / ".claude", home / ".verdent/projects",
            lcl / "Zed", home / ".codex",
        ]
        for root in search_roots:
            if root.exists():
                for pattern in ("*.db", "*.vscdb", "*.sqlite"):
                    for db_file in root.rglob(pattern):
                        if db_file.is_file() and db_file.stat().st_size > 1000:
                            dbs.append(self._inspect_db(db_file))
        return dbs

    def _inspect_db(self, path: Path) -> Dict[str, Any]:
        info = {"path": str(path), "size": path.stat().st_size}
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            info["tables"] = tables
            info["has_itemtable"] = "ItemTable" in tables
            info["has_cursordiskkv"] = "cursorDiskKV" in tables
            if "ItemTable" in tables:
                keys = [r[0] for r in conn.execute("SELECT DISTINCT key FROM ItemTable ORDER BY key LIMIT 100")]
                info["itemtable_keys"] = keys
                info["itemtable_chat_keys"] = [k for k in keys if any(
                    x in k.lower() for x in ["chat", "session", "conversation", "agent",
                                              "composer", "message", "history", "prompt",
                                              "cascade", "windsurf", "memento", "input",
                                              "disk", "storage", "plan"]
                )]
                if info["itemtable_chat_keys"]:
                    info["has_chat_data"] = True
            conn.close()
        except Exception as e:
            info["error"] = str(e)
        return info

    def _scan_config_artifacts(self) -> List[Dict[str, Any]]:
        artifacts = []
        home = Path.home()
        skip = {".", "..", ".cache", ".local", ".npm", ".m2", ".ssh",
                ".docker", ".gradle", ".android", ".aws", ".azure"}
        for dot_dir in home.iterdir():
            if not dot_dir.is_dir() or not dot_dir.name.startswith("."):
                continue
            if dot_dir.name in skip:
                continue
            try:
                for f in dot_dir.rglob("*"):
                    if f.is_file() and f.suffix.lower() in ARTIFACT_EXTENSIONS:
                        if f.stat().st_size > 100:
                            artifacts.append({"path": str(f), "size": f.stat().st_size, "ext": f.suffix, "source": dot_dir.name})
            except (PermissionError, OSError):
                continue
        return artifacts

    def _scan_session_files(self) -> List[Dict[str, Any]]:
        sessions = []
        patterns = [
            (Path.home() / ".continue/sessions", "*.json", "continue"),
            (Path.home() / ".claude/projects", "*.jsonl", "claude"),
            (Path.home() / ".codex/sessions", "*.jsonl", "codex"),
            (Path.home() / ".qwen/projects", "*.jsonl", "qwen"),
            (Path.home() / ".kimi/sessions", "*.jsonl", "kimi"),
            (Path.home() / ".claude/sessions", "*.json", "claude_sessions"),
        ]
        for base_dir, glob_pattern, source in patterns:
            if base_dir.exists():
                for f in base_dir.rglob(glob_pattern):
                    if f.is_file() and f.stat().st_size > 100:
                        sessions.append({"path": str(f), "size": f.stat().st_size, "source": source})
        return sessions

    def generate_report(self, results: Dict[str, Any]) -> str:
        lines = []
        lines.append("# AI Artifact Harvest Report\n")
        lines.append(f"Generated: {datetime.now().isoformat()}\n")
        ides = results.get("ides", {})
        lines.append(f"## IDE Installations Found: {len(ides)}\n")
        for ide, paths in sorted(ides.items()):
            lines.append(f"- **{ide}**: {', '.join(paths)}")
        dbs = results.get("sqlite_dbs", [])
        with_chat = [d for d in dbs if d.get("has_chat_data")]
        lines.append(f"\n## SQLite Databases: {len(dbs)} ({len(with_chat)} with chat data)\n")
        for d in dbs[:20]:
            chat = " \u2705 CHAT" if d.get("has_chat_data") else ""
            lines.append(f"- {d['path']} ({d['size']/1024:.0f} KB, tables={d.get('tables', [])}){chat}")
        cfgs = results.get("config_artifacts", [])
        by_source = {}
        for c in cfgs:
            by_source.setdefault(c["source"], []).append(c)
        lines.append(f"\n## Config/Markdown Artifacts: {len(cfgs)}\n")
        for src, items in sorted(by_source.items()):
            lines.append(f"- **{src}**: {len(items)} files")
        sfiles = results.get("session_files", [])
        lines.append(f"\n## Session Files: {len(sfiles)}\n")
        for f in sfiles[:10]:
            lines.append(f"- [{f['source']}] {f['path']} ({f['size']} bytes)")
        return "\n".join(lines)
