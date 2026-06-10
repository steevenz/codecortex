"""
Global constants and enumerations for the PyScaffold generator engine.

:project: CodeCortex
:package: Modules.Scaffolder.Core.Constants
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""

from __future__ import annotations

from enum import Enum

class StackType(str, Enum):
    """Supported technology stacks for project generation."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    NODEJS_TYPESCRIPT = "nodejs-typescript"
    PHP = "php"
    GO = "go"
    JAVA = "java"
    KOTLIN = "kotlin"
    FLUTTER = "flutter"
    CSHARP = "csharp"
    SWIFT = "swift"
    RUST = "rust"
    CPP = "cpp"
    DART = "dart"
    CSS_SCSS = "css-scss"

class ProjectPattern(str, Enum):
    """Architectural patterns for generated projects (per project-structure-standard.md)."""
    LAYERED = "layered"       # Pattern A: Clean Architecture
    DDD = "ddd"               # Pattern B: DDD Modules
    FSD = "fsd"               # Pattern C: Feature-Sliced Design

class LicenseIdentifier(str, Enum):
    """Available license types for generated projects."""
    MIT = "MIT"
    APACHE_2 = "Apache-2.0"
    GPL_3 = "GPL-3.0"
    BSD_3 = "BSD-3-Clause"
    COMMERCIAL_COMPANY = "Commercial-Company"
    COMMERCIAL_PERSONAL = "Commercial-Personal"
    PRIVATE_COMPANY = "Private-Company"
    PRIVATE_PERSONAL = "Private-Personal"
    NONE = "None"

class FileConvention(str, Enum):
    """File/directory naming conventions per coding-standard.md."""
    SNAKE_CASE = "snake_case"       # Python, Rust, C++, Go
    KEBAB_CASE = "kebab-case"       # TS/JS directories, CSS/SCSS
    PASCAL_CASE = "PascalCase"      # PHP, C#, Swift directories
    LOWERCASE = "lowercase"         # Java, Kotlin directories

# ---------------------------------------------------------------------------
# Standard-mandated directory structure (project-structure-standard.md §2.1)
# ---------------------------------------------------------------------------

STANDARD_ROOT_DIRECTORIES: list[str] = [
    "src",
    "public",
    "storage",
    "database",
    "config",
    "tests",
    "scripts",
    "debugs",
    "outputs",
    "releases",
    "docs",
    "datasets",
    ".aicoders",
    ".agents",
]

STANDARD_TEST_DIRECTORIES: list[str] = [
    "tests/Unit",
    "tests/Integration",
    "tests/Feature",
    "tests/fixtures",
]

STANDARD_SCRIPTS_DIRECTORIES: list[str] = [
    "scripts/debug",
    "scripts/cron",
    "scripts/injection",
    "scripts/setup",
    "scripts/migration",
    "scripts/maintenance",
]

STANDARD_OUTPUTS_DIRECTORIES: list[str] = [
    "outputs/results",
    "outputs/temp",
    "outputs/debug",
    "outputs/logs",
]

STANDARD_DOCS_DIRECTORIES: list[str] = [
    "docs",
    "docs/drafts",
    "docs/archives",
    "docs/product",
    "docs/architecture",
    "docs/architecture/concepts",
    "docs/architecture/api",
    "docs/architecture/codebase",
    "docs/architecture/database",
    "docs/features",
    "docs/guides",
    "docs/guides/setup",
    "docs/guides/deployment",
    "docs/guides/operations",
    "docs/versions",
]

# ---------------------------------------------------------------------------
# AI Context directories (per ~/.aicoders/rules)
# ---------------------------------------------------------------------------

AICODERS_DIRECTORIES: list[str] = [
    ".aicoders",
    ".aicoders/rules",
    ".aicoders/docs",
    ".aicoders/docs/standards",
]

AGENTS_DIRECTORIES: list[str] = [
    ".agents",
    ".agents/contexts",
    ".agents/states",
    ".agents/workflows",
]

# ---------------------------------------------------------------------------
# Module internal structure (project-structure-standard.md §8)
# ---------------------------------------------------------------------------

MODULE_DIRECTORIES: list[str] = [
    "Controllers/Http",
    "Controllers/Cli",
    "Presenters",
    "ViewModels",
    "Views",
    "Models/Entities",
    "Models/ValueObjects",
    "Models/Aggregates",
    "Services",
    "Repositories/Contracts",
    "DTOs",
    "Events",
    "Listeners",
    "Jobs",
    "Middleware",
    "Factories",
    "Seeders",
    "Migrations",
    "Enums",
    "Traits",
    "Helpers",
    "Validators",
    "Mappers",
    "Filters",
    "Exceptions",
    "Providers",
    "Observers",
    "Strategies",
    "Contracts",
    "Plugins",
    "Config",
    "Languages",
    "Libraries",
    "Tests/Unit",
    "Tests/Integration",
    "assets",
    "themes",
]

