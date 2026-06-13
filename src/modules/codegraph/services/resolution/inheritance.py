"""
Inheritance resolution — maps child class → parent class via INHERITS edges.
Ported from legacy codegraph tools/indexing/resolution/inheritance.py.

:project: CodeCortex
:package: Modules.Codegraph.Services.Resolution.Inheritance
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeGraph-v1.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.logging import get_logger

logger = get_logger("CodeCortex.Domain.CodeGraph.Resolution.Inheritance")

def _safe_resolve(path_str: str) -> str:
    """Normalize path safely; fall back to absolute if resolve() fails."""
    if not path_str:
        return ""
    try:
        return str(Path(path_str).resolve())
    except (OSError, RuntimeError):
        return str(Path(path_str).absolute())

def _safe_first_path(imports_map: Dict[str, List[str]], name: str) -> Optional[str]:
    """Safely get the first resolved path, guarding against empty list values."""
    if name not in imports_map:
        return None
    candidates = imports_map[name]
    return candidates[0] if candidates else None

def resolve_inheritance_link(
    class_item: Dict[str, Any],
    base_class_str: str,
    caller_file_path: str,
    local_class_names: set,
    local_imports: Dict[str, Any],
    imports_map: Dict[str, List[str]],
) -> Optional[Dict[str, Any]]:
    """
    Resolve a single base class reference to its definition file path.

    Ported from legacy codegraph with ``object`` skip and Path normalization.
    """
    if base_class_str == "object":
        return None

    # Normalize path for consistent comparison
    caller_file_path = _safe_resolve(caller_file_path)

    # 1. Local class
    if base_class_str in local_class_names:
        return {
            "child_name": class_item["name"],
            "path": caller_file_path,
            "parent_name": base_class_str,
            "resolved_parent_file_path": caller_file_path,
        }

    # 2. Local import alias
    if base_class_str in local_imports:
        import_info = local_imports[base_class_str]
        resolved_path = import_info.get("resolved_path")
        if resolved_path:
            resolved_path = _safe_resolve(resolved_path)
        resolved_name = import_info.get("resolved_name", base_class_str)
        return {
            "child_name": class_item["name"],
            "path": caller_file_path,
            "parent_name": resolved_name,
            "resolved_parent_file_path": resolved_path,
        }

    # 3. Global imports_map
    if base_class_str in imports_map:
        candidates = imports_map[base_class_str]
        resolved_path = _safe_resolve(candidates[0]) if candidates else None
        return {
            "child_name": class_item["name"],
            "path": caller_file_path,
            "parent_name": base_class_str,
            "resolved_parent_file_path": resolved_path,
        }

    # Heuristic: dotted base class
    if "." in base_class_str:
        parts = base_class_str.split(".")
        base = parts[0]
        target = parts[-1]
        if base in local_imports:
            import_info = local_imports[base]
            resolved_path = import_info.get("resolved_path")
            if resolved_path:
                resolved_path = _safe_resolve(resolved_path)
            return {
                "child_name": class_item["name"],
                "path": caller_file_path,
                "parent_name": target,
                "resolved_parent_file_path": resolved_path,
            }
        if base in imports_map:
            candidates = imports_map[base]
            resolved_path = _safe_resolve(candidates[0]) if candidates else None
            return {
                "child_name": class_item["name"],
                "path": caller_file_path,
                "parent_name": target,
                "resolved_parent_file_path": resolved_path,
            }

    return None

def build_inheritance_and_csharp_files(
    all_file_data: List[Dict[str, Any]],
    imports_map: Dict[str, List[str]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Build INHERITS edge payloads for all classes across all files.
    Returns (inheritance_links, csharp_files_for_special_handling).
    """
    inheritance_links: List[Dict[str, Any]] = []
    csharp_files: List[Dict[str, Any]] = []

    for file_data in all_file_data:
        if file_data.get("lang") == "c_sharp":
            csharp_files.append(file_data)
            continue

        caller_file_path = _safe_resolve(file_data.get("path", ""))
        local_class_names = {c.get("name", "") for c in file_data.get("classes", [])}
        local_imports: Dict[str, Any] = {}
        for imp in file_data.get("imports", []):
            name = imp.get("name", "")
            full = imp.get("full_import_name", "")
            if name and full:
                local_imports[name] = {
                    "resolved_name": name,
                    "resolved_path": _safe_first_path(imports_map, name),
                    "full_import_name": full,
                }

        for cls in file_data.get("classes", []):
            for base in cls.get("bases", []):
                link = resolve_inheritance_link(cls, base, caller_file_path, local_class_names, local_imports, imports_map)
                if link:
                    inheritance_links.append(link)

    logger.info("[INHERITS] Resolved %d inheritance links across %d files", len(inheritance_links), len(all_file_data))
    return inheritance_links, csharp_files
