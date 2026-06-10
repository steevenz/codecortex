"""
Next.js framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Nextjs
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional

def detect_nextjs(
    rel_path: str,
    source: str,
    imports: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any] = None,
) -> bool:
    """Detect Next.js usage with maximum coverage.
    
    Requires at least ONE of the following signals:
    1. Next.js file patterns (page.tsx, layout.tsx, etc.)
    2. Next.js imports (next/*)
    3. Next.js in package.json
    """
    if repo_configs is None:
        repo_configs = {}
    
    signals = []
    
    # Signal 1: Next.js file patterns
    nextjs_file_patterns = [
        "page.tsx", "page.ts", "page.jsx", "page.js",
        "layout.tsx", "layout.ts", "layout.jsx", "layout.js",
        "route.tsx", "route.ts", "route.jsx", "route.js",
        "loading.tsx", "error.tsx", "not-found.tsx",
        "middleware.ts", "middleware.js",
    ]
    if any(rel_path.endswith(p) for p in nextjs_file_patterns):
        signals.append("nextjs_file_pattern")
    
    # Signal 2: Next.js imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod.startswith("next/"):
            signals.append("nextjs_import")
            break
    
    # Signal 3: Next.js in package.json
    pkg_deps = repo_configs.get("package.json", {}).get("dependencies", {})
    if "next" in pkg_deps:
        signals.append("nextjs_dependency")
    
    # Maximum coverage: require at least 1 signal
    return len(signals) >= 1

def detect_react(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    repo_configs: Dict[str, Any] = None,
) -> bool:
    """Next.js framework detection module.
    
    This function is kept for backward compatibility but should not be used.
    New code should import from react.py.
    """
    if repo_configs is None:
        repo_configs = {}
    
    # Import the new detector
    from . import react as react_fw
    
    return react_fw.detect_react(rel_path, source, imports, classes, [], repo_configs)

def enrich_class(cls: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    """Next.js is function-centric; no class enrichment."""
    return None

def enrich_function(fn: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    """Tag Next.js-specific functions (API route handlers, special exports)."""
    name = fn.get("name", "")
    if name in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
        return {"route_handler": True, "http_method": name}
    if name == "default" and ("route" in rel_path or "api" in rel_path):
        return {"route_handler": True}
    if name in ("generateStaticParams", "generateMetadata"):
        return {"nextjs_special": name}
    return None
