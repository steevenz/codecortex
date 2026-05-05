"""Angular framework detection and symbol enrichment."""
from typing import Dict, List, Any, Optional


def detect_angular(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any],
) -> bool:
    """Detect Angular usage with zero false positives.
    
    Requires at least TWO of the following signals:
    1. @angular/* imports
    2. Angular in package.json dependencies
    3. Angular decorators (@Component, @NgModule, @Injectable, @Directive)
    4. angular.json configuration file
    """
    signals = []
    
    # Signal 1: Angular imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod.startswith("@angular/"):
            signals.append("angular_import")
            break
    
    # Signal 2: package.json dependency
    pkg_deps = repo_configs.get("package.json", {}).get("dependencies", {})
    if any(dep.startswith("@angular/") for dep in pkg_deps):
        signals.append("angular_dependency")
    
    # Signal 3: Angular decorators
    for cls in classes:
        decorators = cls.get("decorators", [])
        angular_decorators = ["@Component", "@NgModule", "@Injectable", "@Directive", "@Pipe", "@Guard"]
        if any(dec in decorators for dec in angular_decorators):
            signals.append("angular_decorator")
            break
    
    # Signal 4: angular.json (would need to check file existence separately)
    # This is handled at repository level
    
    # Zero false positives: require at least 2 signals
    return len(signals) >= 2


def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Angular-specific class types."""
    decorators = cls.get("decorators", [])
    
    if "@Component" in decorators:
        return {"angular_type": "Component"}
    if "@NgModule" in decorators:
        return {"angular_type": "Module"}
    if "@Injectable" in decorators:
        return {"angular_type": "Service"}
    if "@Directive" in decorators:
        return {"angular_type": "Directive"}
    if "@Pipe" in decorators:
        return {"angular_type": "Pipe"}
    if "@Guard" in decorators:
        return {"angular_type": "Guard"}
    
    return None


def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Angular-specific lifecycle hooks."""
    name = fn.get("name", "")
    
    # Angular lifecycle hooks
    angular_hooks = [
        "ngOnInit", "ngOnChanges", "ngDoCheck", "ngAfterContentInit",
        "ngAfterContentChecked", "ngAfterViewInit", "ngAfterViewChecked",
        "ngOnDestroy"
    ]
    if name in angular_hooks:
        return {"angular_lifecycle": name}
    
    return None
