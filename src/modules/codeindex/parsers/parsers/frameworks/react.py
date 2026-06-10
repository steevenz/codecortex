"""
React framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.React
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional

def detect_react(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any],
) -> bool:
    """Detect React usage with maximum coverage.
    
    Requires at least ONE of the following signals:
    1. React import from 'react' or 'react-dom'
    2. JSX/TSX file extension
    3. React in package.json dependencies
    4. Component base class or function component pattern
    """
    signals = []
    
    # Signal 1: React imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod == "react" or mod == "react-dom" or mod.startswith("react/"):
            signals.append("react_import")
            break
    
    # Signal 2: JSX/TSX extension
    if rel_path.endswith((".jsx", ".tsx")):
        signals.append("jsx_extension")
    
    # Signal 3: package.json dependency
    pkg_deps = repo_configs.get("package.json", {}).get("dependencies", {})
    if "react" in pkg_deps:
        signals.append("react_dependency")
    
    # Signal 4: Component pattern (class extending Component or function returning JSX)
    for cls in classes:
        bases = [b.lower() for b in cls.get("bases", [])]
        if "component" in bases or "react.component" in bases:
            signals.append("react_component_class")
            break
    
    # Check for functional component pattern (function returning JSX-like content)
    for fn in functions:
        if fn.get("decorators"):
            for dec in fn.get("decorators", []):
                if dec in ["@Component", "@ReactComponent"]:
                    signals.append("react_decorator")
                    break
    
    # Maximum coverage: require at least 1 signal
    return len(signals) >= 1

def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag React-specific class types."""
    bases = [b.lower() for b in cls.get("bases", [])]
    if "component" in bases or "react.component" in bases:
        return {"react_type": "Component"}
    if "purecomponent" in bases or "react.purecomponent" in bases:
        return {"react_type": "PureComponent"}
    return None

def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag React-specific functions (hooks, component functions)."""
    name = fn.get("name", "")
    decorators = fn.get("decorators", [])
    
    # React hooks
    if name.startswith("use"):
        common_hooks = ["useState", "useEffect", "useContext", "useReducer", "useCallback", "useMemo", "useRef", "useLayoutEffect", "useImperativeHandle"]
        if name in common_hooks:
            return {"react_hook": name}
    
    # Functional component (has JSX return pattern or component decorator)
    if "@Component" in decorators or "@ReactComponent" in decorators:
        return {"react_functional_component": True}
    
    return None
