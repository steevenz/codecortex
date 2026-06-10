"""
Astro framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Astro
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional


def detect_astro(
    rel_path: str,
    source: str,
    imports: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any] = None,
) -> bool:
    """Detect Astro framework usage.

    Signals:
    1. .astro file extension
    2. astro.config.* file
    3. import from 'astro' or 'astro:*'
    4. astro in package.json
    """
    if repo_configs is None:
        repo_configs = {}

    signals = []

    # Signal 1: .astro file
    if rel_path.endswith(".astro"):
        signals.append("astro_file")

    # Signal 2: astro config file
    if "astro.config." in rel_path:
        signals.append("astro_config")

    # Signal 3: imports from astro namespace
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod == "astro" or mod.startswith("astro:") or mod.startswith("astro/"):
            signals.append("astro_import")
            break

    # Signal 4: package.json dependency
    pkg_deps = {
        **repo_configs.get("package.json", {}).get("dependencies", {}),
        **repo_configs.get("package.json", {}).get("devDependencies", {}),
    }
    if "astro" in pkg_deps:
        signals.append("astro_dependency")

    return len(signals) >= 1


def enrich_function(fn: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    """Tag Astro special functions."""
    name = fn.get("name", "")
    if name in ("getStaticPaths", "getStaticProps"):
        return {"astro_special": name}
    return None


def enrich_class(cls: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    return None
