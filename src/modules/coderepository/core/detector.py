"""
Repository-level framework detection orchestrator.

:project: CodeCortex
:package: Modules.Coderepository.Core.Detector
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v1.0
"""
from pathlib import Path
from typing import Dict, List, Any, Optional
from .config_parser import ConfigParser

class RepositoryFrameworkDetector:
    """Detect frameworks at repository level using configuration files and code analysis with maximum coverage."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.repo_configs = ConfigParser.parse_all_configs(repo_root)
        self._detected_frameworks: Optional[List[str]] = None
        # Lazy imports to break circular dependency with codeindex
        self._framework_modules = None
    def _get_fw_module(self, name):
        """Lazy-load a framework detection module to avoid circular imports."""
        import importlib
        return importlib.import_module(f'src.modules.codeindex.parsers.parsers.frameworks.{name}')


    def detect_all_frameworks(self) -> List[str]:
        """Detect all frameworks used in the repository."""
        if self._detected_frameworks is not None:
            return self._detected_frameworks

        frameworks = []

        # JavaScript/TypeScript frameworks
        if self._detect_javascript_frameworks():
            frameworks.extend(self._detect_javascript_frameworks())

        # Python frameworks
        if self._detect_python_frameworks():
            frameworks.extend(self._detect_python_frameworks())

        # PHP frameworks
        if self._detect_php_frameworks():
            frameworks.extend(self._detect_php_frameworks())

        # Ruby frameworks
        if self._detect_ruby_frameworks():
            frameworks.extend(self._detect_ruby_frameworks())

        # Dart/Flutter
        if self._detect_dart_frameworks():
            frameworks.extend(self._detect_dart_frameworks())

        # .NET frameworks
        if self._detect_dotnet_frameworks():
            frameworks.extend(self._detect_dotnet_frameworks())

        # Remove duplicates while preserving order
        self._detected_frameworks = list(dict.fromkeys(frameworks))
        return self._detected_frameworks

    def get_framework_versions(self) -> Dict[str, str]:
        """Extract framework versions from configuration files."""
        versions = {}

        # From package.json
        pkg_deps = self.repo_configs.get("package.json", {}).get("dependencies", {})
        if "react" in pkg_deps:
            versions["react"] = pkg_deps["react"]
        if "next" in pkg_deps:
            versions["nextjs"] = pkg_deps["next"]
        if "vue" in pkg_deps:
            versions["vue"] = pkg_deps["vue"]
        if "@angular/core" in pkg_deps:
            versions["angular"] = pkg_deps["@angular/core"]
        if "express" in pkg_deps:
            versions["express"] = pkg_deps["express"]
        if "@nestjs/core" in pkg_deps:
            versions["nestjs"] = pkg_deps["@nestjs/core"]

        # From composer.json
        composer_deps = self.repo_configs.get("composer.json", {}).get("dependencies", {})
        if "laravel/framework" in composer_deps:
            versions["laravel"] = composer_deps["laravel/framework"]
        if "symfony/framework-bundle" in composer_deps:
            versions["symfony"] = composer_deps["symfony/framework-bundle"]

        # From Gemfile
        gem_deps = self.repo_configs.get("Gemfile", {}).get("dependencies", {})
        if "rails" in gem_deps:
            versions["rails"] = gem_deps["rails"]

        # From requirements.txt
        req_deps = self.repo_configs.get("requirements.txt", {}).get("dependencies", {})
        if "django" in req_deps:
            versions["django"] = req_deps["django"]
        if "flask" in req_deps:
            versions["flask"] = req_deps["flask"]
        if "fastapi" in req_deps:
            versions["fastapi"] = req_deps["fastapi"]

        # From pubspec.yaml
        pubspec_deps = self.repo_configs.get("pubspec.yaml", {}).get("dependencies", {})
        if "flutter" in pubspec_deps:
            versions["flutter"] = pubspec_deps["flutter"]

        # From .csproj
        csproj_deps = self.repo_configs.get("csproj", {}).get("dependencies", {})
        if "Microsoft.AspNetCore.App" in csproj_deps:
            versions["aspnet"] = csproj_deps["Microsoft.AspNetCore.App"]

        return versions

    def _detect_javascript_frameworks(self) -> List[str]:
        """Detect JavaScript/TypeScript frameworks."""
        frameworks = []

        # Check for React
        pkg_deps = self.repo_configs.get("package.json", {}).get("dependencies", {})
        if "react" in pkg_deps:
            frameworks.append("react")

        # Check for Next.js
        if "next" in pkg_deps:
            frameworks.append("nextjs")

        # Check for Vue
        if "vue" in pkg_deps:
            frameworks.append("vue")

        # Check for Angular
        if any(dep.startswith("@angular/") for dep in pkg_deps):
            frameworks.append("angular")

        # Check for Express
        if "express" in pkg_deps:
            frameworks.append("express")

        # Check for NestJS
        if any(dep.startswith("@nestjs/") for dep in pkg_deps):
            frameworks.append("nestjs")

        return frameworks

    def _detect_python_frameworks(self) -> List[str]:
        """Detect Python frameworks."""
        frameworks = []

        req_deps = self.repo_configs.get("requirements.txt", {}).get("dependencies", {})
        if "django" in req_deps:
            frameworks.append("django")
        if "flask" in req_deps:
            frameworks.append("flask")
        if "fastapi" in req_deps:
            frameworks.append("fastapi")

        return frameworks

    def _detect_php_frameworks(self) -> List[str]:
        """Detect PHP frameworks."""
        frameworks = []

        composer_deps = self.repo_configs.get("composer.json", {}).get("dependencies", {})
        if "laravel/framework" in composer_deps or "laravel" in composer_deps:
            frameworks.append("laravel")
        if "symfony/framework-bundle" in composer_deps or any(dep.startswith("symfony/") for dep in composer_deps):
            frameworks.append("symfony")

        return frameworks

    def _detect_ruby_frameworks(self) -> List[str]:
        """Detect Ruby frameworks."""
        frameworks = []

        gem_deps = self.repo_configs.get("Gemfile", {}).get("dependencies", {})
        if "rails" in gem_deps:
            frameworks.append("rails")

        return frameworks

    def _detect_dart_frameworks(self) -> List[str]:
        """Detect Dart/Flutter frameworks."""
        frameworks = []

        pubspec_deps = self.repo_configs.get("pubspec.yaml", {}).get("dependencies", {})
        if "flutter" in pubspec_deps or "flutter_sdk" in pubspec_deps:
            frameworks.append("flutter")

        return frameworks

    def _detect_dotnet_frameworks(self) -> List[str]:
        """Detect .NET frameworks."""
        frameworks = []

        csproj_deps = self.repo_configs.get("csproj", {}).get("dependencies", {})
        if any(dep.startswith("Microsoft.AspNetCore") for dep in csproj_deps):
            frameworks.append("aspnet")

        return frameworks

    def enrich_file(
        self,
        rel_path: str,
        source: str,
        imports: List[Dict],
        classes: List[Dict],
        functions: List[Dict],
    ) -> Dict[str, Any]:
        """Enrich a file with framework metadata using repository context."""
        result = {
            "frameworks": [],
            "framework_metadata": {},
        }

        # Normalize path
        rel_path = rel_path.replace("\\", "/").lower()

        # Detect frameworks for this specific file
        detected = []

        # JavaScript/TypeScript
        if rel_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            if self._get_fw_module("nextjs").detect_nextjs(rel_path, source, imports, functions, self.repo_configs):
                detected.append("nextjs")
            if self._get_fw_module("react").detect_react(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("react")
            if self._get_fw_module("vue").detect_vue(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("vue")
            if self._get_fw_module("angular").detect_angular(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("angular")
            if self._get_fw_module("express").detect_express(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("express")
            if self._get_fw_module("nestjs").detect_nestjs(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("nestjs")

        # Python
        elif rel_path.endswith(".py"):
            if self._get_fw_module("django").detect_django(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("django")

        # PHP
        elif rel_path.endswith(".php"):
            if self._get_fw_module("laravel").detect_laravel(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("laravel")
            if self._get_fw_module("symfony").detect_symfony(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("symfony")

        # Ruby
        elif rel_path.endswith(".rb"):
            if self._get_fw_module("rails").detect_rails(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("rails")

        # Dart
        elif rel_path.endswith(".dart"):
            if self._get_fw_module("flutter").detect_flutter(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("flutter")

        # C#
        elif rel_path.endswith((".cs", ".csx")):
            if self._get_fw_module("aspnet").detect_aspnet(rel_path, source, imports, classes, functions, self.repo_configs):
                detected.append("aspnet")

        result["frameworks"] = detected

        # Enrich classes
        for cls in classes:
            cls_meta = {}
            if "react" in detected:
                meta = self._get_fw_module("react").enrich_class(cls)
                if meta:
                    cls_meta["react"] = meta
            if "vue" in detected:
                meta = self._get_fw_module("vue").enrich_class(cls)
                if meta:
                    cls_meta["vue"] = meta
            if "angular" in detected:
                meta = self._get_fw_module("angular").enrich_class(cls)
                if meta:
                    cls_meta["angular"] = meta
            if "django" in detected:
                meta = self._get_fw_module("django").enrich_class(cls)
                if meta:
                    cls_meta["django"] = meta
            if "rails" in detected:
                meta = self._get_fw_module("rails").enrich_class(cls)
                if meta:
                    cls_meta["rails"] = meta
            if "laravel" in detected:
                meta = self._get_fw_module("laravel").enrich_class(cls)
                if meta:
                    cls_meta["laravel"] = meta
            if "symfony" in detected:
                meta = self._get_fw_module("symfony").enrich_class(cls)
                if meta:
                    cls_meta["symfony"] = meta
            if "nestjs" in detected:
                meta = self._get_fw_module("nestjs").enrich_class(cls)
                if meta:
                    cls_meta["nestjs"] = meta
            if "aspnet" in detected:
                meta = self._get_fw_module("aspnet").enrich_class(cls)
                if meta:
                    cls_meta["aspnet"] = meta
            if cls_meta:
                cls["framework_metadata"] = cls_meta

        # Enrich functions
        for fn in functions:
            fn_meta = {}
            if "react" in detected:
                meta = self._get_fw_module("react").enrich_function(fn)
                if meta:
                    fn_meta["react"] = meta
            if "vue" in detected:
                meta = self._get_fw_module("vue").enrich_function(fn)
                if meta:
                    fn_meta["vue"] = meta
            if "angular" in detected:
                meta = self._get_fw_module("angular").enrich_function(fn)
                if meta:
                    fn_meta["angular"] = meta
            if "django" in detected:
                meta = self._get_fw_module("django").enrich_function(fn)
                if meta:
                    fn_meta["django"] = meta
            if "rails" in detected:
                meta = self._get_fw_module("rails").enrich_function(fn)
                if meta:
                    fn_meta["rails"] = meta
            if "laravel" in detected:
                meta = self._get_fw_module("laravel").enrich_function(fn)
                if meta:
                    fn_meta["laravel"] = meta
            if "nextjs" in detected:
                meta = self._get_fw_module("nextjs").enrich_function(fn, rel_path)
                if meta:
                    fn_meta["nextjs"] = meta
            if "flutter" in detected:
                meta = self._get_fw_module("flutter").enrich_function(fn)
                if meta:
                    fn_meta["flutter"] = meta
            if "express" in detected:
                meta = self._get_fw_module("express").enrich_function(fn)
                if meta:
                    fn_meta["express"] = meta
            if "nestjs" in detected:
                meta = self._get_fw_module("nestjs").enrich_function(fn)
                if meta:
                    fn_meta["nestjs"] = meta
            if "aspnet" in detected:
                meta = self._get_fw_module("aspnet").enrich_function(fn)
                if meta:
                    fn_meta["aspnet"] = meta
            if fn_meta:
                fn["framework_metadata"] = fn_meta

        return result
