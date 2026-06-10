"""
Module tools – 7 MCP tools for project scaffolding.

Tools:
  scaffold_list_stacks   — List available technology stacks
  scaffold_get_stack     — Get detailed info for one stack
  scaffold_validate_name — Validate and normalize a project name
  scaffold_list_licenses — List available license types
  scaffold_generate      — Generate a single content file (preview)
  scaffold_make          — Generate a class file per Decision Matrix (19 types)
  scaffold_create        — Full project scaffolding (dry_run=True default).

:project: CodeCortex
:package: Modules.Scaffolder.Api.Tools
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from src.core import (
    api_response,
    new_request_id,
    get_project_root,
    FileHeader,
    Version,
)
from src.modules.scaffolder.adapters.stack import Stack as StackAdapter
from src.modules.scaffolder.adapters.template import TemplateAdapter
from src.modules.scaffolder.core.config import get_settings
from src.modules.scaffolder.core.constants import LicenseIdentifier
from src.modules.scaffolder.core.dtos import Project, ProjectType
from src.modules.scaffolder.core.exceptions import (
    InvalidNameError,
    StackNotFoundError,
    ProjectAlreadyExistsError,
    ScaffoldError,
    TemplateRenderError,
)
from src.modules.scaffolder.core.generators import (
    ProjectCategory,
    ai_ignore,
    author_file,
    docker_compose,
    dockerfile,
    env_boilerplate,
    gitignore,
    logger_py,
    pyproject,
    readme,
    requirements,
    setup_bat,
    setup_ps1,
    setup_sh,
)
from src.modules.scaffolder.core.license import License
from src.modules.scaffolder.core.maker import make_class, list_types as maker_list_types, list_stacks as maker_list_stacks
from src.modules.scaffolder.core.name import Name
from src.modules.scaffolder.services.scaffold import Scaffold, Engine as ScaffoldEngine

logger = logging.getLogger(__name__)

_GENERATOR_MAP: dict[str, Callable[..., str]] = {
    "gitignore": gitignore,
    "env": env_boilerplate,
    "pyproject": pyproject,
    "readme": readme,
    "requirements": requirements,
    "dockerfile": dockerfile,
    "docker_compose": docker_compose,
    "setup_sh": setup_sh,
    "setup_bat": setup_bat,
    "setup_ps1": setup_ps1,
    "logger_py": logger_py,
    "author_file": author_file,
    "ai_ignore": ai_ignore,
}

_CATEGORY_MAP: dict[str, ProjectCategory] = {
    "standard": ProjectCategory.STANDARD,
    "data_science": ProjectCategory.DATA_SCIENCE,
    "web_api": ProjectCategory.WEB_API,
    "cli_tool": ProjectCategory.CLI_TOOL,
    "automation": ProjectCategory.AUTOMATION,
    "custom": ProjectCategory.CUSTOM,
}

def _to_stack_dict(stack) -> Dict[str, Any]:
    return {
        "name": stack.name,
        "display_name": stack.display_name,
        "version": stack.version,
        "file_conventions": {
            "directories": stack.file_conventions.directories.value if stack.file_conventions else "snake_case",
            "modules": stack.file_conventions.modules if stack.file_conventions else "snake_case.py",
            "classes": stack.file_conventions.classes if stack.file_conventions else "PascalCase",
        },
        "project_types": [
            {
                "id": pt.id,
                "display_name": pt.display_name,
                "description": pt.description,
                "pattern": pt.pattern.value if pt.pattern else "layered",
                "extra_directories": pt.extra_directories,
            }
            for pt in stack.project_types
        ],
        "templates_path": stack.templates_path,
    }

def _category_from_str(value: str) -> ProjectCategory:
    cleaned = value.strip().lower().replace(" ", "_")
    return _CATEGORY_MAP.get(cleaned, ProjectCategory.STANDARD)

def _build_scaffold_services() -> tuple[StackAdapter, TemplateAdapter, ScaffoldEngine, FileHeader]:
    project_root = get_project_root()
    templates_root = project_root / "datasets" / "templates"
    stack_repo = StackAdapter(templates_root)
    template_repo = TemplateAdapter(templates_root)
    engine = ScaffoldEngine(templates_root)
    file_header = FileHeader()
    return stack_repo, template_repo, engine, file_header

def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """
    Register 7 scaffold MCP tools.

    Each tool is prefixed with ``scaffold_`` for discoverability.
    """

    # ══════════════════════════════════════════════════════════
    # TOOL 1: scaffold_list_stacks
    # ══════════════════════════════════════════════════════════
    @mcp.tool()
    async def scaffold_list_stacks() -> Dict[str, Any]:
        """
        List all available technology stacks for project scaffolding.

        Returns an array of stacks, each with display name, version,
        file conventions, and available project types.

        Returns:
            Dict with ``stacks`` array.
        """
        req_id = new_request_id()
        try:
            stack_repo, *_ = _build_scaffold_services()
            stacks = [_to_stack_dict(s) for s in stack_repo.list_stacks()]
            return api_response(success=True, insight="scaffold_list_stacks", status_code=200,
                message=f"Found {len(stacks)} stacks", data={"stacks": stacks},
                request_id=req_id,
            )
        except Exception as exc:
            logger.error("scaffold_list_stacks failed: %s", exc, exc_info=True)
            return api_response(
                success=False, status_code=500,
                message=str(exc), data=None, request_id=req_id,
                error_code="SCAFFOLD_LIST_ERROR",
            )

    # ══════════════════════════════════════════════════════════
    # TOOL 2: scaffold_get_stack
    # ══════════════════════════════════════════════════════════
    @mcp.tool()
    async def scaffold_get_stack(
        stack_name: str,
    ) -> Dict[str, Any]:
        """
        Get detailed information for a specific technology stack.

        Args:
            stack_name: Stack identifier (e.g. ``"python"``, ``"typescript"``, ``"go"``).

        Returns:
            Full stack details including project types and file conventions.
        """
        req_id = new_request_id()
        try:
            stack_repo, *_ = _build_scaffold_services()
            stack = stack_repo.get_stack(stack_name.strip().lower())
            if stack is None:
                available = [s.name for s in stack_repo.list_stacks()]
                return api_response(
                    success=False, status_code=404,
                    message=f"Stack '{stack_name}' not found. Available: {', '.join(available) or 'none'}",
                    data=None, request_id=req_id,
                    error_code="STACK_NOT_FOUND",
                )
            return api_response(success=True, insight="scaffold_get_stack", status_code=200,
                message=f"Stack '{stack.display_name}' found",
                data={"stack": _to_stack_dict(stack)},
                request_id=req_id,
            )
        except Exception as exc:
            logger.error("scaffold_get_stack failed: %s", exc, exc_info=True)
            return api_response(
                success=False, status_code=500,
                message=str(exc), data=None, request_id=req_id,
                error_code="SCAFFOLD_GET_STACK_ERROR",
            )

    # ══════════════════════════════════════════════════════════
    # TOOL 3: scaffold_validate_name
    # ══════════════════════════════════════════════════════════
    @mcp.tool()
    async def scaffold_validate_name(
        name: str,
    ) -> Dict[str, Any]:
        """
        Validate and normalize a project name.

        Returns the derived naming conventions used in scaffolding:
          - ``display`` : Title Case human-readable name
          - ``slug``    : URL-safe kebab-case (for directories)
          - ``snake``   : Python-safe snake_case (for packages)
          - ``pascal``  : PascalCase (for class prefixes)

        Rules:
          - Must be at least 2 characters
          - Must contain alphanumeric characters
          - snake_case derivation must be a valid Python identifier

        Args:
            name: Raw project name to validate.

        Returns:
            Normalized name forms, or error with reason.
        """
        req_id = new_request_id()
        try:
            validated = Name.create(name)
            return api_response(success=True, insight="scaffold_validate_name", status_code=200,
                message=f"Name '{validated.display}' is valid",
                data={
                    "display": validated.display,
                    "slug": validated.slug,
                    "snake": validated.snake,
                    "pascal": validated.pascal,
                },
                request_id=req_id,
            )
        except InvalidNameError as exc:
            return api_response(
                success=False, status_code=400,
                message=str(exc), data=None,
                request_id=req_id,
                error_code="INVALID_NAME",
            )
        except Exception as exc:
            logger.error("scaffold_validate_name failed: %s", exc, exc_info=True)
            return api_response(
                success=False, status_code=500,
                message=str(exc), data=None, request_id=req_id,
                error_code="VALIDATE_NAME_ERROR",
            )

    # ══════════════════════════════════════════════════════════
    # TOOL 4: scaffold_list_licenses
    # ══════════════════════════════════════════════════════════
    @mcp.tool()
    async def scaffold_list_licenses() -> Dict[str, Any]:
        """
        List all available license types for generated projects.

        Supported licenses: MIT, Apache-2.0, GPL-3.0, BSD-3-Clause,
        Commercial-Company, Commercial-Personal, Private-Company,
        Private-Personal, and None (no license file).

        Returns:
            Dict with ``licenses`` array of ``{id, name}``.
        """
        req_id = new_request_id()
        try:
            licenses = [
                {"id": member.value, "name": member.name.replace("_", " ").title()}
                for member in LicenseIdentifier
            ]
            return api_response(success=True, insight="scaffold_list_licenses", status_code=200,
                message=f"Found {len(licenses)} license types",
                data={"licenses": licenses},
                request_id=req_id,
            )
        except Exception as exc:
            logger.error("scaffold_list_licenses failed: %s", exc, exc_info=True)
            return api_response(
                success=False, status_code=500,
                message=str(exc), data=None, request_id=req_id,
                error_code="LIST_LICENSES_ERROR",
            )

    # ══════════════════════════════════════════════════════════
    # TOOL 5: scaffold_generate
    # ══════════════════════════════════════════════════════════
    @mcp.tool()
    async def scaffold_generate(
        file_type: str,
        project_category: Optional[str] = "standard",
        project_name: Optional[str] = "My Project",
        author: Optional[str] = "Author",
        email: Optional[str] = "author@example.com",
        license_name: Optional[str] = "MIT",
    ) -> Dict[str, Any]:
        """
        Generate a single scaffold content file (preview without writing to disk).

        Supported file types:
          - ``gitignore``      → .gitignore content
          - ``env``            → .env.example template content
          - ``pyproject``      → pyproject.toml content
          - ``readme``         → README.md content
          - ``requirements``   → requirements.txt content
          - ``dockerfile``     → Dockerfile content
          - ``docker_compose`` → docker-compose.yml content
          - ``setup_sh``       → bin/setup.sh content
          - ``setup_bat``      → bin/setup.bat content
          - ``setup_ps1``      → bin/setup.ps1 content
          - ``logger_py``      → src/core/logger.py content
          - ``author_file``    → .author metadata content
          - ``ai_ignore``      → .aiignore content

        Args:
            file_type: Type of content to generate (see list above).
            project_category: Project category for type-aware generators.
              One of: ``standard``, ``data_science``, ``web_api``, ``cli_tool``, ``automation``.
            project_name: Project display name (used in README).
            author: Author name.
            email: Author email.
            license_name: License string (used in README).

        Returns:
            Dict with ``filename`` and ``content`` fields.
        """
        req_id = new_request_id()
        try:
            generator = _GENERATOR_MAP.get(file_type.strip().lower())
            if generator is None:
                return api_response(
                    success=False, status_code=400,
                    message=f"Unknown file_type '{file_type}'. Supported: {', '.join(_GENERATOR_MAP)}",
                    data=None, request_id=req_id,
                    error_code="UNKNOWN_FILE_TYPE",
                )

            category = _category_from_str(project_category or "standard")

            if file_type == "gitignore":
                content = generator(category)
            elif file_type == "env":
                content = generator(category)
            elif file_type == "pyproject":
                content = generator(author, email, project_name, category, project_name.lower().replace(" ", "_"))
            elif file_type == "readme":
                content = generator(project_name, author, email, category, license_name or "None")
            elif file_type == "requirements":
                content = generator(category)
            elif file_type == "dockerfile":
                content = generator(category)
            elif file_type == "docker_compose":
                content = generator(category)
            elif file_type in ("setup_sh", "setup_bat", "setup_ps1"):
                content = generator(project_name, author)
            elif file_type == "logger_py":
                content = generator(author)
            elif file_type == "author_file":
                content = generator(author, email)
            elif file_type == "ai_ignore":
                content = generator()
            else:
                content = generator(category)

            filename_map = {
                "gitignore": ".gitignore",
                "env": ".env.example",
                "pyproject": "pyproject.toml",
                "readme": "README.md",
                "requirements": "requirements.txt",
                "dockerfile": "Dockerfile",
                "docker_compose": "docker-compose.yml",
                "setup_sh": "bin/setup.sh",
                "setup_bat": "bin/setup.bat",
                "setup_ps1": "bin/setup.ps1",
                "logger_py": "src/core/logger.py",
                "author_file": ".author",
                "ai_ignore": ".aiignore",
            }

            return api_response(success=True, insight="scaffold_generate", status_code=200,
                message=f"Generated {file_type}",
                data={
                    "filename": filename_map.get(file_type, file_type),
                    "content": content,
                    "content_length": len(content),
                },
                request_id=req_id,
            )
        except Exception as exc:
            logger.error("scaffold_generate failed: %s", exc, exc_info=True)
            return api_response(
                success=False, status_code=500,
                message=str(exc), data=None, request_id=req_id,
                error_code="GENERATE_ERROR",
            )

    # ══════════════════════════════════════════════════════════
    # TOOL 6: scaffold_make
    # ══════════════════════════════════════════════════════════
    @mcp.tool()
    async def scaffold_make(
        type: str,
        name: str,
        stack: str = "python",
        module: Optional[str] = None,
        project_name: Optional[str] = "Project",
        author: Optional[str] = "Author",
        target_path: Optional[str] = None,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a class file for any of the 34 Decision Matrix types.

        Supports class generation for:
          - **Interfaces / Contracts** — ``interface``
          - **Abstract base classes** — ``abstract``
          - **Domain models / entities** — ``model``
          - **Repositories** — ``repository``
          - **Controllers (HTTP)** — ``controller``
          - **Services** — ``service``
          - **Value Objects** — ``value_object``
          - **DTOs** — ``dto``
          - **Events / Listeners** — ``event``, ``listener``
          - **Jobs / Commands** — ``job``, ``command``
          - **Middleware** — ``middleware``
          - **Factories / Seeders** — ``factory``, ``seeder``
          - **Migrations** — ``migration``
          - **Enums** — ``enum``
          - **Traits** — ``trait``
          - **Helpers** — ``helper``
          - **Validators / Mappers / Filters** — ``validator``, ``mapper``, ``filter``
          - **Presenters / ViewModels** — ``presenter``, ``view_model``
          - **Exceptions / Providers / Observers / Strategies** — ``exception``, ``provider``, ``observer``, ``
          - **Documentation (per ~/.aicoders/docs/standards/documentation.md)** — ``doc_draft``, ``doc_planning``, ``doc_concept``, ``doc_feature``, ``doc_subfeature``, ``doc_ai_impact``

        Naming rules (per coding-standard.md §3.1):
          - Class name = domain concept only (no role suffix redundancy)
          - File name follows the stack convention: ``snake_case.py`` for Python,
            ``PascalCase.ts`` for TypeScript, ``PascalCase.php`` for PHP, etc.
          - Folder location is determined by the type and converted per stack

        Classes are placed in the correct module directory for the type
        (e.g. ``controllers/http/`` for ``controller`` in Python) and
        converted to the stack's naming convention.

        Args:
            type: Class type identifier (see list above).
            name: Domain concept name (e.g. ``"User"``, ``"Order"``, ``"Payment"``).
            stack: Technology stack. Supports 14+ stacks including
              ``python``, ``typescript``, ``javascript``, ``php``, ``go``,
              ``java``, ``kotlin``, ``csharp``, ``swift``, ``rust``, ``cpp``,
              ``dart``, ``flutter``.
            module: Optional module context for DDD/split projects.
              E.g. ``"payment"`` generates ``payment/controllers/http/user.py``.
            project_name: Project name for file headers.
            author: Author name for file headers.
            target_path: Absolute path to write the file.
              If omitted, content is returned without writing.
            overwrite: Overwrite existing files (default ``False``).

        Returns:
            Dict with ``class_name``, ``relative_path``, ``content``, and
            ``written`` flag. If no ``target_path`` is given, ``written`` is
            ``False`` for preview mode.
        """
        req_id = new_request_id()
        try:
            result = make_class(
                type_id=type,
                name=name,
                stack=stack,
                module=module,
                project_name=project_name or "Project",
                author=author or "Author",
                target_path=target_path,
                overwrite=overwrite,
            )
            if not result["success"]:
                return api_response(
                    success=False, status_code=400,
                    message=result["error"], data=None,
                    request_id=req_id, error_code="MAKE_VALIDATION_ERROR",
                )
            return api_response(success=True, insight="scaffold_make", status_code=200,
                message=f"Generated {result['type_display']} '{result['class_name']}' ({result['stack']})",
                data={
                    "type": result["type"],
                    "type_display": result["type_display"],
                    "stack": result["stack"],
                    "class_name": result["class_name"],
                    "file_name": result["file_name"],
                    "relative_path": result["relative_path"],
                    "absolute_path": result.get("absolute_path"),
                    "content": result["content"],
                    "content_length": result["content_length"],
                    "written": result["written"],
                },
                request_id=req_id,
            )
        except Exception as exc:
            logger.error("scaffold_make failed: %s", exc, exc_info=True)
            return api_response(
                success=False, status_code=500,
                message=str(exc), data=None, request_id=req_id,
                error_code="MAKE_SYSTEM_ERROR",
            )

    # ══════════════════════════════════════════════════════════
    # TOOL 7: scaffold_create
    # ══════════════════════════════════════════════════════════
    @mcp.tool()
    async def scaffold_create(
        name: str,
        stack: str = "python",
        project_type: str = "standard",
        target_path: Optional[str] = None,
        author: Optional[str] = None,
        email: Optional[str] = None,
        version: Optional[str] = None,
        license: Optional[str] = "MIT",
        include_ai: bool = False,
        include_trainer: bool = False,
        project_code: Optional[str] = None,
        overwrite: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a full project scaffold — directories, templates, license, and metadata.

        **Dry-run mode** (default): Validates inputs and shows what would be created
        without writing any files. Set ``dry_run=false`` to actually scaffold.

        Pipeline:
          1. Validate project name
          2. Resolve technology stack + project type
          3. Build template context (20+ Jinja2 variables)
          4. Create 33+ standard directories
          5. Render shared templates (``_shared/*.j2``)
          6. Render stack templates (``{stack}/**/*.j2``, ``{stack}/types/{type}/**/*.j2``)
          7. Write ``.version``, ``LICENSE``, ``__init__.py`` files
          8. Prepend standard ``@project`` headers on code files

        Args:
            name: Project name (will be normalized to display/slug/snake/pascal forms).
            stack: Technology stack identifier (e.g. ``"python"``, ``"typescript"``, ``"go"``).
            project_type: Project type identifier within the stack (e.g. ``"standard"``, ``"web_api"``).
            target_path: Absolute output path. Defaults to ``outputs/projects/<slug>/``.
            author: Author name (defaults to config or git config).
            email: Author email.
            version: SemVer string (defaults to ``0.1.0``).
            license: License identifier (default: ``"MIT"``). Use ``"None"`` to skip.
            include_ai: Include optional ``src/ai/`` module.
            include_trainer: Include optional ``src/trainer/`` module.
            project_code: Optional project code (e.g. ``"MP001"``).
            overwrite: Allow overwriting existing project directory.
            dry_run: If True (default), validate inputs only — no files written.

        Returns:
            Project scaffold result with path, versions, and summary.
        """
        req_id = new_request_id()

        try:
            validated_name = Name.create(name)
        except InvalidNameError as exc:
            return api_response(
                success=False, status_code=400,
                message=str(exc), data={"name": exc.name, "reason": exc.reason},
                request_id=req_id, error_code="INVALID_NAME",
            )

        try:
            stack_repo, template_repo, engine, file_header = _build_scaffold_services()
        except Exception as exc:
            return api_response(
                success=False, status_code=500,
                message=f"Failed to initialize scaffold services: {exc}",
                data=None, request_id=req_id, error_code="SERVICE_INIT_ERROR",
            )

        resolved_stack = stack_repo.get_stack(stack.strip().lower())
        if resolved_stack is None:
            available = [s.name for s in stack_repo.list_stacks()] or ["(no stacks registered)"]
            return api_response(
                success=False, status_code=404,
                message=f"Stack '{stack}' not found. Available: {', '.join(available)}",
                data=None, request_id=req_id, error_code="STACK_NOT_FOUND",
            )

        resolved_pt = resolved_stack.get_project_type(project_type.strip().lower())
        if resolved_pt is None:
            available_pts = resolved_stack.project_type_ids or ["(none - using standard defaults)"]
            return api_response(
                success=False, status_code=404,
                message=f"Project type '{project_type}' not found in stack '{stack}'. "
                        f"Available: {', '.join(available_pts)}",
                data=None, request_id=req_id, error_code="PROJECT_TYPE_NOT_FOUND",
            )

        resolved_license = License.from_string(license or "MIT")

        resolved_version: Version
        if version:
            try:
                resolved_version = Version.from_string(version)
            except Exception:
                return api_response(
                    success=False, status_code=400,
                    message=f"Invalid version '{version}': must follow SemVer MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]",
                    data=None, request_id=req_id, error_code="INVALID_VERSION",
                )
        else:
            resolved_version = Version.default()

        project_root = get_project_root()
        final_author = author or "Author"
        final_email = email or "author@example.com"
        slug = validated_name.slug

        if target_path:
            final_target = Path(target_path).resolve()
        else:
            final_target = (project_root / "outputs" / "projects" / slug).resolve()

        if dry_run:
            file_count = (
                len(template_repo.get_shared_templates())
                + len(template_repo.get_stack_templates(resolved_stack.name, resolved_pt.id))
            )
            return api_response(success=True, insight="scaffold_create", status_code=200,
                message=f"Dry-run: project '{validated_name.display}' ready to scaffold",
                data={
                    "dry_run": True,
                    "name": {
                        "display": validated_name.display,
                        "slug": validated_name.slug,
                        "snake": validated_name.snake,
                        "pascal": validated_name.pascal,
                    },
                    "stack": resolved_stack.name,
                    "stack_display": resolved_stack.display_name,
                    "project_type": resolved_pt.id,
                    "project_type_display": resolved_pt.display_name,
                    "target_path": str(final_target),
                    "author": final_author,
                    "email": final_email,
                    "version": str(resolved_version),
                    "license": resolved_license.identifier.value,
                    "include_ai": include_ai,
                    "include_trainer": include_trainer,
                    "template_count": file_count,
                    "directory_count": 33 + len(resolved_pt.extra_directories),
                    "template_context_keys": list(Project(
                        name=validated_name,
                        target_path=final_target,
                        stack_name=resolved_stack.name,
                        project_type=resolved_pt,
                        author=final_author,
                        email=final_email,
                        version=resolved_version,
                        license=resolved_license,
                        include_ai=include_ai,
                        include_trainer=include_trainer,
                        project_code=project_code,
                    ).template_context().keys()),
                },
                request_id=req_id,
            )

        project = Project(
            name=validated_name,
            target_path=final_target,
            stack_name=resolved_stack.name,
            project_type=resolved_pt,
            author=final_author,
            email=final_email,
            version=resolved_version,
            license=resolved_license,
            include_ai=include_ai,
            include_trainer=include_trainer,
            project_code=project_code,
        )

        scaffold_service = Scaffold(stack_repo, template_repo, engine, file_header)

        try:
            progress_messages: list[str] = []

            def _progress(msg: str) -> None:
                progress_messages.append(msg)

            await asyncio.to_thread(
                scaffold_service.scaffold,
                project,
                progress=_progress,
                overwrite=overwrite,
            )

            return api_response(success=True, insight="scaffold_create", status_code=200,
                message=f"Project '{validated_name.display}' scaffolded successfully",
                data={
                    "dry_run": False,
                    "target_path": str(final_target),
                    "name": validated_name.display,
                    "slug": validated_name.slug,
                    "stack": resolved_stack.name,
                    "project_type": resolved_pt.id,
                    "version": str(resolved_version),
                    "license": resolved_license.identifier.value,
                    "progress": progress_messages,
                },
                request_id=req_id,
            )

        except ProjectAlreadyExistsError:
            return api_response(
                success=False, status_code=409,
                message=f"Project directory already exists: {final_target}. "
                        "Set overwrite=true to allow overwriting.",
                data={"target_path": str(final_target)},
                request_id=req_id, error_code="PROJECT_EXISTS",
            )
        except ScaffoldError as exc:
            return api_response(
                success=False, status_code=500,
                message=str(exc), data=None,
                request_id=req_id, error_code="SCAFFOLD_ERROR",
            )
        except Exception as exc:
            logger.error("scaffold_create failed: %s", exc, exc_info=True)
            return api_response(
                success=False, status_code=500,
                message=f"Unexpected scaffold error: {exc}", data=None,
                request_id=req_id, error_code="SCAFFOLD_UNEXPECTED",
            )
