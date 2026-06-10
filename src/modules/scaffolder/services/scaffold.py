"""
Scaffold — main orchestrator that assembles directories, renders templates,.

:project: CodeCortex
:package: Modules.Scaffolder.Services.Scaffold
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path
from typing import Any, Callable, Optional

from ..core.constants import (
    AICODERS_DIRECTORIES,
    AGENTS_DIRECTORIES,
    DEFAULT_PROJECT_VERSION,
    MODULE_DIRECTORIES,
    SRC_SUBDIRECTORIES_DDD,
    SRC_SUBDIRECTORIES_LAYERED,
    STANDARD_DOCS_DIRECTORIES,
    STANDARD_OUTPUTS_DIRECTORIES,
    STANDARD_ROOT_DIRECTORIES,
    STANDARD_SCRIPTS_DIRECTORIES,
    STANDARD_TEST_DIRECTORIES,
    FileConvention,
    ProjectPattern,
)
from ..core.exceptions import (
    ProjectAlreadyExistsError,
    ScaffoldError,
    StackNotFoundError,
)
from ..core.dtos import Project, Template
from ..core.interfaces import StackRepository, TemplateRepository
from src.core import FileHeader
from src.core.templating import Engine as CoreEngine

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[str], None]]

class Engine(CoreEngine):
    """Scaffolder-specific Jinja2 engine that works with ``Template`` DTOs."""

    def render_template(self, template: Template) -> str:
        return super().render_template(template.source_path, template.variables)

class Scaffold:
    """Orchestrates the full project scaffolding pipeline."""

    def __init__(
        self,
        stack_repository: StackRepository,
        template_repository: TemplateRepository,
        template_engine: Engine,
        file_header: FileHeader,
    ) -> None:
        self._stack_repo = stack_repository
        self._template_repo = template_repository
        self._engine = template_engine
        self._header = file_header

    def scaffold(
        self,
        project: Project,
        *,
        progress: ProgressCallback = None,
        overwrite: bool = False,
    ) -> bool:
        target = project.target_path

        if target.exists() and not overwrite:
            raise ProjectAlreadyExistsError(str(target))

        stack = self._stack_repo.get_stack(project.stack_name)
        if stack is None:
            raise StackNotFoundError(project.stack_name)

        context = project.template_context()
        context["header_format"] = stack.header_format or ""

        try:
            self._create_directories(target, stack, project, progress)
            self._write_shared_templates(target, context, progress)
            self._write_stack_templates(target, stack, project, context, progress)
            self._write_version_file(target, project, progress)
            self._write_license_file(target, project, progress)
            self._write_dot_files(target, project, progress)
            self._write_init_files(target, stack, project, progress)
            self._write_ai_context_files(target, project, progress)
            self._write_project_docs(target, project, progress)

            self._notify(progress, f"✅ Project '{project.name.display}' scaffolded successfully!")
            return True

        except (ProjectAlreadyExistsError, StackNotFoundError):
            raise
        except Exception as exc:
            logger.error("Scaffold failed: %s", exc, exc_info=True)
            raise ScaffoldError(str(exc)) from exc

    @staticmethod
    def _apply_dir_convention(name: str, convention: FileConvention) -> str:
        """Convert a canonical dir name to the stack-specific naming convention.

        Canonical names are in PascalCase-with-underscores (e.g. ``ValueObjects``,
        ``Controllers/Http``). This method transforms them per the target convention.
        """
        import re
        parts = name.replace("-", "_").split("/")
        converted = []
        for part in parts:
            if convention == FileConvention.KEBAB_CASE:
                slug = re.sub(r"(?<=[a-z])(?=[A-Z])", "-", part).lower()
                converted.append(slug.replace("_", "-"))
            elif convention == FileConvention.PASCAL_CASE:
                pascal = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", part).title().replace(" ", "")
                converted.append(pascal.replace("_", ""))
            elif convention == FileConvention.LOWERCASE:
                flattened = re.sub(r"(?<=[a-z])(?=[A-Z])", "", part).lower()
                converted.append(flattened.replace("_", ""))
            else:
                snaked = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", part).lower()
                converted.append(snaked)
        return "/".join(converted)

    def _create_directories(
        self,
        target: Path,
        stack: Any,
        project: Project,
        progress: ProgressCallback,
    ) -> None:
        self._notify(progress, "Creating directory structure...")

        dir_convention = (
            stack.file_conventions.directories
            if stack.file_conventions
            else FileConvention.SNAKE_CASE
        )

        all_dirs: list[str] = list(STANDARD_ROOT_DIRECTORIES)

        pt = project.project_type

        if pt.pattern in (ProjectPattern.DDD, ProjectPattern.FSD):
            all_dirs.extend(SRC_SUBDIRECTORIES_DDD)
        else:
            all_dirs.extend(SRC_SUBDIRECTORIES_LAYERED)

        test_dirs = [
            self._apply_dir_convention(d, dir_convention)
            for d in STANDARD_TEST_DIRECTORIES
        ]
        all_dirs.extend(test_dirs)
        all_dirs.extend(STANDARD_SCRIPTS_DIRECTORIES)
        all_dirs.extend(STANDARD_OUTPUTS_DIRECTORIES)
        all_dirs.extend(STANDARD_DOCS_DIRECTORIES)
        all_dirs.extend(AICODERS_DIRECTORIES)
        all_dirs.extend(AGENTS_DIRECTORIES)

        if pt.extra_directories:
            all_dirs.extend(pt.extra_directories)

        if pt.pattern == ProjectPattern.DDD:
            module_base = self._apply_dir_convention("Modules", dir_convention)
            module_name = project.name.slug
            for mdir in MODULE_DIRECTORIES:
                converted = self._apply_dir_convention(mdir, dir_convention)
                all_dirs.append(f"{module_base}/{module_name}/{converted}")

        if project.include_ai and pt.conditional_modules.get("ai"):
            all_dirs.append("src/ai")
        if project.include_trainer and pt.conditional_modules.get("trainer"):
            all_dirs.append("src/trainer")

        seen: set[str] = set()
        unique_dirs: list[str] = []
        for d in all_dirs:
            if d not in seen:
                seen.add(d)
                unique_dirs.append(d)

        for dir_path in unique_dirs:
            full_path = target / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            self._notify(progress, f"  📁 {dir_path}/")

    def _write_shared_templates(
        self,
        target: Path,
        context: dict[str, Any],
        progress: ProgressCallback,
    ) -> None:
        self._notify(progress, "Rendering shared templates...")
        templates = self._template_repo.get_shared_templates()
        for tmpl in templates:
            enriched = tmpl.with_variables(context)
            self._render_and_write(target, enriched, progress)

    def _write_stack_templates(
        self,
        target: Path,
        stack: Any,
        project: Project,
        context: dict[str, Any],
        progress: ProgressCallback,
    ) -> None:
        self._notify(progress, f"Rendering {stack.display_name} templates...")
        templates = self._template_repo.get_stack_templates(stack.name, project.project_type.id)
        for tmpl in templates:
            enriched = tmpl.with_variables(context)
            self._render_and_write(target, enriched, progress)

    def _write_version_file(
        self,
        target: Path,
        project: Project,
        progress: ProgressCallback,
    ) -> None:
        version_file = target / ".version"
        version_file.write_text(str(project.version) + "\n", encoding="utf-8")
        self._notify(progress, "  📄 .version")

    def _write_license_file(
        self,
        target: Path,
        project: Project,
        progress: ProgressCallback,
    ) -> None:
        if project.license.is_none:
            return
        content = project.license.render_content(project.author, project.created_at.year)
        if content:
            license_file = target / "LICENSE"
            license_file.write_text(content, encoding="utf-8")
            self._notify(progress, "  📄 LICENSE")

    def _write_dot_files(
        self,
        target: Path,
        project: Project,
        progress: ProgressCallback,
    ) -> None:
        author_content = (
            f"name: {project.author}\n"
            f"email: {project.email}\n"
            f"role: owner\n"
        )
        (target / ".author").write_text(author_content, encoding="utf-8")
        self._notify(progress, "  📄 .author")

        ai_ignore_content = (
            "vendor/\nnode_modules/\n__pycache__/\n.git/\n"
            "outputs/\nstorage/\nreleases/\ndatasets/\n"
            "*.pyc\n.env\n"
        )
        (target / ".aiignore").write_text(ai_ignore_content, encoding="utf-8")
        self._notify(progress, "  📄 .aiignore")

    def _write_init_files(
        self,
        target: Path,
        stack: Any,
        project: Project,
        progress: ProgressCallback,
    ) -> None:
        if stack.name != "python":
            return

        self._notify(progress, "Creating package init files...")
        src_dir = target / "src"
        if not src_dir.exists():
            return

        for dirpath, dirnames, _filenames in os.walk(src_dir):
            dir_p = Path(dirpath)
            init_file = dir_p / "__init__.py"
            if not init_file.exists():
                rel = dir_p.relative_to(target)
                package_path = str(rel).replace(os.sep, ".")

                header = self._header.generate_for_init(
                    project_name=project.name.display,
                    package_path=package_path,
                    author=project.author,
                    stack_name="python",
                )
                init_file.write_text(header, encoding="utf-8")
                self._notify(progress, f"  📄 {rel / '__init__.py'}")

    def _write_ai_context_files(
        self,
        target: Path,
        project: Project,
        progress: ProgressCallback,
    ) -> None:
        """Generate AI context files for the project."""
        self._notify(progress, "Creating AI context structure...")
        
        # Create .agents/contexts/working.md
        agents_context_dir = target / ".agents" / "contexts"
        agents_context_dir.mkdir(parents=True, exist_ok=True)
        
        working_content = f"""---
