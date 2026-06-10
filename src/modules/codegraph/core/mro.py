"""
MRO (Method Resolution Order) — C3 linearization for OOP inheritance.
Ported from GitNexus's mro.ts pipeline phase.

:project: CodeCortex
:package: Modules.Codegraph.Core.Mro
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger("CodeCortex.CodeGraph.MRO")

@dataclass
class ClassInfo:
    name: str
    bases: List[str]
    methods: List[str]
    file_path: str

def c3_linearize(class_name: str, heritage_map: Dict[str, List[str]]) -> List[str]:
    """
    Compute C3 linearization (MRO) for a class.

    Implements the C3 superclass linearization algorithm used by Python.
    heritage_map: class_name -> [parent_class_names]
    Returns ordered list of classes in MRO order.
    """
    def merge(lists: List[List[str]]) -> List[str]:
        result = []
        while True:
            non_empty = [l for l in lists if l]
            if not non_empty:
                return result
            
            for lst in non_empty:
                candidate = lst[0]
                # Check if candidate appears in the tail of any other list
                in_tail = False
                for other in non_empty:
                    if other is not lst and candidate in other[1:]:
                        in_tail = True
                        break
                if not in_tail:
                    result.append(candidate)
                    for l in lists:
                        if l and l[0] == candidate:
                            l.pop(0)
                    break
            else:
                # Inconsistent hierarchy
                logger.warning(f"Inconsistent MRO hierarchy for {class_name}")
                return result + [item for sublist in non_empty for item in sublist]
    
    def linearize(cname: str, visited: Set[str]) -> List[str]:
        if cname in visited:
            return [cname]
        visited.add(cname)
        bases = heritage_map.get(cname, [])
        if not bases:
            return [cname]
        parent_linearizations = [linearize(b, visited) for b in bases if b != cname]
        return [cname] + merge(parent_linearizations + [bases])
    
    return linearize(class_name, set())

def compute_mro(heritage_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Compute MRO for ALL classes in the heritage map.
    Returns: class_name -> [ordered MRO list]
    """
    mro_map: Dict[str, List[str]] = {}
    for cls_name in heritage_map:
        try:
            mro_map[cls_name] = c3_linearize(cls_name, heritage_map)
        except Exception as e:
            logger.warning(f"MRO failed for {cls_name}: {e}")
            mro_map[cls_name] = [cls_name] + heritage_map.get(cls_name, [])
    return mro_map

def detect_method_overrides(
    classes: Dict[str, ClassInfo],
    mro_map: Dict[str, List[str]]
) -> List[Dict[str, str]]:
    """
    Detect method overrides in the inheritance hierarchy.
    Returns: list of {child_class, method, parent_class}
    """
    overrides = []
    for cls_name, cls_info in classes.items():
        mro = mro_map.get(cls_name, [])
        for method in cls_info.methods:
            for ancestor in mro[1:]:  # Skip self
                if ancestor in classes:
                    anc_methods = classes[ancestor].methods
                    if method in anc_methods:
                        overrides.append({
                            "child_class": cls_name,
                            "method": method,
                            "parent_class": ancestor,
                        })
                        break
    return overrides

def build_heritage_map_from_symbols(symbols: List[Dict]) -> Dict[str, List[str]]:
    """Build heritage map from parsed symbols (classes with parents)."""
    heritage: Dict[str, List[str]] = {}
    for sym in symbols:
        if sym.get("type") == "class":
            name = sym.get("name", "")
            parents = sym.get("parents", sym.get("bases", []))
            if name:
                heritage[name] = parents
    return heritage
