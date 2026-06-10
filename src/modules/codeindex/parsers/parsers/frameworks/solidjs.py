"""
SolidJS framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Solidjs
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional


def detect_solidjs(
    rel_path: str,
    source: str,
    imports: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any] = None,
) -> bool:
    """Detect SolidJS usage.

    Signals:
    1. import from 'solid-js' or '@solidjs/*'
    2. solid-js in package.json
    3. .jsx / .tsx with SolidJS-specific primitives in source
    """
    if repo_configs is None:
        repo_configs = {}

    signals = []

    # Signal 1: SolidJS imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod == "solid-js" or mod.startswith("solid-js/") or mod.startswith("@solidjs/"):
            signals.append("solidjs_import")
            break

    # Signal 2: package.json
    pkg_deps = {
        **repo_configs.get("package.json", {}).get("dependencies", {}),
        **repo_configs.get("package.json", {}).get("devDependencies", {}),
    }
    if "solid-js" in pkg_deps:
        signals.append("solidjs_dependency")

    # Signal 3: SolidJS primitives in source
    solid_primitives = ["createSignal", "createEffect", "createMemo", "createResource", "createStore"]
    if any(p in source for p in solid_primitives):
        signals.append("solidjs_primitives")

    return len(signals) >= 1


def enrich_function(fn: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    """Tag SolidJS reactive primitives."""
    name = fn.get("name", "")
    solid_primitives = {
        "createSignal": "signal",
        "createEffect": "effect",
        "createMemo": "memo",
        "createResource": "resource",
        "createStore": "store",
    }
    if name in solid_primitives:
        return {"solid_primitive": solid_primitives[name]}
    return None


def enrich_class(cls: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    return None
