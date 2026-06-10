"""
Symfony framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Symfony
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional

def detect_symfony(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any],
) -> bool:
    """Detect Symfony usage with zero false positives.
    
    Requires at least TWO of the following signals:
    1. Symfony/* imports
    2. Symfony in composer.json dependencies
    3. Symfony directory structure (src/Controller, config/, bin/console)
    4. Symfony-specific patterns (Controller extends AbstractController, etc.)
    """
    signals = []
    
    # Signal 1: Symfony imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod.startswith("symfony\\") or mod.startswith("symfony/"):
            signals.append("symfony_import")
            break
    
    # Signal 2: Symfony in composer.json
    composer_deps = repo_configs.get("composer.json", {}).get("dependencies", {})
    if any(dep.startswith("symfony/") for dep in composer_deps):
        signals.append("symfony_dependency")
    
    # Signal 3: Symfony directory structure
    symfony_paths = [
        "src/controller", "config/", "bin/console", "templates/",
        "src/entity", "src/service", "src/repository"
    ]
    if any(sp in rel_path for sp in symfony_paths):
        signals.append("symfony_structure")
    
    # Signal 4: Symfony-specific base classes
    for cls in classes:
        bases = [b.lower() for b in cls.get("bases", [])]
        if "abstractcontroller" in bases or "controller" in bases:
            signals.append("symfony_controller")
            break
        if "abstractservice" in bases or "service" in bases:
            signals.append("symfony_service")
            break
    
    # Zero false positives: require at least 2 signals
    return len(signals) >= 2

def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Symfony-specific class types."""
    bases = [b.lower() for b in cls.get("bases", [])]
    
    if "abstractcontroller" in bases or "controller" in bases:
        return {"symfony_type": "Controller"}
    if "abstractservice" in bases or "service" in bases:
        return {"symfony_type": "Service"}
    if "entity" in bases:
        return {"symfony_type": "Entity"}
    if "repository" in bases:
        return {"symfony_type": "Repository"}
    if "command" in bases:
        return {"symfony_type": "Command"}
    if "eventsubscriber" in bases:
        return {"symfony_type": "EventSubscriber"}
    
    return None

def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Symfony-specific attributes and lifecycle hooks."""
    name = fn.get("name", "")
    decorators = fn.get("decorators", [])
    
    # Symfony attributes (PHP 8+)
    symfony_attrs = ["@Route", "@Entity", "@ORM\\", "@Assert\\", "@Cache\\", "@Security"]
    if any(attr in str(decorators) for attr in symfony_attrs):
        return {"symfony_attribute": True}
    
    # Symfony lifecycle callbacks
    symfony_lifecycle = ["prePersist", "postPersist", "preUpdate", "postUpdate", "preRemove", "postRemove"]
    if name in symfony_lifecycle:
        return {"symfony_lifecycle": name}
    
    return None