Version: 1.0.0
Date: {project.created_at.strftime("%Y-%m-%d")}
---

# Working Context — {project.name.display}

## Current Truth
- **Active Task**: Greenfield project initialization
- **Project Root**: {target}
- **Stack**: {project.stack_name}
- **Project Type**: {project.project_type.id}
- **Python**: 3.12 | **Package Manager**: UV | **MCP**: FastMCP (stdio)
- **Database**: SQLite (WAL)

## Core Status
- Project structure generated with {len(STANDARD_ROOT_DIRECTORIES)} standard directories
- AI context structure initialized
- Documentation structure initialized

## Context Gap
- No context gaps for greenfield project

## Done List
- [x] Project directory structure created
- [x] AI context directories created
- [x] Documentation directories created
- [x] Standard directories created

## Target Queue
1. [ ] Implement business logic
2. [ ] Write unit tests
3. [ ] Add CI/CD configuration
4. [ ] Deploy to production
"""
        (agents_context_dir / "working.md").write_text(working_content, encoding="utf-8")
        self._notify(progress, "  📄 .agents/contexts/working.md")
        
        # Create .agents/states/current.yaml
        agents_states_dir = target / ".agents" / "states"
        agents_states_dir.mkdir(parents=True, exist_ok=True)
        
        current_content = f"""version: 1.0.0
