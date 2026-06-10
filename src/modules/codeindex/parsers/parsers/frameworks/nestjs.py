"""
NestJS framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Nestjs
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional

def detect_nestjs(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any],
) -> bool:
    """Detect NestJS usage with zero false positives.
    
    Requires at least TWO of the following signals:
    1. @nestjs/* imports
    2. NestJS in package.json dependencies
    3. NestJS decorators (@Controller, @Service, @Module, @Injectable)
    """
    signals = []
    
    # Signal 1: NestJS imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod.startswith("@nestjs/"):
            signals.append("nestjs_import")
            break
    
    # Signal 2: NestJS in package.json
    pkg_deps = repo_configs.get("package.json", {}).get("dependencies", {})
    if any(dep.startswith("@nestjs/") for dep in pkg_deps):
        signals.append("nestjs_dependency")
    
    # Signal 3: NestJS decorators
    for cls in classes:
        decorators = cls.get("decorators", [])
        nestjs_decorators = ["@Controller", "@Service", "@Module", "@Injectable", "@Get", "@Post", "@Put", "@Delete"]
        if any(dec in decorators for dec in nestjs_decorators):
            signals.append("nestjs_decorator")
            break
    
    # Zero false positives: require at least 2 signals
    return len(signals) >= 2

def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag NestJS-specific class types."""
    decorators = cls.get("decorators", [])
    
    if "@Controller" in decorators:
        return {"nestjs_type": "Controller"}
    if "@Service" in decorators:
        return {"nestjs_type": "Service"}
    if "@Module" in decorators:
        return {"nestjs_type": "Module"}
    if "@Injectable" in decorators:
        return {"nestjs_type": "Provider"}
    if "@Guard" in decorators:
        return {"nestjs_type": "Guard"}
    if "@Interceptor" in decorators:
        return {"nestjs_type": "Interceptor"}
    if "@Pipe" in decorators:
        return {"nestjs_type": "Pipe"}
    
    return None

def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag NestJS-specific decorators and lifecycle hooks."""
    decorators = fn.get("decorators", [])
    name = fn.get("name", "")
    
    # NestJS HTTP method decorators
    if name in ["get", "post", "put", "delete", "patch"]:
        if any(dec in decorators for dec in ["@Get", "@Post", "@Put", "@Delete", "@Patch"]):
            return {"nestjs_http_method": name}
    
    # NestJS lifecycle hooks
    nestjs_hooks = ["onModuleInit", "onModuleDestroy", "onApplicationBootstrap", "onApplicationShutdown"]
    if name in nestjs_hooks:
        return {"nestjs_lifecycle": name}
    
    return None
