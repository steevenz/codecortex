"""Vue.js framework detection and symbol enrichment."""
from typing import Dict, List, Any, Optional


def detect_vue(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any],
) -> bool:
    """Detect Vue.js usage with zero false positives.
    
    Requires at least TWO of the following signals:
    1. Vue import from 'vue' or '@vue/*'
    2. .vue file extension
    3. Vue in package.json dependencies
    4. Vue-specific decorators (@Component, @Prop, @Watch)
    """
    signals = []
    
    # Signal 1: Vue imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod == "vue" or mod.startswith("@vue/") or mod.startswith("vue-"):
            signals.append("vue_import")
            break
    
    # Signal 2: .vue file extension
    if rel_path.endswith(".vue"):
        signals.append("vue_extension")
    
    # Signal 3: package.json dependency
    pkg_deps = repo_configs.get("package.json", {}).get("dependencies", {})
    if "vue" in pkg_deps:
        signals.append("vue_dependency")
    
    # Signal 4: Vue decorators
    for fn in functions:
        decorators = fn.get("decorators", [])
        vue_decorators = ["@Component", "@Prop", "@Watch", "@Emit", "@Ref", "@Inject", "@Provide"]
        if any(dec in decorators for dec in vue_decorators):
            signals.append("vue_decorator")
            break
    
    # Signal 5: Vue class extends Vue
    for cls in classes:
        bases = [b.lower() for b in cls.get("bases", [])]
        if "vue" in bases or "component" in bases:
            signals.append("vue_class")
            break
    
    # Zero false positives: require at least 2 signals
    return len(signals) >= 2


def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Vue-specific class types."""
    bases = [b.lower() for b in cls.get("bases", [])]
    if "vue" in bases:
        return {"vue_type": "VueComponent"}
    return None


def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Vue-specific functions and lifecycle hooks."""
    name = fn.get("name", "")
    decorators = fn.get("decorators", [])
    
    # Vue lifecycle hooks
    vue_hooks = [
        "beforeCreate", "created", "beforeMount", "mounted",
        "beforeUpdate", "updated", "beforeUnmount", "unmounted",
        "onBeforeMount", "onMounted", "onBeforeUpdate", "onUpdated",
        "onBeforeUnmount", "onUnmounted"
    ]
    if name in vue_hooks:
        return {"vue_lifecycle": name}
    
    # Vue decorators
    if "@Component" in decorators:
        return {"vue_decorator": "Component"}
    if "@Prop" in decorators:
        return {"vue_decorator": "Prop"}
    if "@Watch" in decorators:
        return {"vue_decorator": "Watch"}
    
    return None
