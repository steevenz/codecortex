"""Configuration file parser for repository-level framework detection."""
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import re


class ConfigParser:
    """Parse project configuration files to detect frameworks and versions."""
    
    @staticmethod
    def parse_package_json(repo_root: Path) -> Dict[str, Any]:
        """Parse package.json for JavaScript/TypeScript projects."""
        package_json = repo_root / "package.json"
        if not package_json.exists():
            return {}
        
        try:
            with open(package_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            dependencies = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {})
            }
            
            return {
                "dependencies": dependencies,
                "name": data.get("name"),
                "version": data.get("version"),
            }
        except (json.JSONDecodeError, IOError):
            return {}
    
    @staticmethod
    def parse_composer_json(repo_root: Path) -> Dict[str, Any]:
        """Parse composer.json for PHP projects."""
        composer_json = repo_root / "composer.json"
        if not composer_json.exists():
            return {}
        
        try:
            with open(composer_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            require = {
                **data.get("require", {}),
                **data.get("require-dev", {})
            }
            
            return {
                "dependencies": require,
                "name": data.get("name"),
                "version": data.get("version"),
            }
        except (json.JSONDecodeError, IOError):
            return {}
    
    @staticmethod
    def parse_gemfile(repo_root: Path) -> Dict[str, Any]:
        """Parse Gemfile for Ruby projects."""
        gemfile = repo_root / "Gemfile"
        gemfile_lock = repo_root / "Gemfile.lock"
        
        dependencies = {}
        
        # Parse Gemfile
        if gemfile.exists():
            try:
                with open(gemfile, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Match gem "name" or gem 'name', "version"
                    gem_pattern = r"gem\s+['\"]([^'\"]+)['\"](?:\s*,\s*['\"]?([^'\"]+)['\"]?)?"
                    for match in re.finditer(gem_pattern, content):
                        name = match.group(1)
                        version = match.group(2)
                        dependencies[name] = version if version else None
            except IOError:
                pass
        
        # Parse Gemfile.lock for exact versions
        if gemfile_lock.exists():
            try:
                with open(gemfile_lock, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Match gems in lock file
                    lock_pattern = r"^\s{4}([a-z0-9_\-]+)\s+\(([^)]+)\)"
                    for match in re.finditer(lock_pattern, content, re.MULTILINE):
                        name = match.group(1)
                        version = match.group(2)
                        dependencies[name] = version
            except IOError:
                pass
        
        return {"dependencies": dependencies}
    
    @staticmethod
    def parse_requirements_txt(repo_root: Path) -> Dict[str, Any]:
        """Parse requirements.txt for Python projects."""
        requirements_files = [
            repo_root / "requirements.txt",
            repo_root / "requirements-dev.txt",
            repo_root / "dev-requirements.txt",
            repo_root / "pyproject.toml",
        ]
        
        dependencies = {}
        
        for req_file in requirements_files:
            if not req_file.exists():
                continue
            
            try:
                with open(req_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    if req_file.name == "pyproject.toml":
                        # Parse pyproject.toml (simplified)
                        deps_section = re.search(r"dependencies\s*=\s*\[([^\]]+)\]", content, re.DOTALL)
                        if deps_section:
                            for dep in re.findall(r'["\']([^"\']+)["\']', deps_section.group(1)):
                                name = dep.split(">=")[0].split("==")[0].split("<")[0].strip()
                                dependencies[name] = None
                    else:
                        # Parse requirements.txt
                        for line in content.splitlines():
                            line = line.strip()
                            if not line or line.startswith("#") or line.startswith("-"):
                                continue
                            # Extract package name (before version specifier)
                            name = re.split(r"[<>=!~]", line)[0].strip()
                            if name:
                                dependencies[name] = None
            except IOError:
                continue
        
        return {"dependencies": dependencies}
    
    @staticmethod
    def parse_pubspec_yaml(repo_root: Path) -> Dict[str, Any]:
        """Parse pubspec.yaml for Dart/Flutter projects."""
        pubspec = repo_root / "pubspec.yaml"
        if not pubspec.exists():
            return {}
        
        try:
            with open(pubspec, "r", encoding="utf-8") as f:
                content = f.read()
            
            dependencies = {}
            # Parse dependencies section
            deps_section = re.search(r"dependencies:\s*\n((?:\s{2}[^\n]+\n)+)", content)
            if deps_section:
                for line in deps_section.group(1).splitlines():
                    match = re.match(r"\s{2}([a-z_][a-z0-9_]*):\s*(.+)", line)
                    if match:
                        name = match.group(1)
                        version = match.group(2)
                        dependencies[name] = version
            
            return {"dependencies": dependencies}
        except IOError:
            return {}
    
    @staticmethod
    def parse_csproj(repo_root: Path) -> Dict[str, Any]:
        """Parse .csproj files for .NET projects."""
        csproj_files = list(repo_root.glob("*.csproj"))
        if not csproj_files:
            return {}
        
        dependencies = {}
        
        for csproj in csproj_files:
            try:
                with open(csproj, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Parse PackageReference elements
                package_pattern = r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"'
                for match in re.finditer(package_pattern, content):
                    name = match.group(1)
                    version = match.group(2)
                    dependencies[name] = version
            except IOError:
                continue
        
        return {"dependencies": dependencies}
    
    @staticmethod
    def parse_all_configs(repo_root: Path) -> Dict[str, Any]:
        """Parse all configuration files and return combined results."""
        return {
            "package.json": ConfigParser.parse_package_json(repo_root),
            "composer.json": ConfigParser.parse_composer_json(repo_root),
            "Gemfile": ConfigParser.parse_gemfile(repo_root),
            "requirements.txt": ConfigParser.parse_requirements_txt(repo_root),
            "pubspec.yaml": ConfigParser.parse_pubspec_yaml(repo_root),
            "csproj": ConfigParser.parse_csproj(repo_root),
        }
