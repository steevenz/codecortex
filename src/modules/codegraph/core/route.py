"""
Route Extraction — detects API routes and navigation paths from source code.
Ported from GitNexus's route-extractors/ and routes.ts pipeline phase.

:project: CodeCortex
:package: Modules.Codegraph.Core.Route
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from src.core.utils.language import detect_language

logger = logging.getLogger("CodeCortex.CodeGraph.RouteExtraction")

@dataclass
class Route:
    path: str
    method: str  # GET, POST, PUT, DELETE, PATCH, ALL
    handler: str
    framework: str
    file: str
    line: int
    params: List[str] = field(default_factory=list)

    @property
    def signature(self) -> str:
        return f"{self.method} {self.path}"

class RouteExtractor:
    """
    Extracts API routes from various web frameworks.

    Supports:
    - FastAPI: @app.get("/path"), @router.post("/path")
    - Django: path("path/", view), re_path(...)
    - Flask: @app.route("/path")
    - Next.js: File-based routing in pages/ and app/ directories
    - Express: router.get("/path"), app.post("/path")
    """

    def extract(self, file_path: str, content: str, language: Optional[str] = None) -> List[Route]:
        """Extract routes from a file based on its framework patterns."""
        routes = []
        lang = language or self._detect_language(file_path)

        if lang == "python":
            routes.extend(self._extract_fastapi(content, file_path))
            routes.extend(self._extract_django(content, file_path))
            routes.extend(self._extract_flask(content, file_path))
        elif lang in ("javascript", "typescript", "tsx"):
            routes.extend(self._extract_express(content, file_path))
            routes.extend(self._extract_nextjs(file_path))
        elif lang == "nextjs":
            routes.extend(self._extract_nextjs(file_path))

        return routes

    def _detect_language(self, file_path: str) -> str:
        base = detect_language(file_path)
        if base in ("typescript", "javascript", "typescriptjsx"):
            p = file_path.replace("\\", "/")
            if "/pages/" in p or "/app/" in p:
                return "nextjs"
        return base

    def _extract_fastapi(self, content: str, file_path: str) -> List[Route]:
        routes = []
        pattern = re.compile(
            r'@(?:app|router|api_router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            re.MULTILINE,
        )
        for i, line in enumerate(content.split("\n"), 1):
            m = pattern.search(line)
            if m:
                routes.append(Route(
                    path=m.group(2),
                    method=m.group(1).upper(),
                    handler=self._infer_handler_name(line),
                    framework="fastapi",
                    file=file_path,
                    line=i,
                    params=self._extract_params(m.group(2)),
                ))
        return routes

    def _extract_django(self, content: str, file_path: str) -> List[Route]:
        routes = []
        # path("url/", view)
        p1 = re.compile(r'path\s*\(\s*["\']([^"\']+)["\']\s*,\s*([^,\s)]+)', re.MULTILINE)
        # re_path(r"...", view)
        p2 = re.compile(r're_path\s*\(\s*r?["\']([^"\']+)["\']\s*,\s*([^,\s)]+)', re.MULTILINE)

        for i, line in enumerate(content.split("\n"), 1):
            for p in (p1, p2):
                m = p.search(line)
                if m:
                    routes.append(Route(
                        path=m.group(1),
                        method="GET",  # Django default
                        handler=m.group(2).strip(),
                        framework="django",
                        file=file_path,
                        line=i,
                    ))
        return routes

    def _extract_flask(self, content: str, file_path: str) -> List[Route]:
        routes = []
        pattern = re.compile(
            r'@(?:app|blueprint)\.route\s*\(\s*["\']([^"\']+)["\']',
            re.MULTILINE,
        )
        for i, line in enumerate(content.split("\n"), 1):
            m = pattern.search(line)
            if m:
                # Check for methods argument
                methods = re.search(r"methods=\[['\"]([^'\"]+)['\"]", line)
                method = methods.group(1).upper() if methods else "GET"
                routes.append(Route(
                    path=m.group(1),
                    method=method,
                    handler=self._infer_handler_name(line),
                    framework="flask",
                    file=file_path,
                    line=i,
                ))
        return routes

    def _extract_express(self, content: str, file_path: str) -> List[Route]:
        routes = []
        pattern = re.compile(
            r'(?:router|app)\.(get|post|put|delete|patch|all)\s*\(\s*["\']([^"\']+)["\']',
            re.MULTILINE,
        )
        for i, line in enumerate(content.split("\n"), 1):
            m = pattern.search(line)
            if m:
                routes.append(Route(
                    path=m.group(2),
                    method=m.group(1).upper(),
                    handler=self._infer_handler_name(line),
                    framework="express",
                    file=file_path,
                    line=i,
                ))
        return routes

    def _extract_nextjs(self, file_path: str) -> List[Route]:
        """Next.js uses file-based routing — extract from path."""
        routes = []
        p = file_path.replace("\\", "/")

        # Next.js Pages Router
        m = re.search(r"/pages/(?:api/)?(.+?)\.(tsx|ts|jsx|js)$", p)
        if m:
            route_path = "/" + m.group(1)
            route_path = re.sub(r"\[([^\]]+)\]", r":\1", route_path)
            route_path = re.sub(r"/index$", "/", route_path) or "/"
            method = "ALL"
            if "/api/" in p:
                method = "GET"  # Default for API routes
            routes.append(Route(
                path=route_path,
                method=method,
                handler=p.split("/")[-1],
                framework="nextjs-pages",
                file=file_path,
                line=1,
                params=re.findall(r":(\w+)", route_path),
            ))
            return routes

        # Next.js App Router
        m = re.search(r"/app/(.+?)/route\.(ts|js)$", p)
        if m:
            route_path = "/" + m.group(1)
            route_path = re.sub(r"\[([^\]]+)\]", r":\1", route_path)
            routes.append(Route(
                path=route_path or "/",
                method="ALL",
                handler="route_handler",
                framework="nextjs-app",
                file=file_path,
                line=1,
                params=re.findall(r":(\w+)", route_path),
            ))

        return routes

    def _extract_params(self, path: str) -> List[str]:
        return re.findall(r"\{(\w+)\}|:(\w+)", path)

    def _infer_handler_name(self, line: str) -> str:
        m = re.search(r"def\s+(\w+)\s*\(", line)
        if m:
            return m.group(1)
        m = re.search(r"(\w+)\s*[:=]\s*(?:lambda|async|function)", line)
        return m.group(1) if m else "handler"

def extract_routes_from_files(files: List[Dict[str, str]]) -> List[Route]:
    """Extract routes from multiple files."""
    extractor = RouteExtractor()
    all_routes = []
    for f in files:
        try:
            routes = extractor.extract(f.get("path", ""), f.get("content", ""))
            all_routes.extend(routes)
        except Exception as e:
            logger.debug(f"Route extraction failed for {f.get('path')}: {e}")
    return all_routes
