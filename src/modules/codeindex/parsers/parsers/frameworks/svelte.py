"""
Svelte / SvelteKit framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Svelte
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional


def detect_svelte(
    rel_path: str,
    source: str,
    imports: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any] = None,
) -> bool:
    """Detect Svelte / SvelteKit usage.

    Signals:
    1. .svelte file extension
    2. SvelteKit route file patterns (+page.svelte, +layout.svelte)
    3. import from 'svelte' or '$app/*'
    4. svelte / @sveltejs/* in package.json
    """
    if repo_configs is None:
        repo_configs = {}

    signals = []

    # Signal 1: .svelte file
    if rel_path.endswith(".svelte"):
        signals.append("svelte_file")

    # Signal 2: SvelteKit route patterns
    sk_patterns = [
        "+page.svelte", "+layout.svelte", "+error.svelte",
        "+page.ts", "+page.js", "+layout.ts", "+layout.js",
        "+page.server.ts", "+page.server.js",
        "+layout.server.ts", "+layout.server.js",
    ]
    if any(rel_path.endswith(p) for p in sk_patterns):
        signals.append("sveltekit_route")

    # Signal 3: imports from svelte or $app
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod == "svelte" or mod.startswith("svelte/") or mod.startswith("$app/"):
            signals.append("svelte_import")
            break

    # Signal 4: package.json dependency
    pkg_deps = {
        **repo_configs.get("package.json", {}).get("dependencies", {}),
        **repo_configs.get("package.json", {}).get("devDependencies", {}),
    }
    if "svelte" in pkg_deps or "@sveltejs/kit" in pkg_deps:
        signals.append("svelte_dependency")

    return len(signals) >= 1


def enrich_function(fn: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    """Tag SvelteKit special functions."""
    name = fn.get("name", "")
    if name in ("load", "actions"):
        return {"sveltekit_special": name}
    if name in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        return {"sveltekit_handler": True, "http_method": name}
    return None


def enrich_class(cls: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    return None
