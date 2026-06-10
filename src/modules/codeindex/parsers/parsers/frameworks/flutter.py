"""
Flutter framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Flutter
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional

def detect_flutter(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any] = None,
) -> bool:
    """Detect Flutter usage with maximum coverage.
    
    Requires at least ONE of the following signals:
    1. Flutter imports
    2. Widget subclasses
    3. Flutter in pubspec.yaml
    4. Flutter-specific directory structure (lib/)
    """
    if repo_configs is None:
        repo_configs = {}
    
    signals = []
    
    # Signal 1: Flutter imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if "flutter" in mod or "material.dart" in mod:
            signals.append("flutter_import")
            break
    
    # Signal 2: Widget subclasses
    for cls in classes:
        bases = [b.lower() for b in cls.get("bases", [])]
        if any(b in ("statelesswidget", "statefulwidget", "widget") for b in bases):
            signals.append("widget_subclass")
            break
    
    # Signal 3: Flutter in pubspec.yaml
    pubspec_deps = repo_configs.get("pubspec.yaml", {}).get("dependencies", {})
    if "flutter" in pubspec_deps or "flutter_sdk" in pubspec_deps:
        signals.append("flutter_pubspec")
    
    # Signal 4: Flutter directory structure
    if "lib/" in rel_path and rel_path.endswith(".dart"):
        signals.append("flutter_structure")
    
    # Maximum coverage: require at least 1 signal
    return len(signals) >= 1

def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Flutter Widget subclasses."""
    bases = [b.lower() for b in cls.get("bases", [])]
    if "statelesswidget" in bases:
        return {"widget_type": "StatelessWidget"}
    if "statefulwidget" in bases:
        return {"widget_type": "StatefulWidget"}
    if "widget" in bases:
        return {"widget_type": "Widget"}
    return None

def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Flutter build methods."""
    name = fn.get("name", "")
    if name == "build":
        return {"widget_method": "build"}
    return None
