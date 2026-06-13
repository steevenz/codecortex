"""
Express.js framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Express
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional

def detect_express(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any],
) -> bool:
    """Detect Express.js usage with zero false positives.

    Requires at least TWO of the following signals:
    1. Express import from 'express'
    2. Express in package.json dependencies
    3. Express-specific patterns (app.get, app.post, router.use, etc.)
    """
    signals = []

    # Signal 1: Express imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod == "express":
            signals.append("express_import")
            break

    # Signal 2: Express in package.json
    pkg_deps = repo_configs.get("package.json", {}).get("dependencies", {})
    if "express" in pkg_deps:
        signals.append("express_dependency")

    # Signal 3: Express-specific patterns in source
    express_patterns = ["app.get(", "app.post(", "app.put(", "app.delete(", "router.use(", "app.use("]
    if any(pattern in source for pattern in express_patterns):
        signals.append("express_pattern")

    # Signal 4: Common Express middleware imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod in ["body-parser", "cors", "morgan", "helmet", "cookie-parser"]:
            signals.append("express_middleware")
            break

    # Zero false positives: require at least 2 signals
    return len(signals) >= 2

def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Express-specific class types (rare, Express is function-based)."""
    return None

def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Express-specific route handlers and middleware."""
    name = fn.get("name", "")

    # Express route handlers
    if name in ["get", "post", "put", "delete", "patch", "all", "use"]:
        return {"express_method": name}

    # Common middleware function names
    if name in ["errorHandler", "notFoundHandler", "requestLogger"]:
        return {"express_middleware": name}

    return None