# ---------------------------------------------------------------------------
# Stack sub-directory structure (created inside src/ for non-modular layouts)
# ---------------------------------------------------------------------------

SRC_SUBDIRECTORIES_LAYERED: list[str] = [
    "core",
    "app",
    "api",
    "helpers",
]

SRC_SUBDIRECTORIES_DDD: list[str] = [
    "Modules",
    "core",
    "app",
    "api",
]

# ---------------------------------------------------------------------------
# File header formats per coding-standard.md / project-structure-standard.md §4.1
# ---------------------------------------------------------------------------

FILE_HEADER_FORMATS: dict[str, str] = {
    "python": (
        '"""\n'
        "@project   {project_name}\n"
        "@package   {package_path}\n"
        "@author    {author}\n"
        "@copyright (c) {author}\n"
        "@fileoverview {description}\n"
        '"""\n'
    ),
    "typescript": (
        "/**\n"
        " * @project   {project_name}\n"
        " * @package   {package_path}\n"
        " * @author    {author}\n"
        " * @copyright (c) {author}\n"
        " * @fileoverview {description}\n"
        " */\n"
    ),
    "javascript": (
        "/**\n"
        " * @project   {project_name}\n"
        " * @package   {package_path}\n"
        " * @author    {author}\n"
        " * @copyright (c) {author}\n"
        " * @fileoverview {description}\n"
        " */\n"
    ),
    "nodejs-typescript": (
        "/**\n"
        " * @project   {project_name}\n"
        " * @package   {package_path}\n"
        " * @author    {author}\n"
        " * @copyright (c) {author}\n"
        " * @fileoverview {description}\n"
        " */\n"
    ),
    "php": (
        "<?php\n"
        "/**\n"
        " * @project   {project_name}\n"
        " * @package   {package_path}\n"
        " * @author    {author}\n"
        " * @copyright (c) {author}\n"
        " * @fileoverview {description}\n"
        " */\n"
    ),
    "go": (
        "// Package {package_name} — {description}\n"
        "//\n"
        "// Copyright (c) {author}\n"
    ),
    "java": (
        "/**\n"
        " * Project: {project_name}\n"
        " * Package: {package_path}\n"
        " * Author: {author}\n"
        " * Copyright (c) {author}\n"
        " * File overview: {description}\n"
        " */\n"
    ),
    "kotlin": (
        "/**\n"
        " * Project: {project_name}\n"
        " * Package: {package_path}\n"
        " * Author: {author}\n"
        " * Copyright (c) {author}\n"
        " * File overview: {description}\n"
        " */\n"
    ),
    "csharp": (
        "// <copyright file=\"{filename}\" company=\"{project_name}\">\n"
        "// Copyright (c) {author}. All rights reserved.\n"
        "// Licensed under the MIT License.\n"
        "// </copyright>\n"
        "// <summary>{description}</summary>\n"
    ),
    "swift": (
        "///\n"
        "/// @project   {project_name}\n"
        "/// @package   {package_path}\n"
        "/// @author    {author}\n"
        "/// @copyright (c) {author}\n"
        "/// @fileoverview {description}\n"
        "///\n"
    ),
    "rust": (
        "//!\n"
        "//! @project   {project_name}\n"
        "//! @package   {package_path}\n"
        "//! @author    {author}\n"
        "//! @copyright (c) {author}\n"
        "//! @fileoverview {description}\n"
        "//!\n"
    ),
    "cpp": (
        "/**\n"
        " * @project   {project_name}\n"
        " * @package   {package_path}\n"
        " * @author    {author}\n"
        " * @copyright (c) {author}\n"
        " * @fileoverview {description}\n"
        " */\n"
    ),
    "dart": (
        "///\n"
        "/// @project   {project_name}\n"
        "/// @package   {package_path}\n"
        "/// @author    {author}\n"
        "/// @copyright (c) {author}\n"
        "/// @fileoverview {description}\n"
        "///\n"
    ),
    "flutter": (
        "///\n"
        "/// @project   {project_name}\n"
        "/// @package   {package_path}\n"
        "/// @author    {author}\n"
        "/// @copyright (c) {author}\n"
        "/// @fileoverview {description}\n"
        "///\n"
    ),
    "css-scss": (
        "/**\n"
        " * @project   {project_name}\n"
        " * @package   {package_path}\n"
        " * @author    {author}\n"
        " * @copyright (c) {author}\n"
        " * @fileoverview {description}\n"
        " */\n"
    ),
    "shell": (
        "#!/bin/bash\n"
        "# @project   {project_name}\n"
        "# @category  {package_path}\n"
        "# @author    {author}\n"
        "# @copyright (c) {author}\n"
        "# @fileoverview {description}\n"
    ),
}

# ---------------------------------------------------------------------------
# Default version for newly generated projects
# ---------------------------------------------------------------------------

DEFAULT_PROJECT_VERSION: str = "0.1.0"

# Template directories
TEMPLATES_BASE_DIR: str = "datasets/templates"
SHARED_TEMPLATES_DIR: str = "_shared"
