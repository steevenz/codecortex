"""
Tauri framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Tauri
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional


def detect_tauri(
    rel_path: str,
    source: str,
    imports: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any] = None,
) -> bool:
    """Detect Tauri app usage (Rust + web frontend desktop framework).

    Signals:
    1. tauri.conf.json or tauri.conf.json5 exists
    2. src-tauri/ path prefix
    3. use tauri:: in Rust source
    4. import from '@tauri-apps/*' in JS/TS
    5. @tauri-apps/* in package.json
    """
    if repo_configs is None:
        repo_configs = {}

    signals = []

    # Signal 1: tauri config file
    if "tauri.conf" in rel_path:
        signals.append("tauri_config")

    # Signal 2: src-tauri path
    if rel_path.startswith("src-tauri/") or "/src-tauri/" in rel_path:
        signals.append("tauri_srcdir")

    # Signal 3: Rust tauri import
    if "use tauri::" in source or "tauri::command" in source:
        signals.append("tauri_rust_import")

    # Signal 4: JS/TS import from @tauri-apps
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod.startswith("@tauri-apps/"):
            signals.append("tauri_js_import")
            break

    # Signal 5: package.json dependency
    pkg_deps = {
        **repo_configs.get("package.json", {}).get("dependencies", {}),
        **repo_configs.get("package.json", {}).get("devDependencies", {}),
    }
    if any(k.startswith("@tauri-apps/") for k in pkg_deps):
        signals.append("tauri_dependency")

    return len(signals) >= 1


def enrich_function(fn: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    """Tag Tauri command functions."""
    decorators = fn.get("decorators", [])
    if "#[tauri::command]" in decorators or "tauri::command" in str(decorators):
        return {"tauri_command": True}
    return None


def enrich_class(cls: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    return None
