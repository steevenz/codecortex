"""Framework detection enricher using modular framework detectors."""
from pathlib import Path
from typing import Dict, List, Any, Optional
from .parsers.frameworks import nextjs as nextjs_fw
from .parsers.frameworks import react as react_fw
from .parsers.frameworks import flutter as flutter_fw
from .parsers.frameworks import laravel as laravel_fw


def detect_frameworks(file_path: Path, parsed: Dict[str, Any], repo_configs: Dict[str, Any] = None) -> List[str]:
    """Detect frameworks using modular detectors with repository-level config context."""
    if repo_configs is None:
        repo_configs = {}
    
    detected: List[str] = []
    suffix = file_path.suffix.lower()
    rel_path = str(file_path).replace("\\", "/").lower()
    source = parsed.get("source", "")
    imports = parsed.get("imports", [])
    classes = parsed.get("classes", [])
    functions = parsed.get("functions", [])

    if suffix in (".ts", ".tsx", ".js", ".jsx"):
        if nextjs_fw.detect_nextjs(rel_path, source, imports, functions, repo_configs):
            detected.append("nextjs")
        if react_fw.detect_react(rel_path, source, imports, classes, functions, repo_configs):
            detected.append("react")

    if suffix == ".dart":
        if flutter_fw.detect_flutter(rel_path, source, imports, classes, functions, repo_configs):
            detected.append("flutter")

    if suffix == ".php":
        if laravel_fw.detect_laravel(rel_path, source, imports, classes, functions, repo_configs):
            detected.append("laravel")
        if ".blade.php" in rel_path:
            detected.append("laravel_blade")

    return list(dict.fromkeys(detected))


def enrich_parsed_data(file_path: Path, parsed: Dict[str, Any], repo_configs: Dict[str, Any] = None) -> Dict[str, Any]:
    """Enrich parsed data with framework metadata using modular enrichers."""
    if repo_configs is None:
        repo_configs = {}
    
    frameworks = detect_frameworks(file_path, parsed, repo_configs)
    if frameworks:
        parsed["frameworks"] = frameworks
        _enrich_symbols(file_path, parsed, frameworks)
    return parsed


def _enrich_symbols(file_path: Path, parsed: Dict[str, Any], frameworks: List[str]) -> None:
    rel_path = str(file_path).replace("\\", "/").lower()

    for cls in parsed.get("classes", []):
        for fw in frameworks:
            meta = _class_framework_meta(fw, cls, rel_path)
            if meta:
                cls.setdefault("framework_metadata", {})[fw] = meta

    for fn in parsed.get("functions", []):
        for fw in frameworks:
            meta = _function_framework_meta(fw, fn, rel_path)
            if meta:
                fn.setdefault("framework_metadata", {})[fw] = meta


def _class_framework_meta(fw: str, cls: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    """Delegate class enrichment to framework-specific modules."""
    if fw == "nextjs":
        return nextjs_fw.enrich_class(cls, rel_path)
    if fw == "react":
        return react_fw.enrich_class(cls)
    if fw == "flutter":
        return flutter_fw.enrich_class(cls)
    if fw == "laravel":
        return laravel_fw.enrich_class(cls)
    return None


def _function_framework_meta(fw: str, fn: Dict[str, Any], rel_path: str) -> Optional[Dict[str, Any]]:
    """Delegate function enrichment to framework-specific modules."""
    if fw == "nextjs":
        return nextjs_fw.enrich_function(fn, rel_path)
    if fw == "react":
        return react_fw.enrich_function(fn)
    if fw == "flutter":
        return flutter_fw.enrich_function(fn)
    if fw == "laravel":
        return laravel_fw.enrich_function(fn)
    return None
