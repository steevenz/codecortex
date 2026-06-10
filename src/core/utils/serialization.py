"""
Serialization utilities — recursive dataclass conversion.

:project: CodeCortex
:package: Core.Utils.Serialization
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

def to_dict(obj: Any) -> Any:
    """Recursively convert a dataclass (or nested structure) to plain dicts/lists.

    Handles:
    - Dataclass instances → dict
    - Lists → list of converted items
    - Dicts → dict with converted values
    - Primitives → returned as-is

    Args:
        obj: A dataclass instance, list, dict, or primitive.

    Returns:
        JSON-serialisable structure.
    """
    if is_dataclass(obj):
        result = {}
        for f in fields(obj):
            value = getattr(obj, f.name)
            result[f.name] = to_dict(value)
        return result
    if isinstance(obj, list):
        return [to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        return {k: to_dict(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return obj
