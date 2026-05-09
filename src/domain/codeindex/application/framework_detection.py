"""
/**
 * @project   CodeCortex
 * @package   CodeIndex/Framework
 * @standard  Aegis-CrossStack-v1.0
 * * Framework Detection — auto-detect frameworks from project files and source patterns.
 *   Ported from GitNexus's framework-detection.ts.
 */
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("CodeCortex.CodeIndex.FrameworkDetection")


_FRAMEWORK_PATTERNS: Dict[str, List[Dict]] = {
    # Python frameworks
    "django": [
        {"type": "file", "pattern": r"wsgi\.py$|asgi\.py$", "confidence": "high"},
        {"type": "file", "pattern": r"urls\.py$", "confidence": "high"},
        {"type": "file", "pattern": r"views\.py$", "confidence": "high"},
        {"type": "file", "pattern": r"settings\.py$", "confidence": "high"},
        {"type": "file", "pattern": r"models\.py$", "confidence": "medium"},
        {"type": "import", "pattern": r"from django\b", "confidence": "high"},
        {"type": "manifest", "key": "django", "confidence": "high"},
    ],
    "fastapi": [
        {"type": "file", "pattern": r"routers/", "confidence": "high"},
        {"type": "file", "pattern": r"main\.py$", "confidence": "medium"},
        {"type": "import", "pattern": r"from fastapi\b", "confidence": "high"},
        {"type": "import", "pattern": r"from fastapi\.routing\b", "confidence": "high"},
        {"type": "manifest", "key": "fastapi", "confidence": "high"},
    ],
    "flask": [
        {"type": "file", "pattern": r"app\.py$", "confidence": "medium"},
        {"type": "file", "pattern": r"routes\.py$", "confidence": "high"},
        {"type": "import", "pattern": r"from flask\b", "confidence": "high"},
        {"type": "manifest", "key": "flask", "confidence": "high"},
    ],
    # TypeScript/JS frameworks
    "nextjs": [
        {"type": "file", "pattern": r"next\.config", "confidence": "high"},
        {"type": "file", "pattern": r"pages/.*\.(tsx|ts|jsx|js)$", "confidence": "high"},
        {"type": "file", "pattern": r"app/.*page\.(tsx|ts)$", "confidence": "high"},
        {"type": "file", "pattern": r"app/.*layout\.(tsx|ts)$", "confidence": "high"},
        {"type": "manifest", "key": "next", "confidence": "high"},
    ],
    "express": [
        {"type": "file", "pattern": r"routes/.*\.(ts|js)$", "confidence": "high"},
        {"type": "file", "pattern": r"middleware/", "confidence": "medium"},
        {"type": "import", "pattern": r"require\(['\"]express['\"]\)", "confidence": "high"},
        {"type": "import", "pattern": r"from ['\"]express['\"]", "confidence": "high"},
        {"type": "manifest", "key": "express", "confidence": "high"},
    ],
    "nestjs": [
        {"type": "file", "pattern": r"modules/.*\.module\.ts$", "confidence": "high"},
        {"type": "file", "pattern": r"controllers/.*\.controller\.ts$", "confidence": "high"},
        {"type": "import", "pattern": r"@nestjs/", "confidence": "high"},
        {"type": "manifest", "key": "@nestjs/core", "confidence": "high"},
    ],
    # Java frameworks
    "spring": [
        {"type": "file", "pattern": r"@Controller", "confidence": "high"},
        {"type": "file", "pattern": r"@RestController", "confidence": "high"},
        {"type": "file", "pattern": r"@RequestMapping", "confidence": "high"},
        {"type": "file", "pattern": r"application\.yml$|application\.properties$", "confidence": "medium"},
    ],
    # Go frameworks
    "gin": [
        {"type": "import", "pattern": r'\"github\.com/gin-gonic/gin\"', "confidence": "high"},
    ],
}


def detect_frameworks(repo_root: Path, files: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Detect frameworks used in a repository.

    Scans project manifests (package.json, requirements.txt, etc.) and source file
    patterns to identify frameworks.

    Returns dict of {framework_name: confidence_level}
    """
    detected: Dict[str, str] = {}
    all_confidences: Dict[str, List[int]] = {}
    conf_map = {"high": 3, "medium": 2, "low": 1}

    # Phase 1: Check manifest files
    manifest_patterns = {
        "package.json": ("json", ["dependencies", "devDependencies"]),
        "requirements.txt": ("text", None),
        "Pipfile": ("text", None),
        "pyproject.toml": ("text", None),
        "go.mod": ("text", None),
        "composer.json": ("json", ["require", "require-dev"]),
        "Gemfile": ("text", None),
    }

    for fname, (ftype, keys) in manifest_patterns.items():
        manifest_path = repo_root / fname
        if manifest_path.exists():
            try:
                if ftype == "json":
                    data = json.loads(manifest_path.read_text())
                    for key in (keys or []):
                        deps = data.get(key, {})
                        if isinstance(deps, dict):
                            for dep in deps:
                                _check_framework(dep, detected, all_confidences, conf_map)
                else:
                    content = manifest_path.read_text()
                    for fw_name, patterns in _FRAMEWORK_PATTERNS.items():
                        for p in patterns:
                            if p["type"] == "manifest":
                                key = p["key"]
                                if key in content:
                                    _record(fw_name, p["confidence"], detected, all_confidences, conf_map)
            except Exception:
                pass

    # Phase 2: Check file path patterns
    search_files = files or []
    if not search_files:
        try:
            top_files = [str(f.relative_to(repo_root)) for f in repo_root.glob("*")
                         if f.is_file() and not f.name.startswith(".")]
            search_files = top_files
        except Exception:
            pass

    for fpath in search_files:
        for fw_name, patterns in _FRAMEWORK_PATTERNS.items():
            for p in patterns:
                if p["type"] == "file" and re.search(p["pattern"], fpath, re.I):
                    _record(fw_name, p["confidence"], detected, all_confidences, conf_map)

    # Compute final confidence
    result = {}
    for fw, confs in all_confidences.items():
        avg = sum(confs) / len(confs)
        if avg >= 2.5:
            result[fw] = "high"
        elif avg >= 1.5:
            result[fw] = "medium"
        else:
            result[fw] = "low"
    return result


def _check_framework(name: str, detected: Dict, all_confidences: Dict, conf_map: Dict):
    for fw_name, patterns in _FRAMEWORK_PATTERNS.items():
        for p in patterns:
            if p["type"] == "manifest" and name == p.get("key"):
                _record(fw_name, p["confidence"], detected, all_confidences, conf_map)
            elif name and fw_name in name.lower():
                _record(fw_name, "medium", detected, all_confidences, conf_map)


def _record(fw: str, confidence: str, detected: Dict, all_confidences: Dict, conf_map: Dict):
    detected[fw] = max(detected.get(fw, "low"), confidence,
                       key=lambda x: conf_map.get(x, 0))
    all_confidences.setdefault(fw, []).append(conf_map.get(confidence, 1))


def detect_from_source(content: str, file_path: str) -> Dict[str, str]:
    """Detect framework from source file content (imports, decorators, annotations)."""
    detected = {}
    for fw_name, patterns in _FRAMEWORK_PATTERNS.items():
        for p in patterns:
            if p["type"] == "import":
                if re.search(p["pattern"], content):
                    detected[fw_name] = p["confidence"]
    return detected