date: {project.created_at.strftime("%Y-%m-%d")}
state: initialization
phase: greenfield
project: {project.name.display}
stack: {project.stack_name}
project_type: {project.project_type.id}
author: {project.author}
"""
        (agents_states_dir / "current.yaml").write_text(current_content, encoding="utf-8")
        self._notify(progress, "  📄 .agents/states/current.yaml")
        
        # Create .aicoders/rules/ directory
        aicoders_rules_dir = target / ".aicoders" / "rules"
        aicoders_rules_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy standard rules from CodeCortex
        rules_content = """# Architecture Compliance Rules

> **Standard:** Aegis-Architecture-v1.0
> **Applies to:** All domains/modules in this project

## 1. Lego Principle (Modular Monolith)

- Each domain MUST be self-contained with clear boundaries
- Cross-domain dependencies MUST go through adapters/DTOs only
- No direct imports of internal module files from other domains
- Domain entry points: `api/tools.py` (MCP), `api/cli.py` (CLI)

## 2. Dependency Injection / IoC

- **Constructor injection ONLY** — no hardcoded `new Class()` or service locators
- All dependencies MUST be injected via `__init__` parameters
- Orchestrator factory pattern for MCP tools (avoids circular imports)

## 3. DTO Boundaries

- **Raw ORM models / HTTP requests MUST NOT leak across layers**
- Use DTOs (dataclasses) for ALL layer crossings
- DTOs MUST have `to_dict()` method for serialization
- DTO `to_dict()` MUST truncate large fields for token economy

## 4. Adapter Pattern

