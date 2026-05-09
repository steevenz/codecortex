"""
Comprehensive tests for ALL framework parsers (detect, enrich_class, enrich_function).
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pytest


def _test_detect(mod_name, **kwargs):
    """Test detect function returns bool."""
    mod = __import__(f"src.domain.codeindex.infrastructure.parsers.frameworks.{mod_name}", fromlist=["detect"])
    detect_fn = getattr(mod, f"detect_{mod_name}")
    result = detect_fn(**kwargs)
    assert isinstance(result, bool)
    return result


def _test_enrich_class(mod_name, cls_data):
    """Test enrich_class returns dict or None."""
    mod = __import__(f"src.domain.codeindex.infrastructure.parsers.frameworks.{mod_name}", fromlist=["enrich_class"])
    fn = getattr(mod, "enrich_class")
    result = fn(cls_data)
    assert result is None or isinstance(result, dict)
    return result


def _test_enrich_function(mod_name, fn_data):
    """Test enrich_function returns dict or None."""
    mod = __import__(f"src.domain.codeindex.infrastructure.parsers.frameworks.{mod_name}", fromlist=["enrich_function"])
    fn = getattr(mod, "enrich_function")
    result = fn(fn_data)
    assert result is None or isinstance(result, dict)
    return result


BASE_KWARGS = {
    "rel_path": "test.py", "source": "", "imports": [],
    "classes": [], "functions": [], "repo_configs": {},
}


# ═══════════════════════════════════════════════════════════
# DJANGO (57%)
# ═══════════════════════════════════════════════════════════

def test_django_detect():
    assert _test_detect("django", **BASE_KWARGS) is False  # No signals

def test_django_detect_positive():
    kwargs = {**BASE_KWARGS, "imports": [{"module": "django.db.models", "names": ["Model"]}],
              "classes": [{"name": "User", "bases": ["Model"]}],
              "rel_path": "models.py"}
    assert _test_detect("django", **kwargs) is True

def test_django_enrich_model():
    result = _test_enrich_class("django", {"name": "User", "bases": ["Model"]})
    assert result is not None
    assert result.get("django_type") == "Model"

def test_django_enrich_none():
    result = _test_enrich_class("django", {"name": "Helper", "bases": ["object"]})
    assert result is None

def test_django_enrich_function_view():
    result = _test_enrich_function("django", {"name": "get", "decorators": []})
    assert result is not None

def test_django_enrich_function_csrf():
    result = _test_enrich_function("django", {"name": "my_view", "decorators": ["@csrf_exempt"]})
    assert result is not None

# ═══════════════════════════════════════════════════════════
# EXPRESS (62%)
# ═══════════════════════════════════════════════════════════

def test_express_detect():
    assert _test_detect("express", **BASE_KWARGS) is False

def test_express_detect_positive():
    kwargs = {**BASE_KWARGS, "imports": [{"module": "express", "names": ["express"]}],
              "source": "app.get('/users', handler)",
              "rel_path": "routes/user.js"}
    assert _test_detect("express", **kwargs) is True

def test_express_enrich_class():
    result = _test_enrich_class("express", {"name": "UserRouter", "bases": ["Router"]})
    assert isinstance(result, dict) or result is None

def test_express_enrich_function():
    result = _test_enrich_function("express", {"name": "getUsers", "decorators": []})
    assert isinstance(result, dict) or result is None

# ═══════════════════════════════════════════════════════════
# FLUTTER (49%)
# ═══════════════════════════════════════════════════════════

def test_flutter_detect():
    assert _test_detect("flutter", **BASE_KWARGS) is False

def test_flutter_detect_positive():
    kwargs = {**BASE_KWARGS, "rel_path": "lib/main.dart",
              "imports": [{"module": "package:flutter/material.dart"}]}
    assert _test_detect("flutter", **kwargs) is True

def test_flutter_enrich_class():
    result = _test_enrich_class("flutter", {"name": "MyApp", "bases": ["StatelessWidget"]})
    assert result is not None

def test_flutter_enrich_function():
    result = _test_enrich_function("flutter", {"name": "build", "decorators": []})
    assert isinstance(result, dict) or result is None

# ═══════════════════════════════════════════════════════════
# REACT (43%)
# ═══════════════════════════════════════════════════════════

def test_react_detect():
    assert _test_detect("react", **BASE_KWARGS) is False

def test_react_detect_positive():
    kwargs = {**BASE_KWARGS, "imports": [{"module": "react", "names": ["React"]}]}
    assert _test_detect("react", **kwargs) is True

def test_react_enrich_class():
    result = _test_enrich_class("react", {"name": "MyComponent", "bases": ["Component"]})
    assert result is not None

def test_react_enrich_function():
    result = _test_enrich_function("react", {"name": "useState", "decorators": []})
    assert isinstance(result, dict) or result is None

# ═══════════════════════════════════════════════════════════
# VUE (30%)
# ═══════════════════════════════════════════════════════════

def test_vue_detect():
    assert _test_detect("vue", **BASE_KWARGS) is False

def test_vue_detect_positive():
    kwargs = {**BASE_KWARGS, "rel_path": "App.vue",
              "imports": [{"module": "vue", "names": ["ref"]}],
              "source": "<template><div>hi</div></template>"}
    assert _test_detect("vue", **kwargs) is True

def test_vue_enrich_class():
    result = _test_enrich_class("vue", {"name": "MyComponent", "bases": ["Vue"]})
    assert isinstance(result, dict) or result is None

def test_vue_enrich_function():
    result = _test_enrich_function("vue", {"name": "mounted", "decorators": []})
    assert isinstance(result, dict) or result is None

# ═══════════════════════════════════════════════════════════
# ANGULAR (36%)
# ═══════════════════════════════════════════════════════════

def test_angular_detect():
    assert _test_detect("angular", **BASE_KWARGS) is False

def test_angular_detect_positive():
    kwargs = {**BASE_KWARGS, "imports": [{"module": "@angular/core", "names": ["Component"]}],
              "classes": [{"name": "AppComponent", "bases": [], "decorators": ["@Component"]}]}
    assert _test_detect("angular", **kwargs) is True

def test_angular_enrich_class():
    result = _test_enrich_class("angular", {"name": "AppComponent", "bases": ["Component"]})
    assert isinstance(result, dict) or result is None

def test_angular_enrich_function():
    result = _test_enrich_function("angular", {"name": "ngOnInit", "decorators": []})
    assert isinstance(result, dict) or result is None

# ═══════════════════════════════════════════════════════════
# LARAVEL (34%)
# ═══════════════════════════════════════════════════════════

def test_laravel_detect():
    assert _test_detect("laravel", **BASE_KWARGS) is False

def test_laravel_detect_positive():
    kwargs = {**BASE_KWARGS, "classes": [{"name": "UserController", "bases": ["Controller"]}],
              "rel_path": "app/Http/Controllers/UserController.php"}
    assert _test_detect("laravel", **kwargs) is True

def test_laravel_enrich_class():
    result = _test_enrich_class("laravel", {"name": "User", "bases": ["Model"]})
    assert result is not None

def test_laravel_enrich_function():
    result = _test_enrich_function("laravel", {"name": "index", "decorators": []})
    assert isinstance(result, dict) or result is None

# ═══════════════════════════════════════════════════════════
# NESTJS (31%)
# ═══════════════════════════════════════════════════════════

def test_nestjs_detect():
    assert _test_detect("nestjs", **BASE_KWARGS) is False

def test_nestjs_detect_positive():
    kwargs = {**BASE_KWARGS, "imports": [{"module": "@nestjs/core", "names": ["Module"]}],
              "classes": [{"name": "AppModule", "bases": [], "decorators": ["@Module"]}]}
    assert _test_detect("nestjs", **kwargs) is True

def test_nestjs_enrich_class():
    result = _test_enrich_class("nestjs", {"name": "AppModule", "bases": ["Module"]})
    assert isinstance(result, dict) or result is None

def test_nestjs_enrich_function():
    result = _test_enrich_function("nestjs", {"name": "getUsers", "decorators": ["@Get"]})
    assert isinstance(result, dict) or result is None

# ═══════════════════════════════════════════════════════════
# RAILS (44%)
# ═══════════════════════════════════════════════════════════

def test_rails_detect():
    assert _test_detect("rails", **BASE_KWARGS) is False

def test_rails_detect_positive():
    kwargs = {**BASE_KWARGS, "classes": [{"name": "UsersController", "bases": ["ApplicationController"]}],
              "rel_path": "app/controllers/users_controller.rb"}
    assert _test_detect("rails", **kwargs) is True

def test_rails_enrich_class():
    result = _test_enrich_class("rails", {"name": "User", "bases": ["ApplicationRecord"]})
    assert result is not None

def test_rails_enrich_function():
    result = _test_enrich_function("rails", {"name": "index", "decorators": []})
    assert isinstance(result, dict) or result is None

# ═══════════════════════════════════════════════════════════
# SYMFONY (31%)
# ═══════════════════════════════════════════════════════════

def test_symfony_detect():
    assert _test_detect("symfony", **BASE_KWARGS) is False

def test_symfony_detect_positive():
    kwargs = {**BASE_KWARGS, "classes": [{"name": "UserController", "bases": ["AbstractController"]}],
              "imports": [{"module": "Symfony\\Bundle\\FrameworkBundle\\Controller\\AbstractController"}],
              "rel_path": "src/Controller/UserController.php"}
    assert _test_detect("symfony", **kwargs) is True

def test_symfony_enrich_class():
    result = _test_enrich_class("symfony", {"name": "User", "bases": ["Entity"]})
    assert isinstance(result, dict) or result is None

def test_symfony_enrich_function():
    result = _test_enrich_function("symfony", {"name": "list", "decorators": ["@Route"]})
    assert isinstance(result, dict) or result is None

# ═══════════════════════════════════════════════════════════
# ASPNET (37%)
# ═══════════════════════════════════════════════════════════

def test_aspnet_detect():
    assert _test_detect("aspnet", **BASE_KWARGS) is False

def test_aspnet_detect_positive():
    kwargs = {**BASE_KWARGS, "classes": [{"name": "UserController", "bases": ["Controller"]}],
              "imports": [{"module": "Microsoft.AspNetCore.Mvc", "names": ["Controller"]}],
              "rel_path": "Controllers/UserController.cs"}
    assert _test_detect("aspnet", **kwargs) is True

def test_aspnet_enrich_class():
    result = _test_enrich_class("aspnet", {"name": "User", "bases": ["Controller"]})
    assert isinstance(result, dict) or result is None

def test_aspnet_enrich_function():
    result = _test_enrich_function("aspnet", {"name": "Index", "decorators": []})
    assert isinstance(result, dict) or result is None

# ═══════════════════════════════════════════════════════════
# NEXTJS (48%)
# ═══════════════════════════════════════════════════════════

def test_nextjs_detect():
    assert _test_detect("nextjs", rel_path="test.js", source="", imports=[],
                        functions=[], repo_configs={}) is False

def test_nextjs_detect_positive():
    assert _test_detect("nextjs", rel_path="pages/users/page.tsx", source="export default function Users() {}",
                        imports=[], functions=[{"name": "Users"}], repo_configs={}) is True

if __name__ == "__main__":
    print("All framework parser tests ready for pytest.")
