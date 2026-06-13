"""
FrameworkDetector - Auto-detect test frameworks by scanning project config files.

:project: CodeCortex
:package: Modules.Codetester.Core.Framework
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""

import os
import subprocess
from typing import Optional, List, Tuple
from src.core.utils.process import try_get_version
from src.modules.codetester.core.dtos import FrameworkDetection

FRAMEWORK_SIGNATURES: List[Tuple[str, str, List[str], Optional[str], str]] = [
    ("pytest",        "pytest",     ["pyproject.toml", "pytest.ini", "setup.cfg", "conftest.py"],        "pytest --version",             "pytest"),
    ("unittest",      "unittest",   [],                                                                   "python -m unittest --version","python -m unittest discover"),
    ("jest",          "jest",       ["jest.config.js", "jest.config.ts", "jest.config.mjs", "jest.config.cjs", "jest.config.mjs"], "npx jest --version",          "npx jest"),
    ("vitest",        "vitest",     ["vitest.config.ts", "vitest.config.js", "vitest.config.mjs", "vitest.config.cjs"],               "npx vitest --version",        "npx vitest run"),
    ("go_test",       "go_test",    ["go.mod"],                                                           "go version",                   "go test ./..."),
    ("cargo_test",    "cargo_test", ["Cargo.toml"],                                                       "cargo --version",              "cargo test"),
    ("maven_test",    "maven_test", ["pom.xml"],                                                          "mvn --version",                "mvn test"),
    ("gradle",        "kotlin_test",["build.gradle", "build.gradle.kts", "settings.gradle"],             "gradle --version",             "gradle test"),
    ("phpunit",       "phpunit",    ["phpunit.xml", "phpunit.xml.dist"],                                  "phpunit --version",            "phpunit"),
    ("sbt_test",      "sbt_test",   ["build.sbt"],                                                        "sbt --version",                "sbt test"),
    ("swift_test",    "swift_test", ["Package.swift"],                                                    "swift --version",              "swift test"),
    ("flutter_test",  "flutter_test",["pubspec.yaml"],                                                    "flutter --version",            "flutter test"),
    ("dart_test",     "dart_test",  ["pubspec.yaml"],                                                     "dart --version",               "dart test"),
    ("rspec",         "ruby_test",  ["Gemfile", "spec/"],                                                 "ruby --version",               "bundle exec rspec"),
    ("dotnet_test",   "dotnet_test",["*.csproj", "*.sln"],                                                "dotnet --version",             "dotnet test"),
    ("haskell_test",  "haskell_test",["*.cabal", "stack.yaml", "package.yaml"],                          "ghc --version",                "cabal test"),
    ("elixir_test",   "elixir_test",["mix.exs"],                                                          "elixir --version",             "mix test"),
    ("perl_test",     "perl_test",  ["Makefile.PL", "Build.PL", "cpanfile"],                             "perl --version",               "make test"),
    ("ctest",         "ctest",      ["CMakeLists.txt"],                                                   "cmake --version",              "ctest"),
]

def detect_framework(target_path: str, preferred: Optional[str] = None) -> FrameworkDetection:
    """
    Auto-detect test framework from target_path.

    Scans project config files and returns the best matching FrameworkDetection.
    If preferred is set and valid, returns that framework immediately.
    """
    target_path = os.path.abspath(target_path)

    for name, adapter_key, config_files, version_cmd, _ in FRAMEWORK_SIGNATURES:
        if preferred and name != preferred:
            continue
        for cfg in config_files:
            resolved = _resolve_glob(target_path, cfg)
            if resolved and os.path.exists(resolved):
                version = try_get_version(target_path, version_cmd) if version_cmd else None
                return FrameworkDetection(
                    framework=name,
                    adapter_key=adapter_key,
                    config_file=resolved,
                    version=version,
                    project_dir=target_path,
                )

    if preferred:
        return FrameworkDetection(
            framework=preferred,
            adapter_key=preferred,
            project_dir=target_path,
        )

    fallback = _detect_language_fallback(target_path)
    if fallback:
        return fallback

    return FrameworkDetection(
        framework="pytest",
        adapter_key="pytest",
        project_dir=target_path,
    )

def get_run_command(detection: FrameworkDetection) -> str:
    """Return the base run command for a detected framework."""
    for name, _, _, _, run_cmd in FRAMEWORK_SIGNATURES:
        if name == detection.framework:
            return run_cmd
    return "pytest"

def _resolve_glob(base: str, pattern: str) -> Optional[str]:
    """Resolve a glob-like pattern to a single file path."""
    if "*" not in pattern:
        candidate = os.path.join(base, pattern)
        return candidate if os.path.exists(candidate) else None
    import glob as glob_module
    matches = glob_module.glob(os.path.join(base, pattern))
    return matches[0] if matches else None

def _detect_language_fallback(target_path: str) -> Optional[FrameworkDetection]:
    """Fallback detection based on file extensions present."""
    py_files = 0
    js_files = 0
    ts_files = 0
    rs_files = 0
    go_files = 0
    for root, _, files in os.walk(target_path):
        if ".git" in root or "__pycache__" in root or "node_modules" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                py_files += 1
            elif f.endswith(".js"):
                js_files += 1
            elif f.endswith(".ts") or f.endswith(".tsx"):
                ts_files += 1
            elif f.endswith(".rs"):
                rs_files += 1
            elif f.endswith(".go"):
                go_files += 1
        if py_files > 0 or js_files > 0 or ts_files > 0:
            break

    if py_files > 0:
        return FrameworkDetection(framework="pytest", adapter_key="pytest", project_dir=target_path)
    if ts_files > 0:
        return FrameworkDetection(framework="jest", adapter_key="jest", project_dir=target_path)
    if js_files > 0:
        return FrameworkDetection(framework="jest", adapter_key="jest", project_dir=target_path)
    if rs_files > 0:
        return FrameworkDetection(framework="cargo_test", adapter_key="cargo_test", project_dir=target_path)
    if go_files > 0:
        return FrameworkDetection(framework="go_test", adapter_key="go_test", project_dir=target_path)
    return None