- All 3rd-party SDK interactions MUST be wrapped in local adapters
- Format parsing (docx, pdf, xlsx, pptx) → `adapters/format_parser.py`
- Storage (SQLite + GoldenKnowledgeStore) → `adapters/storage.py`
- No direct 3rd-party imports in core/domain logic

## 5. Codification

- Machine IDs: UUID (12-char truncated for display)
- Human codes: Readable business codes (e.g., KG_001, KG_EXTRACT_ERROR)
- Error codes MUST follow domain prefix pattern: `{DOMAIN}_{number}`

## 6. Clean Architecture Layers

```
api/        → MCP tools, CLI commands (input adapters)
core/       → Business logic, extraction, classification, graph
adapters/   → External service wrappers (storage, format_parser)
models/     → DTOs (chunk, relationship)
```

## 7. Compliance Checklist

- [ ] Constructor injection used everywhere
- [ ] DTOs used for all layer crossings
- [ ] No raw model leaks to API layer
- [ ] Adapters wrap all 3rd-party dependencies
- [ ] Error codes follow domain prefix standard
- [ ] `api_response()` used for all MCP tool responses
- [ ] `api/tools.py` and `api/cli.py` are the ONLY public APIs
"""
        (aicoders_rules_dir / "architecture.md").write_text(rules_content, encoding="utf-8")
        self._notify(progress, "  📄 .aicoders/rules/architecture.md")

    def _write_project_docs(
        self,
        target: Path,
        project: Project,
        progress: ProgressCallback,
    ) -> None:
        """Generate project documentation files."""
        self._notify(progress, "Creating project documentation...")
        
        # Create docs/features/{domain}/concept.md
        domain_name = project.name.slug
        docs_features_dir = target / "docs" / "features" / domain_name
        docs_features_dir.mkdir(parents=True, exist_ok=True)
        
        concept_content = f"""# {project.name.display}: {project.name.display}

> **Domain:** {domain_name}
> **Package:** `src/`
> **Version:** {project.version}
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

{domain_name} is a greenfield project initialized with {project.stack_name} stack and {project.project_type.display_name} pattern.

## Why This Exists

- Rapid project initialization with standard structure
- AI coder-friendly directory structure
- Compliance with Aegis Codeworks standards
- Ready for immediate development

## Architecture

```
{domain_name}/
├── src/
│   ├── core/
│   ├── api/
│   ├── services/
│   └── adapters/
├── tests/
├── docs/
├── scripts/
└── outputs/
```

## Domain Boundary

- Owns: All project-specific code and documentation
- Does NOT own: External dependencies, 3rd-party SDKs
- Dependencies: External services via adapters

## CLI Architecture Note

CLI domain name: {domain_name}
Aliases: {domain_name[:3]}

## ~/.aicoders/ Compliance

- Follows Aegis-Architecture-v1.0 standards
- Constructor injection for all services
- DTOs for all layer crossings
- Adapters wrap all 3rd-party dependencies

## Error Codes

| Prefix | Tool |
|--------|------|
| {domain_name.upper()}_001 | Validation errors |
| {domain_name.upper()}_002 | Not found errors |
| {domain_name.upper()}_500 | Internal errors |

## AI Coder Impact Features

1. Standard directory structure for immediate context
2. AI context files for session continuity
3. Documentation structure for discoverability
4. Dry-run safety for validation
5. Multi-stack support with proper naming conventions
6. Template context for customization
7. Decision Matrix class generation
8. Boilerplate generation for rapid development
9. License generation for compliance
10. Version management for releases

## Related Sub-Features

- Project initialization
- Class generation
- Boilerplate generation
- Documentation generation
"""
        (docs_features_dir / "concept.md").write_text(concept_content, encoding="utf-8")
        self._notify(progress, f"  📄 docs/features/{domain_name}/concept.md")
        
        # Create docs/architecture/ARCHITECTURE.md
        docs_arch_dir = target / "docs" / "architecture"
        docs_arch_dir.mkdir(parents=True, exist_ok=True)
        
        arch_content = f"""# Architecture — {project.name.display}

> **Standard:** Aegis-Architecture-v1.0
> **Project:** {project.name.display}
> **Stack:** {project.stack_name}
> **Pattern:** {project.project_type.pattern.value}

## Domain Map

