"""
Laravel framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Laravel
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional

def detect_laravel(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any] = None,
) -> bool:
    """Detect Laravel usage with maximum coverage.

    Requires at least ONE of the following signals:
    1. Laravel directory structure
    2. Illuminate imports
    3. Laravel base classes
    4. Laravel in composer.json
    """
    if repo_configs is None:
        repo_configs = {}

    signals = []

    # Signal 1: Laravel directory structure
    laravel_paths = [
        "app/http/controllers",
        "app/models",
        "app/middleware",
        "app/providers",
        "routes/web.php",
        "routes/api.php",
        "app/console/commands",
        "database/migrations",
    ]
    if any(lp in rel_path for lp in laravel_paths):
        signals.append("laravel_structure")

    # Signal 2: Illuminate imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if "illuminate" in mod:
            signals.append("illuminate_import")
            break

    # Signal 3: Laravel base classes
    for cls in classes:
        bases = [b.lower() for b in cls.get("bases", [])]
        if any(
            b in ("model", "controller", "middleware", "command", "serviceprovider")
            for b in bases
        ):
            signals.append("laravel_base_class")
            break

    # Signal 4: Laravel in composer.json
    composer_deps = repo_configs.get("composer.json", {}).get("dependencies", {})
    if "laravel/framework" in composer_deps or "laravel" in composer_deps:
        signals.append("laravel_composer")

    # Maximum coverage: require at least 1 signal
    return len(signals) >= 1

def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Laravel-specific class types (Model, Controller, etc.)."""
    bases = [b.lower() for b in cls.get("bases", [])]
    if "model" in bases:
        return {"laravel_type": "Model"}
    if "controller" in bases:
        return {"laravel_type": "Controller"}
    if "middleware" in bases:
        return {"laravel_type": "Middleware"}
    if "command" in bases:
        return {"laravel_type": "Command"}
    if "serviceprovider" in bases:
        return {"laravel_type": "ServiceProvider"}
    if "migrator" in bases or "migration" in bases:
        return {"laravel_type": "Migration"}
    return None

def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Laravel-specific methods (handle, migration up/down)."""
    name = fn.get("name", "")
    if name == "handle":
        return {"laravel_method": "handle"}
    if name in ("up", "down"):
        return {"laravel_method": name, "migration_method": True}
    return None
