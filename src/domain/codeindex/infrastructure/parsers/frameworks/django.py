"""Django framework detection and symbol enrichment."""
from typing import Dict, List, Any, Optional


def detect_django(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any],
) -> bool:
    """Detect Django usage with zero false positives.
    
    Requires at least TWO of the following signals:
    1. Django imports (django.*, django.db.models, etc.)
    2. Django in requirements.txt/pyproject.toml
    3. Django directory structure (apps/, manage.py, settings.py)
    4. Django-specific patterns (Model class inheritance, @csrf_exempt, etc.)
    """
    signals = []
    
    # Signal 1: Django imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod.startswith("django.") or mod == "django":
            signals.append("django_import")
            break
    
    # Signal 2: Django in dependencies
    req_deps = repo_configs.get("requirements.txt", {}).get("dependencies", {})
    if "django" in req_deps:
        signals.append("django_dependency")
    
    # Signal 3: Django directory structure
    django_paths = [
        "manage.py", "settings.py", "urls.py", "wsgi.py", "asgi.py",
        "apps/", "migrations/", "templates/"
    ]
    if any(dp in rel_path for dp in django_paths):
        signals.append("django_structure")
    
    # Signal 4: Django Model inheritance
    for cls in classes:
        bases = [b.lower() for b in cls.get("bases", [])]
        if "models.model" in bases or "model" in bases:
            signals.append("django_model")
            break
    
    # Signal 5: Django decorators
    for fn in functions:
        decorators = fn.get("decorators", [])
        django_decorators = ["@csrf_exempt", "@login_required", "@permission_required", "@require_http_methods"]
        if any(dec in decorators for dec in django_decorators):
            signals.append("django_decorator")
            break
    
    # Zero false positives: require at least 2 signals
    return len(signals) >= 2


def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Django-specific class types."""
    bases = [b.lower() for b in cls.get("bases", [])]
    
    if "models.model" in bases or "model" in bases:
        return {"django_type": "Model"}
    if "view" in bases or "templateview" in bases:
        return {"django_type": "View"}
    if "form" in bases or "modelform" in bases:
        return {"django_type": "Form"}
    if "modeladmin" in bases:
        return {"django_type": "ModelAdmin"}
    if "middleware" in bases:
        return {"django_type": "Middleware"}
    
    return None


def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Django-specific functions and decorators."""
    decorators = fn.get("decorators", [])
    name = fn.get("name", "")
    
    # Django decorators
    if "@csrf_exempt" in decorators:
        return {"django_decorator": "csrf_exempt"}
    if "@login_required" in decorators:
        return {"django_decorator": "login_required"}
    if "@permission_required" in decorators:
        return {"django_decorator": "permission_required"}
    
    # Django view patterns
    if name in ["get", "post", "put", "delete", "patch"]:
        # Could be a class-based view method
        return {"django_view_method": name}
    
    return None