```
{domain_name}/
├── src/
│   ├── core/           → Business logic, domain entities
│   ├── api/            → API endpoints, controllers
│   ├── services/       → Business services
│   └── adapters/       → External integrations
├── tests/
│   ├── Unit/            → Unit tests
│   ├── Integration/     → Integration tests
│   └── Feature/         # Feature tests
├── docs/
│   ├── architecture/    → Architecture docs
│   ├── features/        # Feature docs
│   └── guides/          # User guides
└── scripts/
    ├── setup/           # Setup scripts
    ├── migration/       # Migration scripts
    └── maintenance/    # Maintenance scripts
```

## Clean Architecture Layers

```
api/        → Input adapters (MCP tools, CLI commands)
core/       → Business logic, domain entities, services
adapters/   → External service wrappers (storage, 3rd-party APIs)
models/     → DTOs (dataclasses for layer crossings)
```

## Dependency Injection

All services use constructor injection:
- StackRepository → injected via constructor
- TemplateRepository → injected via constructor
- TemplateEngine → injected via constructor
- FileHeader → injected via constructor

## Domain Boundaries

- Owns: Project-specific business logic
- Does NOT own: External 3rd-party SDKs (wrapped in adapters)
- Dependencies: External services via adapters only
"""
        (docs_arch_dir / "ARCHITECTURE.md").write_text(arch_content, encoding="utf-8")
        self._notify(progress, "  📄 docs/architecture/ARCHITECTURE.md")
        
        # Create docs/architecture/SECURITY.md
        security_content = f"""# Security — {project.name.display}

> **Standard:** Aegis-Security-v1.0
> **Project:** {project.name.display}
> **Stack:** {project.stack_name}

## Security Principles

1. **Path Validation:** All file paths validated before access
2. **Input Sanitization:** All user inputs sanitized before processing
3. **Secrets Management:** Secrets stored in environment variables, never in code
4. **Dependency Scanning:** Dependencies scanned for vulnerabilities
5. **Access Control:** Proper access controls on sensitive operations

## SSRF Protection

- All URLs validated before fetching
- Path traversal prevention on file operations
- Label sanitization on user inputs

## Secrets Management

- Use .env.example for template
- Never commit .env files
- Use environment variables for all secrets
- Rotate secrets regularly

## Access Control

- Implement proper authentication for sensitive operations
- Use principle of least privilege
- Audit access logs regularly
"""
        (docs_arch_dir / "SECURITY.md").write_text(security_content, encoding="utf-8")
        self._notify(progress, "  📄 docs/architecture/SECURITY.md")
        
        # Create AGENTS.md
        agents_content = f"""# AGENTS.md — Project Operating Manual for AI Agents

> **Project:** {project.name.display}
> **Package:** src/
> **Version:** 1.0.0
> **Last Updated:** {project.created_at.strftime("%Y-%m-%d")}
> **Author:** {project.author}

## 0. Project Overview

{project.name.display} is a greenfield project initialized with {project.stack_name} stack and {project.project_type.display_name} pattern.

## 1. Project Name
{project.name.display}

## 2. Project Path
{target}

## 3. Project Stack
{project.stack_name}

## 4. Project Type
{project.project_type.id} ({project.project_type.display_name})

## 5. Project Standards

- Architecture: Aegis-Architecture-v1.0
- Project Structure: Aegis-ProjectStructure-v1.0
- API: Aegis-API-v1.0
- Documentation: Aegis-Documentation-v1.0

## 6. Setup

Run `uv sync` to install dependencies.

## 7. Run

Run `python -m src.main` to start the application.

## 8. Test

Run `pytest tests/` to run tests.
"""
        (target / "AGENTS.md").write_text(agents_content, encoding="utf-8")
        self._notify(progress, "  📄 AGENTS.md")
        
        # Create principal.md
        principal_content = f"""# Principal — {project.name.display}

> **Project:** {project.name.display}
> **Version:** {project.version}
> **Author:** {project.author}
> **Email:** {project.email}
> **Created:** {project.created_at.strftime("%Y-%m-%d")}

## Project Purpose

{project.name.display} is a greenfield project initialized with {project.stack_name} stack and {project.project_type.display_name} pattern.

## Project Structure

- Stack: {project.stack_name}
- Pattern: {project.project_type.pattern.value}
- Standard directories: {len(STANDARD_ROOT_DIRECTORIES)} directories
- Module directories: {len(MODULE_DIRECTORIES)} directories

