"""
Language detection utilities — extension-to-language mapping and file classification.

:project: CodeCortex
:package: Core.Utils.Language
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict

EXTENSION_TO_LANGUAGE: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescriptjsx",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".m": "objective_c",
    ".mm": "objective_cpp",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".pl": "perl",
    ".pm": "perl",
    ".lua": "lua",
    ".r": "r",
    ".ex": "elixir",
    ".exs": "elixir",
    ".clj": "clojure",
    ".cljs": "clojure",
    ".tf": "terraform",
    ".hcl": "terraform",
    ".vue": "vue",
    ".svelte": "svelte",
    ".astro": "astro",
    ".dart": "dart",
    ".hs": "haskell",
    ".lhs": "haskell",
    ".cob": "cobol",
    ".cbl": "cobol",
    ".cpy": "cobol",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".html": "html",
    ".htm": "html",
    ".xml": "xml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".txt": "text",
}

SOURCE_CODE_EXTENSIONS = frozenset({
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".kts", ".cs", ".rb", ".php",
    ".swift", ".scala", ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp",
    ".m", ".mm", ".sh", ".bash", ".zsh", ".pl", ".pm", ".lua", ".r",
    ".ex", ".exs", ".clj", ".cljs", ".tf", ".hcl", ".vue", ".svelte",
    ".astro", ".dart", ".hs", ".lhs", ".cob", ".cbl", ".cpy",
})

CONFIG_EXTENSIONS = frozenset({
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".xml", ".properties", ".env", ".editorconfig",
})

DOC_EXTENSIONS = frozenset({
    ".md", ".rst", ".txt", ".html", ".css", ".scss", ".less",
})

BINARY_EXTENSIONS = frozenset({
    ".exe", ".dll", ".so", ".dylib", ".bin", ".msi", ".deb", ".rpm",
    ".dmg", ".pyc", ".pyo", ".class", ".o", ".obj", ".a", ".lib",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".png", ".jpg",
    ".jpeg", ".gif", ".ico", ".svg", ".mp3", ".mp4", ".avi", ".mov",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".ttf", ".otf", ".woff", ".woff2", ".eot", ".wasm",
})

@lru_cache(maxsize=512)
def detect_language(file_path: str | Path) -> str:
    """Detect programming language from a file extension.

    Args:
        file_path: File path (string or Path object).

    Returns:
        Language name string, or ``'unknown'`` if the extension is unrecognised.
    """
    ext = Path(file_path).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(ext, "unknown")

@lru_cache(maxsize=512)
def is_source_code(file_path: str | Path) -> bool:
    """Check if a file is a source code file based on its extension."""
    ext = Path(file_path).suffix.lower()
    return ext in SOURCE_CODE_EXTENSIONS

@lru_cache(maxsize=512)
def classify_file(file_path: str | Path) -> str:
    """Classify a file by type based on its extension.

    Returns one of: ``'code'``, ``'config'``, ``'doc'``, ``'binary'``, ``'other'``.
    """
    ext = Path(file_path).suffix.lower()
    if ext in SOURCE_CODE_EXTENSIONS:
        return "code"
    if ext in CONFIG_EXTENSIONS:
        return "config"
    if ext in DOC_EXTENSIONS:
        return "doc"
    if ext in BINARY_EXTENSIONS:
        return "binary"
    return "other"

def is_extension_in(file_path: str | Path, allowed: frozenset) -> bool:
    """Check if a file extension is in an allowed set."""
    return Path(file_path).suffix.lower() in allowed
