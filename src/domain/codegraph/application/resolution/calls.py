"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeGraph/Resolution
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Function call resolution — maps caller→callee across files using imports_map.
 *   Ported from legacy codegraph tools/indexing/resolution/calls.py.
 */
"""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.logging_config import get_logger

logger = get_logger("CodeCortex.Domain.CodeGraph.Resolution.Calls")
_BUILTIN_NAMES: set = set(builtins.__dict__.keys())


def resolve_function_call(
    call: Dict[str, Any],
    caller_file_path: str,
    local_names: set,
    local_imports: Dict[str, Any],
    imports_map: Dict[str, List[str]],
    skip_external: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Resolve a single function call to its target definition.

    Resolution order (ported from legacy codegraph):
      1. Skip Python builtins (len, print, etc.)
      2. self/this/super/cls/@ — resolve to caller file
      3. Local name (same file)
      4. Direct import alias
      5. Global imports_map lookup (with dotted-call heuristics)
      6. Mark as unresolved external if skip_external=True
    """
    called_name = call.get("name", "")
    if called_name in _BUILTIN_NAMES:
        return None

    full_call_name = call.get("full_name", called_name)

    # Normalize caller path safely (may not exist on disk during resolution)
    try:
        caller_file_path = str(Path(caller_file_path).resolve())
    except (OSError, RuntimeError):
        pass

    # Extract caller context — context may be [name, node_type, def_line] or a plain string
    caller_ctx = call.get("context")
    if isinstance(caller_ctx, (list, tuple)):
        caller_name = caller_ctx[0] if len(caller_ctx) > 0 else None
        # Use function definition line (index 2) so the uid matches the stored Function node
        caller_line_number = caller_ctx[2] if len(caller_ctx) > 2 else call.get("line_number", 0)
    else:
        caller_name = caller_ctx
        caller_line_number = call.get("line_number", 0)

    is_unresolved_external = False
    resolved_called_name = called_name
    resolved_path: Optional[str] = None

    # Determine if this is a chained call (e.g. obj.foo.bar())
    is_chained_call = full_call_name.count(".") > 1 if "." in full_call_name else False
    base_obj = full_call_name.split(".")[0] if "." in full_call_name else None

    # For chained calls on self/this/super/cls/@, the lookup name stays the method name
    if is_chained_call and base_obj in ("self", "this", "super", "super()", "cls", "@"):
        lookup_name = called_name
    else:
        lookup_name = base_obj if base_obj else called_name

    # 1. self/this/super/cls/@ calls (unqualified) resolve to the caller file
    if base_obj in ("self", "this", "super", "super()", "cls", "@") and not is_chained_call:
        resolved_path = caller_file_path
        resolved_called_name = called_name
    # 2. Check local names first
    elif lookup_name in local_names:
        resolved_path = caller_file_path
        resolved_called_name = called_name if lookup_name == called_name else lookup_name
    # 3. Check local imports
    elif lookup_name in local_imports:
        import_info = local_imports[lookup_name]
        resolved_path = import_info.get("resolved_path")
        resolved_called_name = import_info.get("resolved_name", called_name)
    # 4. Global imports_map
    elif lookup_name in imports_map:
        candidates = imports_map[lookup_name]
        resolved_path = candidates[0] if candidates else None
        resolved_called_name = called_name if lookup_name == called_name else lookup_name
    else:
        # Heuristic: try splitting dotted calls
        if "." in full_call_name:
            parts = full_call_name.split(".")
            base = parts[0]
            if base in local_imports:
                import_info = local_imports[base]
                resolved_path = import_info.get("resolved_path")
                resolved_called_name = parts[-1]
            elif base in imports_map:
                candidates = imports_map[base]
                resolved_path = candidates[0] if candidates else None
                resolved_called_name = parts[-1]
            else:
                is_unresolved_external = True
        else:
            is_unresolved_external = True

    if skip_external and is_unresolved_external:
        return None

    return {
        "type": "function",
        "caller_name": caller_name,
        "caller_file_path": caller_file_path,
        "caller_line_number": caller_line_number,
        "called_name": resolved_called_name,
        "called_file_path": resolved_path,
        "line_number": call.get("line_number", 0),
        "args": call.get("args", []),
        "full_call_name": full_call_name,
        "is_unresolved_external": is_unresolved_external,
    }