## Technology Stack

- Language: {project.stack_name}
- Package Manager: UV
- MCP: FastMCP (stdio)
- Database: SQLite (WAL)

## Development Standards

- Architecture: Aegis-Architecture-v1.0
- Project Structure: Aegis-ProjectStructure-v1.0
- API: Aegis-API-v1.0
- Documentation: Aegis-Documentation-v1.0

## AI Context

AI context files are located in `.agents/contexts/`:
- working.md - Working context for AI agents
- states/current.yaml - State management

## Documentation

Project documentation is located in `docs/`:
- architecture/ - Architecture documentation
- features/ - Feature documentation
- guides/ - User guides

## Next Steps

1. Implement business logic in `src/core/`
2. Write unit tests in `tests/`
3. Add CI/CD configuration
4. Deploy to production
"""
        (target / "principal.md").write_text(principal_content, encoding="utf-8")
        self._notify(progress, "  📄 principal.md")

    def _render_and_write(
        self,
        target: Path,
        template: Template,
        progress: ProgressCallback,
    ) -> None:
        output_path = target / template.target_path

        if template.skip_if_exists and output_path.exists():
            self._notify(progress, f"  ⏭️  {template.target_path} (exists, skipped)")
            return

        content = self._engine.render_template(template)
        content = self._with_standard_header(template=template, target_path=output_path, content=content)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        if template.executable:
            self._make_executable(output_path)

        self._notify(progress, f"  📄 {template.target_path}")

    def _with_standard_header(self, *, template: Template, target_path: Path, content: str) -> str:
        header_format = template.variables.get("header_format") if template.variables else None
        if not isinstance(header_format, str) or not header_format.strip():
            return content

        if target_path.name == "Package.swift":
            return content

        if not self._is_code_file(target_path):
            return content

        if self._has_project_header(content):
            return content

        package_path = self._package_path_for_file(template.target_path)
        description = self._description_for_file(template.target_path)

        try:
            header = self._engine.render_string(
                header_format,
                variables={
                    "project_name": template.variables.get("project_name", ""),
                    "package_path": package_path,
                    "author": template.variables.get("author", ""),
                    "description": description,
                },
            )
        except Exception:
            return content

        if not header.endswith("\n"):
            header += "\n"

        if target_path.suffix.lower() == ".php":
            stripped = content.lstrip("\n")
            if stripped.startswith("<?php"):
                first_newline = stripped.find("\n")
                if first_newline == -1:
                    return stripped + "\n\n" + header + "\n"
                prefix = stripped[: first_newline + 1]
                rest = stripped[first_newline + 1:]
                return prefix + "\n" + header + "\n" + rest.lstrip("\n")

        return header + "\n" + content.lstrip("\n")

    @staticmethod
    def _is_code_file(path: Path) -> bool:
        suffix = path.suffix.lower()
        return suffix in {
            ".py", ".js", ".ts", ".php", ".cs", ".swift", ".rs",
            ".cpp", ".cc", ".cxx", ".h", ".hpp", ".kt", ".java",
            ".go", ".dart", ".css", ".scss",
        }

    @staticmethod
    def _has_project_header(content: str) -> bool:
        head = content.lstrip()[:800]
        if "@project" not in head:
            return False
        return head.startswith('"""') or head.startswith("/**") or head.startswith("/*") or head.startswith("//")

    @staticmethod
    def _package_path_for_file(template_target_path: str) -> str:
        rel = template_target_path.replace("\\", "/").strip("/")
        if "/" not in rel:
            return ""
        return rel.rsplit("/", 1)[0]

    @staticmethod
    def _description_for_file(template_target_path: str) -> str:
        rel = template_target_path.replace("\\", "/").strip("/")
        name = rel.rsplit("/", 1)[-1]
        stem = name.split(".", 1)[0]
        lowered = stem.lower()
        if lowered in {"main", "mainentry", "program"}:
            return "Main entry point."
        if lowered in {"logger", "logwriter"}:
            return "Structured logging utility."
        return f"{stem} module."

    @staticmethod
    def _make_executable(path: Path) -> None:
        try:
            current = path.stat().st_mode
            path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass

    @staticmethod
    def _notify(callback: ProgressCallback, message: str) -> None:
        if callback:
            callback(message)
