"""
Cross-Language Symbol Resolution — resolves symbols across programming languages.

Detects integration points between language ecosystems:
- protobuf (.proto) → multiple language implementations
- OpenAPI specs → endpoint implementations in different languages
- Package/service names across package managers
- Framework routers matching API specs

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Cross_language
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("CodeCortex.CodeIndex.CrossLanguage")

# Language detection by file extension
LANG_BY_EXT: Dict[str, str] = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".jsx": "javascript",
    ".go": "go", ".rs": "rust", ".java": "java",
    ".kt": "kotlin", ".cs": "csharp", ".rb": "ruby",
    ".php": "php", ".swift": "swift",
}

# Framework detection by file/directory patterns
FRAMEWORK_PATTERNS: Dict[str, List[str]] = {
    "fastapi": ["main.py", "routers/", "schemas.py"],
    "flask": ["app.py", "routes.py", "views.py"],
    "django": ["urls.py", "views.py", "serializers.py"],
    "express": ["routes/", "router", "app.js", "server.js"],
    "nextjs": ["pages/api/", "app/api/", "route.ts"],
    "gin": ["router", "routes"],
    "grpc": ["_pb2.py", "_pb2_grpc.py", "proto/"],
}

# Package manager file patterns
PACKAGE_FILES: Dict[str, str] = {
    "package.json": "npm",
    "pyproject.toml": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "kotlin",
    "Gemfile": "ruby",
    "composer.json": "php",
    "Podfile": "swift",
}


@dataclass
class CrossLanguageRef:
    """A cross-language symbol reference."""
    source_language: str
    source_file: str
    target_language: str
    target_file: str
    symbol_name: str
    ref_type: str  # proto_rpc, openapi_endpoint, package_ref, framework_route
    confidence: float  # 0.0 - 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_language": self.source_language,
            "source_file": self.source_file,
            "target_language": self.target_language,
            "target_file": self.target_file,
            "symbol_name": self.symbol_name,
            "ref_type": self.ref_type,
            "confidence": self.confidence,
        }


class CrossLanguageResolver:
    """Resolves symbols and services across multiple programming languages.

    Usage:
        resolver = CrossLanguageResolver()
        result = resolver.resolve("/path/to/monorepo")
        # {"services": [...], "api_endpoints": [...], "cross_refs": [...]}
    """

    def __init__(self):
        self._findings: List[CrossLanguageRef] = []

    def resolve(self, root_path: str) -> Dict[str, Any]:
        """Run all cross-language resolution strategies.

        Args:
            root_path: Root of the repository or monorepo.

        Returns:
            Dict with services, api_endpoints, cross_refs, proto_services.
        """
        root = Path(root_path)
        if not root.exists():
            return {"error": f"Path not found: {root_path}"}

        self._findings = []

        # Detect project packages first
        packages = self._detect_packages(root)

        # Strategy 1: protobuf → multiple languages
        proto_services = self._resolve_protobuf(root)

        # Strategy 2: OpenAPI → endpoint implementations
        api_endpoints = self._resolve_openapi(root)

        # Strategy 3: Package name cross-ref
        package_refs = self._cross_ref_packages(root, packages)

        # Strategy 4: Framework routes
        framework_routes = self._detect_framework_routes(root)

        return {
            "packages": packages,
            "proto_services": proto_services,
            "api_endpoints": api_endpoints,
            "framework_routes": framework_routes,
            "cross_refs": [f.to_dict() for f in self._findings],
            "total_cross_refs": len(self._findings),
            "languages_detected": list({
                LANG_BY_EXT.get(fp.suffix.lower(), "other")
                for fp in root.rglob("*")
                if fp.suffix.lower() in LANG_BY_EXT and not self._is_excluded(fp, root)
            }),
        }

    def _detect_packages(self, root: Path) -> List[Dict[str, Any]]:
        """Detect packages from package manager files."""
        packages = []
        for pf, pm_type in PACKAGE_FILES.items():
            for fp in root.rglob(pf):
                if self._is_excluded(fp, root):
                    continue
                try:
                    rel = fp.relative_to(root)
                    if pm_type == "npm":
                        data = json.loads(fp.read_text(encoding="utf-8", errors="replace"))
                        name = data.get("name", fp.parent.name)
                        packages.append({
                            "name": name,
                            "type": pm_type,
                            "path": str(rel.parent),
                            "file": str(rel),
                            "version": data.get("version", ""),
                            "dependencies": list(data.get("dependencies", {}).keys())[:20],
                        })
                    elif pm_type == "python":
                        content = fp.read_text(encoding="utf-8", errors="replace")
                        name = fp.parent.name
                        packages.append({
                            "name": name,
                            "type": pm_type,
                            "path": str(rel.parent),
                            "file": str(rel),
                        })
                    elif pm_type == "go":
                        content = fp.read_text(encoding="utf-8", errors="replace")
                        m = re.search(r"module\s+(\S+)", content)
                        if m:
                            packages.append({
                                "name": m.group(1),
                                "type": pm_type,
                                "path": str(rel.parent),
                                "file": str(rel),
                            })
                except Exception:
                    continue
        return packages

    def _resolve_protobuf(self, root: Path) -> List[Dict[str, Any]]:
        """Find .proto files and match to language implementations."""
        services = []
        for fp in root.rglob("*.proto"):
            if self._is_excluded(fp, root):
                continue
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                rel = fp.relative_to(root)
                package = re.search(r"package\s+([^;]+);", content)
                package_name = package.group(1).strip() if package else ""

                # Extract service definitions
                for m in re.finditer(r"service\s+(\w+)\s*\{", content):
                    service_name = m.group(1)
                    svc_entry: Dict[str, Any] = {
                        "proto_file": str(rel),
                        "package": package_name,
                        "service": service_name,
                        "implementations": [],
                    }

                    # Find implementations in various languages
                    impls = self._find_proto_implementations(root, service_name, package_name)
                    svc_entry["implementations"] = impls
                    services.append(svc_entry)

                    # Create cross-refs
                    for impl in impls:
                        self._findings.append(CrossLanguageRef(
                            source_language="protobuf",
                            source_file=str(rel),
                            target_language=impl["language"],
                            target_file=impl["file"],
                            symbol_name=service_name,
                            ref_type="proto_rpc",
                            confidence=0.9,
                        ))

            except Exception as e:
                logger.debug(f"Proto parse error {fp}: {e}")

        return services

    def _find_proto_implementations(
        self, root: Path, service_name: str, package: str,
    ) -> List[Dict[str, str]]:
        """Find language-specific implementations of a protobuf service."""
        impls: List[Dict[str, str]] = []
        name_lower = service_name.lower()

        # Python: Search for Servicer classes
        for fp in root.rglob("*.py"):
            if self._is_excluded(fp, root):
                continue
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                if name_lower in content.lower():
                    # Check for gRPC implementation patterns
                    patterns = [
                        re.escape(service_name) + r"Servicer",
                        re.escape(service_name) + r"Servicer\(.*\)",
                        r"class\s+\w*" + re.escape(service_name) + r"\w*",
                    ]
                    for pat in patterns:
                        if re.search(pat, content):
                            rel = fp.relative_to(root)
                            impls.append({
                                "language": "python",
                                "file": str(rel),
                                "type": "grpc_server" if "Servicer" in content else "grpc_client",
                            })
                            break
            except Exception:
                continue

        # TypeScript/JavaScript
        for ext in (".ts", ".js"):
            for fp in root.rglob(f"*{ext}"):
                if self._is_excluded(fp, root):
                    continue
                try:
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    if name_lower in content.lower() and ("grpc" in content.lower() or "proto" in content.lower()):
                        rel = fp.relative_to(root)
                        impls.append({
                            "language": "typescript" if ext == ".ts" else "javascript",
                            "file": str(rel),
                            "type": "grpc_client",
                        })
                except Exception:
                    continue

        # Go
        for fp in root.rglob("*.go"):
            if self._is_excluded(fp, root):
                continue
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                if name_lower in content.lower() and "grpc" in content.lower():
                    rel = fp.relative_to(root)
                    impl_type = "grpc_server" if "Register" in content else "grpc_client"
                    impls.append({
                        "language": "go",
                        "file": str(rel),
                        "type": impl_type,
                    })
            except Exception:
                continue

        return impls

    def _resolve_openapi(self, root: Path) -> List[Dict[str, Any]]:
        """Find OpenAPI specs and match to endpoint implementations."""
        endpoints: List[Dict[str, Any]] = []

        for fp in root.rglob("*"):
            if self._is_excluded(fp, root):
                continue
            name = fp.name.lower()
            if name not in ("openapi.yaml", "openapi.yml", "openapi.json", "swagger.json", "swagger.yaml"):
                continue

            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                import json
                try:
                    import yaml
                    spec = json.loads(content) if fp.suffix == ".json" else yaml.safe_load(content)
                except ImportError:
                    spec = json.loads(content) if fp.suffix == ".json" else None
                    if not spec:
                        continue
                if not isinstance(spec, dict):
                    continue

                rel = fp.relative_to(root)
                paths = spec.get("paths", {}) or {}
                for path_name, methods in paths.items():
                    if not isinstance(methods, dict):
                        continue
                    for method, details in methods.items():
                        if not isinstance(details, dict):
                            continue
                        operation_id = details.get("operationId", "")
                        summary = details.get("summary", "")

                        # Find implementations
                        impls = self._find_api_implementations(
                            root, method, path_name, operation_id,
                        )

                        endpoints.append({
                            "spec_file": str(rel),
                            "path": path_name,
                            "method": method.upper(),
                            "operation_id": operation_id,
                            "summary": summary[:100],
                            "implementations": impls,
                        })

                        for impl in impls:
                            self._findings.append(CrossLanguageRef(
                                source_language="openapi",
                                source_file=str(rel),
                                target_language=impl["language"],
                                target_file=impl["file"],
                                symbol_name=operation_id or f"{method.upper()} {path_name}",
                                ref_type="openapi_endpoint",
                                confidence=0.7,
                            ))

            except Exception as e:
                logger.debug(f"OpenAPI parse error {fp}: {e}")

        return endpoints

    def _find_api_implementations(
        self, root: Path, method: str, path: str, operation_id: str,
    ) -> List[Dict[str, str]]:
        """Find endpoint implementations across languages."""
        impls: List[Dict[str, str]] = []
        method_upper = method.upper()
        path_parts = [p for p in path.split("/") if p and not p.startswith("{")]

        # Python: FastAPI, Flask, Django
        for fp in root.rglob("*.py"):
            if self._is_excluded(fp, root):
                continue
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                content_lower = content.lower()

                # Match by operation_id
                if operation_id and operation_id.lower() in content_lower:
                    rel = fp.relative_to(root)
                    impls.append({"language": "python", "file": str(rel), "type": "handler"})
                    continue

                # Match by HTTP method decorator + path segment
                route_patterns = [
                    rf"@{method_upper}\({path}\)",
                    rf"router\.{method_lower}\({path}\)",
                    rf"app\.{method_lower}\({path}\)",
                ]
                method_lower = method.lower()
                for pat in route_patterns:
                    if re.search(pat, content):
                        rel = fp.relative_to(root)
                        impls.append({"language": "python", "file": str(rel), "type": "handler"})
                        break
            except Exception:
                continue

        # TypeScript: Express, Next.js
        for fp in root.rglob("*"):
            if self._is_excluded(fp, root):
                continue
            if fp.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                continue
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                content_lower = content.lower()
                if operation_id and operation_id.lower() in content_lower:
                    rel = fp.relative_to(root)
                    impls.append({"language": "typescript" if fp.suffix.startswith(".ts") else "javascript",
                                  "file": str(rel), "type": "handler"})
                    continue
                # Match route handler
                for part in path_parts:
                    if part in content_lower and (method_lower in content_lower or "handler" in content_lower):
                        rel = fp.relative_to(root)
                        impls.append({"language": "typescript" if fp.suffix.startswith(".ts") else "javascript",
                                      "file": str(rel), "type": "handler"})
                        break
            except Exception:
                continue

        return impls

    def _cross_ref_packages(
        self, root: Path, packages: List[Dict],
    ) -> List[Dict[str, Any]]:
        """Cross-reference packages across language boundaries."""
        refs: List[Dict[str, Any]] = []
        names = {p["name"].lower(): p for p in packages if p.get("name")}

        for pkg in packages:
            name = pkg.get("name", "").lower()
            if not name:
                continue

            # Find references to this package in other-language files
            for fp in root.rglob("*"):
                if self._is_excluded(fp, root):
                    continue
                if fp.suffix not in LANG_BY_EXT:
                    continue
                pkg_lang = LANG_BY_EXT.get(fp.suffix, "")
                if pkg_lang == pkg.get("type"):
                    continue  # Skip same-language refs

                try:
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    if name in content.lower():
                        rel = fp.relative_to(root)
                        refs.append({
                            "package": pkg["name"],
                            "package_path": pkg["path"],
                            "referenced_in": str(rel),
                            "language": pkg_lang,
                        })
                        self._findings.append(CrossLanguageRef(
                            source_language=pkg["type"],
                            source_file=str(Path(pkg["path"]) / pkg.get("file", "")),
                            target_language=pkg_lang,
                            target_file=str(rel),
                            symbol_name=pkg["name"],
                            ref_type="package_ref",
                            confidence=0.5,
                        ))
                except Exception:
                    continue

        return refs

    def _detect_framework_routes(self, root: Path) -> List[Dict[str, Any]]:
        """Detect framework route definitions."""
        routes: List[Dict[str, Any]] = []

        # FastAPI routers
        for fp in root.rglob("*.py"):
            if self._is_excluded(fp, root):
                continue
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                for m in re.finditer(r"@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*[\"']([^\"']+)[\"']", content):
                    rel = fp.relative_to(root)
                    routes.append({
                        "file": str(rel),
                        "method": m.group(1).upper(),
                        "path": m.group(2),
                        "framework": "fastapi",
                        "language": "python",
                    })
            except Exception:
                continue

        # Express routers
        for fp in root.rglob("*"):
            if fp.suffix not in (".ts", ".js"):
                continue
            if self._is_excluded(fp, root):
                continue
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                for m in re.finditer(r"router\.(get|post|put|delete|patch)\s*\(\s*[\"']([^\"']+)[\"']", content):
                    rel = fp.relative_to(root)
                    routes.append({
                        "file": str(rel),
                        "method": m.group(1).upper(),
                        "path": m.group(2),
                        "framework": "express",
                        "language": "typescript" if fp.suffix == ".ts" else "javascript",
                    })
            except Exception:
                continue

        return routes

    @staticmethod
    def _is_excluded(fp: Path, root: Path) -> bool:
        try:
            rel = fp.relative_to(root)
            for part in rel.parts:
                if part.startswith(".") or part in ("node_modules", "venv", ".venv", "__pycache__", "vendor", "dist", "build", ".git"):
                    return True
        except ValueError:
            return True
        return False
