"""
/**
 * @project   CodeCortex
 * @package   CodeIndex/ImportResolvers
 * @standard  Aegis-CrossStack-v1.0
 * * Wildcard Import Synthesis — resolves `from X import *` and whole-module imports.
 *   Ported from GitNexus's wildcard-synthesis.ts pipeline phase.
 */
"""

import re
import logging
from typing import Dict, List, Set, Optional, Any

logger = logging.getLogger("CodeCortex.CodeIndex.WildcardImports")


def is_wildcard_import(import_stmt: str) -> bool:
    """Check if an import statement is a wildcard import."""
    return "*" in import_stmt and "import" in import_stmt


def get_exported_symbols(content: str, language: str) -> List[str]:
    """
    Get all exported symbols from a file's content.
    Python: names without leading underscore
    TypeScript/JS: exported names
    Go: capitalized names
    """
    exported = []
    
    if language == "python":
        # Match top-level functions, classes, variables (no _ prefix)
        patterns = [
            r"^(?:async\s+)?def\s+(\w+)\s*\(",
            r"^class\s+(\w+)\s*",
            r"^(\w+)\s*=\s*",
        ]
        for pat in patterns:
            for m in re.finditer(pat, content, re.MULTILINE):
                name = m.group(1)
                if not name.startswith("_"):
                    exported.append(name)
        # Also check __all__
        all_match = re.search(r"__all__\s*=\s*\[([^\]]*)\]", content)
        if all_match:
            explicit = re.findall(r"['\"]([^'\"]+)['\"]", all_match.group(1))
            if explicit:
                return explicit
    
    elif language in ("typescript", "javascript", "tsx", "jsx"):
        pat = re.compile(r"^export\s+(?:default\s+)?(?:function|class|const|let|var|interface|type)\s+(\w+)", re.MULTILINE)
        for m in pat.finditer(content):
            exported.append(m.group(1))
    
    elif language == "go":
        # Go: capitalized names are exported
        pat = re.compile(r"^func\s+([A-Z]\w*)\s*\(", re.MULTILINE)
        for m in pat.finditer(content):
            exported.append(m.group(1))
        pat2 = re.compile(r"^type\s+([A-Z]\w*)", re.MULTILINE)
        for m in pat2.finditer(content):
            exported.append(m.group(1))
    
    return exported


def synthesize_wildcard_imports(
    files: Dict[str, str],  # file_path -> content
    language_map: Dict[str, str],  # file_path -> language
) -> Dict[str, List[str]]:
    """
    Synthesize wildcard imports into explicit symbol imports.
    
    Returns: source_file -> [resolved_symbol_names]
    Maps each file that has `from X import *` to the list of symbols
    that would be imported from module X.
    """
    # Build export index: module_name -> [exported_symbols]
    export_index: Dict[str, List[str]] = {}
    for file_path, content in files.items():
        lang = language_map.get(file_path, "python")
        # Use the file stem as the module name
        module_name = file_path.replace("\\", "/").rstrip(".py").replace("/", ".")
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]  # Remove .__init__
        exported = get_exported_symbols(content, lang)
        if exported:
            export_index[file_path] = exported
    
    # Resolve wildcard imports
    result: Dict[str, List[str]] = {}
    for file_path, content in files.items():
        lines = content.split("\n")
        lang = language_map.get(file_path, "python")
        
        for line in lines:
            if not is_wildcard_import(line):
                continue
            
            # Parse: from module import *
            m = re.match(r"from\s+([\w.]+)\s+import\s+\*", line)
            if not m:
                continue
            
            module_path = m.group(1).replace(".", "/")
            resolved = []
            
            # Look for the module in our files
            for fpath, exports in export_index.items():
                # Check if this file matches the module path
                norm_fpath = fpath.replace("\\", "/").rstrip(".py")
                if (norm_fpath == module_path or 
                    norm_fpath.endswith(f"/{module_path}") or 
                    norm_fpath.endswith(f"/{module_path}/__init__")):
                    resolved.extend(exports)
            
            if resolved:
                result[file_path] = list(set(resolved))
    
    return result


def quick_wildcard_resolve(
    source_file: str,
    import_line: str,
    all_files: Dict[str, str],
    language_map: Dict[str, str],
) -> List[str]:
    """Quick resolve a single wildcard import."""
    m = re.match(r"from\s+([\w.]+)\s+import\s+\*", import_line)
    if not m:
        return []
    
    module_path = m.group(1).replace(".", "/")
    result = []
    
    for fpath, content in all_files.items():
        norm = fpath.replace("\\", "/").rstrip(".py")
        if norm == module_path or norm.endswith(f"/{module_path}") or norm.endswith(f"/{module_path}/__init__"):
            lang = language_map.get(fpath, "python")
            result.extend(get_exported_symbols(content, lang))
    
    return list(set(result))