# Language-to-extension mapping for imports_map filtering
_LANG_EXTS: Dict[str, set] = {
    "java":       {".java"},
    "python":     {".py", ".ipynb"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "typescript": {".ts", ".tsx"},
    "go":         {".go"},
    "rust":       {".rs"},
    "cpp":        {".cpp", ".h", ".hpp", ".hh"},
    "c":          {".c"},
    "c_sharp":    {".cs"},
    "kotlin":     {".kt"},
    "scala":      {".scala", ".sc"},
    "ruby":       {".rb"},
    "swift":      {".swift"},
    "php":        {".php"},
    "dart":       {".dart"},
    "perl":       {".pl", ".pm"},
    "haskell":    {".hs"},
    "elixir":     {".ex", ".exs"},
    "css":        {".css", ".scss", ".sass", ".less"},
}


def _get_lang_imports(caller_lang: str, imports_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Filter imports_map to entries whose paths match the caller language."""
    exts = _LANG_EXTS.get(caller_lang)
    if not exts:
        return imports_map
    filtered: Dict[str, List[str]] = {}
    for name, paths in imports_map.items():
        same_lang = [p for p in paths if Path(p).suffix in exts]
        if same_lang:
            filtered[name] = same_lang
        elif paths and not any(Path(p).suffix for p in paths):
            # Keep non-file entries (e.g. package names with no extension)
            filtered[name] = paths
    return filtered


def _safe_first_path(imports_map: Dict[str, List[str]], name: str) -> Optional[str]:
    """Safely get the first resolved path, guarding against empty list values."""
    if name not in imports_map:
        return None
    candidates = imports_map[name]
    return candidates[0] if candidates else None


def _build_local_imports(
    file_data: Dict[str, Any],
    imports_map: Dict[str, List[str]],
) -> Dict[str, Any]:
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
    return local_imports


def _classify_call(
    resolved: Dict[str, Any],
    caller_type: str,
    global_class_names: set,
    fn_to_fn: List[Dict],
    fn_to_cls: List[Dict],
    cls_to_fn: List[Dict],
    cls_to_cls: List[Dict],
    file_to_fn: List[Dict],
    file_to_cls: List[Dict],
) -> None:
    callee_is_class = resolved["called_name"] in global_class_names
    if caller_type == "function":
        (fn_to_cls if callee_is_class else fn_to_fn).append(resolved)
    elif caller_type == "class":
        (cls_to_cls if callee_is_class else cls_to_fn).append(resolved)
    else:
        (file_to_cls if callee_is_class else file_to_fn).append(resolved)


def build_function_call_groups(
    all_file_data: List[Dict[str, Any]],
    imports_map: Dict[str, List[str]],
    file_class_lookup: Optional[Dict[str, set]] = None,
    skip_external: bool = True,
) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict], List[Dict], List[Dict]]:
    """
    Group resolved function calls into caller→callee buckets:
    (fn→fn, fn→cls, cls→fn, cls→cls, file→fn, file→cls).

    Traverses both file-level calls and function-body calls so all call sites
    are captured regardless of scope.
    """
    fn_to_fn: List[Dict] = []
    fn_to_cls: List[Dict] = []
    cls_to_fn: List[Dict] = []
    cls_to_cls: List[Dict] = []
    file_to_fn: List[Dict] = []
    file_to_cls: List[Dict] = []

    # Pre-compute global class names once (O(n) vs O(n²) per-call scan)
    global_class_names: set = set()
    for fd in all_file_data:
        for c in fd.get("classes", []):
            name = c.get("name")
            if name:
                global_class_names.add(name)

    if file_class_lookup is None:
        file_class_lookup = {}
        for fd in all_file_data:
            path = fd.get("path", "")
            classes = {c.get("name") for c in fd.get("classes", [])}
            file_class_lookup[path] = classes

    # Pre-build per-language filtered imports_map views
    _lang_imports_cache: Dict[str, Dict[str, List[str]]] = {}

    buckets = (fn_to_fn, fn_to_cls, cls_to_fn, cls_to_cls, file_to_fn, file_to_cls)

    for idx, file_data in enumerate(all_file_data):
        caller_file_path = file_data.get("path", "")
        func_names = {f.get("name", "") for f in file_data.get("functions", [])}
        class_names = {c.get("name", "") for c in file_data.get("classes", [])}
        local_names = func_names | class_names
        local_imports = _build_local_imports(file_data, imports_map)

        caller_lang = file_data.get("lang", "")
        effective_imports_map = (
            _lang_imports_cache.setdefault(caller_lang, _get_lang_imports(caller_lang, imports_map))
            if caller_lang else imports_map
        )

        # 1. File-scope calls (module-level, context is None → caller_type = "file")
        for call in file_data.get("function_calls", []):
            resolved = resolve_function_call(
                call, caller_file_path, local_names, local_imports, effective_imports_map, skip_external
            )
            if resolved is None:
                continue
            caller_ctx = call.get("context")
            if isinstance(caller_ctx, (list, tuple)) and len(caller_ctx) > 1:
                caller_type = (
                    "function" if caller_ctx[1] == "function_definition"
                    else ("class" if caller_ctx[1] == "class_definition" else "file")
                )
            elif isinstance(caller_ctx, str):
                caller_type = caller_ctx
            else:
                caller_type = "file"
            _classify_call(resolved, caller_type, global_class_names, *buckets)

        # 2. Function-body calls — inject proper context so caller uid can be built
        for func in file_data.get("functions", []):
            func_name = func.get("name", "")
            func_def_line = func.get("line_number", 0)
            func_context = [func_name, "function_definition", func_def_line]
            for call in func.get("function_calls", []):
                call_with_ctx = dict(call)
                call_with_ctx["context"] = func_context
                resolved = resolve_function_call(
                    call_with_ctx, caller_file_path, local_names, local_imports,
                    effective_imports_map, skip_external
                )
                if resolved is None:
                    continue
                _classify_call(resolved, "function", global_class_names, *buckets)

        # 3. Class-body / method calls
        for cls in file_data.get("classes", []):
            cls_name = cls.get("name", "")
            cls_def_line = cls.get("line_number", 0)
            for method in cls.get("methods", []):
                method_name = method.get("name", "")
                method_def_line = method.get("line_number", 0)
                method_context = [method_name, "function_definition", method_def_line]
                for call in method.get("function_calls", []):
                    call_with_ctx = dict(call)
                    call_with_ctx["context"] = method_context
                    resolved = resolve_function_call(
                        call_with_ctx, caller_file_path, local_names, local_imports,
                        effective_imports_map, skip_external
                    )
                    if resolved is None:
                        continue
                    _classify_call(resolved, "function", global_class_names, *buckets)
            # Class-level (non-method) calls
            for call in cls.get("function_calls", []):
                cls_context = [cls_name, "class_definition", cls_def_line]
                call_with_ctx = dict(call)
                call_with_ctx["context"] = cls_context
                resolved = resolve_function_call(
                    call_with_ctx, caller_file_path, local_names, local_imports,
                    effective_imports_map, skip_external
                )
                if resolved is None:
                    continue
                _classify_call(resolved, "class", global_class_names, *buckets)

        if (idx + 1) % 1000 == 0:
            total = len(fn_to_fn) + len(fn_to_cls) + len(cls_to_fn) + len(cls_to_cls)
            file_total = len(file_to_fn) + len(file_to_cls)
            logger.info(
                "[CALLS] Resolved %d/%d files... (%d fn/cls calls, %d file calls)",
                idx + 1, len(all_file_data), total, file_total,
            )

    total_all = (
        len(fn_to_fn) + len(fn_to_cls) + len(cls_to_fn) + len(cls_to_cls)
        + len(file_to_fn) + len(file_to_cls)
    )
    logger.info(
        "[CALLS] Resolution complete: fn→fn=%d, fn→cls=%d, cls→fn=%d, cls→cls=%d, file→fn=%d, file→cls=%d. Total=%d",
        len(fn_to_fn), len(fn_to_cls), len(cls_to_fn), len(cls_to_cls),
        len(file_to_fn), len(file_to_cls), total_all,
    )
    return fn_to_fn, fn_to_cls, cls_to_fn, cls_to_cls, file_to_fn, file_to_cls
