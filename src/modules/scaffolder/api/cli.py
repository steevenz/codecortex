from __future__ import annotations
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

DOMAIN = "scaffolder"
ALIASES = ["sc"]


def output(data: Any, pretty: bool = True) -> None:
    """Print JSON to stdout as UTF-8 bytes (avoids Windows cp1252 issues)."""
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    text = json.dumps(data, **kwargs, default=str)
    buf = sys.stdout.buffer
    buf.write(text.encode("utf-8", errors="replace"))
    buf.write(b"\n")
    buf.flush()


def ok(message: str, data: Any = None) -> Dict[str, Any]:
    return {"success": True, "status_code": 200, "message": message, "data": data}


def err(message: str, code: str = "CLI_ERROR", status: int = 400) -> Dict[str, Any]:
    return {"success": False, "status_code": status, "message": message, "data": None, "error_code": code}


def run_async(coro):
    """Safely run a coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


def cmd_sc_list_stacks(args_ns: argparse.Namespace) -> Dict:
    from src.modules.scaffolder.adapters.stack import Stack as StackAdapter
    from src.core import get_project_root
    stack_repo = StackAdapter(get_project_root() / "datasets" / "templates")
    stacks = stack_repo.list_stacks()
    data = [{
        "name": s.name, "display_name": s.display_name,
        "version": s.version,
        "project_types": [pt.id for pt in s.project_types] if s.project_types else [],
    } for s in stacks]
    return ok(f"Found {len(data)} stacks", {"stacks": data})


def cmd_sc_get_stack(args_ns: argparse.Namespace) -> Dict:
    from src.modules.scaffolder.adapters.stack import Stack as StackAdapter
    from src.core import get_project_root
    stack_repo = StackAdapter(get_project_root() / "datasets" / "templates")
    stack = stack_repo.get_stack(args_ns.name)
    if not stack:
        available = [s.name for s in stack_repo.list_stacks()] or ["(none)"]
        return err(f"Stack '{args_ns.name}' not found. Available: {', '.join(available)}", "STACK_NOT_FOUND", 404)
    return ok(f"Stack '{stack.display_name}' found", {"stack": {
        "name": stack.name, "display_name": stack.display_name, "version": stack.version,
        "file_conventions": {
            "directories": stack.file_conventions.directories.value if stack.file_conventions else "snake_case",
            "modules": stack.file_conventions.modules if stack.file_conventions else "snake_case.py",
            "classes": stack.file_conventions.classes if stack.file_conventions else "PascalCase",
        },
        "project_types": [
            {"id": pt.id, "display_name": pt.display_name, "description": pt.description}
            for pt in (stack.project_types or [])
        ],
    }})


def cmd_sc_validate_name(args_ns: argparse.Namespace) -> Dict:
    from src.modules.scaffolder.core.name import Name
    from src.modules.scaffolder.core.exceptions import InvalidNameError
    try:
        validated = Name.create(args_ns.name)
        return ok(f"Name '{validated.display}' is valid", {
            "display": validated.display, "slug": validated.slug,
            "snake": validated.snake, "pascal": validated.pascal,
        })
    except InvalidNameError as e:
        return err(str(e), "INVALID_NAME", 400)


def cmd_sc_list_licenses(args_ns: argparse.Namespace) -> Dict:
    from src.modules.scaffolder.core.constants import LicenseIdentifier
    licenses = [
        {"id": m.value, "name": m.name.replace("_", " ").title()}
        for m in LicenseIdentifier
    ]
    return ok(f"Found {len(licenses)} license types", {"licenses": licenses})


def cmd_sc_generate(args_ns: argparse.Namespace) -> Dict:
    from src.modules.scaffolder.core.generators import (
        ProjectCategory, gitignore, env_boilerplate, pyproject, readme,
        requirements, dockerfile, docker_compose, setup_sh, setup_bat,
        setup_ps1, logger_py, author_file, ai_ignore,
    )
    GENERATOR_MAP = {
        "gitignore": gitignore, "env": env_boilerplate, "pyproject": pyproject,
        "readme": readme, "requirements": requirements, "dockerfile": dockerfile,
        "docker_compose": docker_compose, "setup_sh": setup_sh, "setup_bat": setup_bat,
        "setup_ps1": setup_ps1, "logger_py": logger_py, "author_file": author_file,
        "ai_ignore": ai_ignore,
    }
    FILENAME_MAP = {
        "gitignore": ".gitignore", "env": ".env.example", "pyproject": "pyproject.toml",
        "readme": "README.md", "requirements": "requirements.txt", "dockerfile": "Dockerfile",
        "docker_compose": "docker-compose.yml", "setup_sh": "bin/setup.sh", "setup_bat": "bin/setup.bat",
        "setup_ps1": "bin/setup.ps1", "logger_py": "src/core/logger.py",
        "author_file": ".author", "ai_ignore": ".aiignore",
    }
    try:
        ft = args_ns.file_type
        generator = GENERATOR_MAP.get(ft)
        if not generator:
            return err(f"Unknown file_type '{ft}'. Supported: {', '.join(GENERATOR_MAP)}", "UNKNOWN_FILE_TYPE")
        category_map = {
            "standard": ProjectCategory.STANDARD, "data_science": ProjectCategory.DATA_SCIENCE,
            "web_api": ProjectCategory.WEB_API, "cli_tool": ProjectCategory.CLI_TOOL,
            "automation": ProjectCategory.AUTOMATION, "custom": ProjectCategory.CUSTOM,
        }
        category = category_map.get(getattr(args_ns, "category", "standard"), ProjectCategory.STANDARD)
        pn = args_ns.project_name or "My Project"
        au = args_ns.author or "Author"
        em = args_ns.email or "author@example.com"

        if ft in ("gitignore", "env", "requirements", "dockerfile", "docker_compose"):
            content = generator(category)
        elif ft == "pyproject":
            content = generator(au, em, pn, category, pn.lower().replace(" ", "_"))
        elif ft == "readme":
            content = generator(pn, au, em, category, args_ns.license or "MIT")
        elif ft in ("setup_sh", "setup_bat", "setup_ps1"):
            content = generator(pn, au)
        elif ft == "logger_py":
            content = generator(au)
        elif ft == "author_file":
            content = generator(au, em)
        elif ft == "ai_ignore":
            content = generator()
        else:
            content = generator(category)
        return ok(f"Generated {ft}", {
            "filename": FILENAME_MAP.get(ft, ft), "content": content, "content_length": len(content),
        })
    except Exception as e:
        return err(f"Generate failed: {e}", "GENERATE_ERROR", 500)


def cmd_sc_make(args_ns: argparse.Namespace) -> Dict:
    from src.modules.scaffolder.core.maker import make_class
    try:
        result = make_class(
            type_id=args_ns.type_id,
            name=args_ns.name,
            stack=getattr(args_ns, "stack", "python"),
            module=getattr(args_ns, "module", None),
            project_name=getattr(args_ns, "project", "Project"),
            author=getattr(args_ns, "author", "Author"),
            target_path=getattr(args_ns, "target", None),
            overwrite=getattr(args_ns, "overwrite", False),
        )
        if not result["success"]:
            return err(result["error"], "MAKE_VALIDATION_ERROR", 400)
        return ok(f"Generated {result['type_display']} '{result['class_name']}'", {
            "type": result["type"], "type_display": result["type_display"],
            "stack": result["stack"], "class_name": result["class_name"],
            "file_name": result["file_name"], "relative_path": result["relative_path"],
            "absolute_path": result.get("absolute_path"), "content": result["content"],
            "content_length": result["content_length"], "written": result["written"],
        })
    except Exception as e:
        return err(f"Make failed: {e}", "MAKE_SYSTEM_ERROR", 500)


def cmd_sc_create(args_ns: argparse.Namespace) -> Dict:
    import asyncio
    from pathlib import Path
    from src.core import get_project_root, Version
    from src.modules.scaffolder.api.tools import _build_scaffold_services
    from src.modules.scaffolder.core.name import Name
    from src.modules.scaffolder.core.license import License
    from src.modules.scaffolder.core.exceptions import InvalidNameError, ProjectAlreadyExistsError, ScaffoldError
    from src.modules.scaffolder.core.dtos import Project as ProjectDTO
    from src.modules.scaffolder.services.scaffold import Scaffold

    try:
        validated_name = Name.create(args_ns.name)
    except InvalidNameError as e:
        return err(str(e), "INVALID_NAME", 400)

    stack_repo, template_repo, engine, file_header = _build_scaffold_services()
    resolved_stack = stack_repo.get_stack(getattr(args_ns, "stack", "python"))
    if not resolved_stack:
        return err(f"Stack not found. Available: {', '.join(s.name for s in stack_repo.list_stacks())}", "STACK_NOT_FOUND", 404)

    resolved_pt = resolved_stack.get_project_type(getattr(args_ns, "project_type", "standard"))
    if not resolved_pt:
        return err(f"Project type not found", "PROJECT_TYPE_NOT_FOUND", 404)

    final_target = (
        Path(args_ns.target).resolve()
        if getattr(args_ns, "target", None)
        else (get_project_root() / "outputs" / "projects" / validated_name.slug).resolve()
    )
    author = args_ns.author or "Author"
    email = args_ns.email or "author@example.com"
    version_str = args_ns.version or "0.1.0"
    license_str = args_ns.license or "MIT"
    overwrite = getattr(args_ns, "overwrite", False)
    dry_run = getattr(args_ns, "dry_run", True)

    try:
        resolved_version = Version.parse(version_str)
    except Exception:
        return err(f"Invalid version '{version_str}'", "INVALID_VERSION", 400)

    resolved_license = License.from_string(license_str)

    if dry_run:
        file_count = (
            len(template_repo.get_shared_templates())
            + len(template_repo.get_stack_templates(resolved_stack.name, resolved_pt.id))
        )
        return ok(f"Dry-run: project '{validated_name.display}' ready", {
            "dry_run": True,
            "name": {"display": validated_name.display, "slug": validated_name.slug,
                     "snake": validated_name.snake, "pascal": validated_name.pascal},
            "stack": resolved_stack.name, "stack_display": resolved_stack.display_name,
            "project_type": resolved_pt.id, "project_type_display": resolved_pt.display_name,
            "target_path": str(final_target), "author": author, "email": email,
            "version": version_str, "license": resolved_license.identifier.value,
            "include_ai": getattr(args_ns, "include_ai", False),
            "include_trainer": getattr(args_ns, "include_trainer", False),
            "template_count": file_count,
            "directory_count": 33 + len(resolved_pt.extra_directories),
        })

    project = ProjectDTO(
        name=validated_name, target_path=final_target, stack_name=resolved_stack.name,
        project_type=resolved_pt, author=author, email=email,
        version=resolved_version, license=resolved_license,
        include_ai=getattr(args_ns, "include_ai", False),
        include_trainer=getattr(args_ns, "include_trainer", False),
        project_code=getattr(args_ns, "project_code", None),
    )

    scaffold_service = Scaffold(stack_repo, template_repo, engine, file_header)
    progress = []

    def _progress(msg: str) -> None:
        progress.append(msg)

    try:
        run_async(asyncio.to_thread(scaffold_service.scaffold, project, progress=_progress, overwrite=overwrite))
        return ok(f"Project '{validated_name.display}' scaffolded", {
            "dry_run": False, "target_path": str(final_target),
            "name": validated_name.display, "slug": validated_name.slug,
            "stack": resolved_stack.name, "project_type": resolved_pt.id,
            "version": version_str, "license": resolved_license.identifier.value,
            "progress": progress,
        })
    except ProjectAlreadyExistsError:
        return err(f"Project directory already exists: {final_target}. Set overwrite=true.", "PROJECT_EXISTS", 409)
    except ScaffoldError as e:
        return err(str(e), "SCAFFOLD_ERROR", 500)
    except Exception as e:
        return err(f"Unexpected scaffold error: {e}", "SCAFFOLD_UNEXPECTED", 500)


SC_COMMANDS = {
    "list-stacks": cmd_sc_list_stacks,
    "get-stack": cmd_sc_get_stack,
    "validate-name": cmd_sc_validate_name,
    "list-licenses": cmd_sc_list_licenses,
    "generate": cmd_sc_generate,
    "make": cmd_sc_make,
    "create": cmd_sc_create,
}


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("scaffolder", aliases=["sc"], help="Project scaffolding")
    sp = p.add_subparsers(dest="sc_action", required=True)

    sp.add_parser("list-stacks", help="List available technology stacks")
    sp.add_parser("get-stack", help="Get detailed info for one stack").add_argument("name", help="Stack name")
    sp.add_parser("validate-name", help="Validate a project name").add_argument("name", help="Name to validate")
    sp.add_parser("list-licenses", help="List available license types")

    gen = sp.add_parser("generate", help="Generate a content file (preview)")
    gen.add_argument("file_type", help="File type (gitignore, env, readme, dockerfile, ...)")
    gen.add_argument("--category", default="standard", help="Project category")
    gen.add_argument("--project-name", default="My Project", help="Project name")
    gen.add_argument("--author", default="Author", help="Author name")
    gen.add_argument("--email", default="author@example.com", help="Author email")
    gen.add_argument("--license", default="MIT", help="License name")

    mk = sp.add_parser("make", help="Generate a class file")
    mk.add_argument("type_id", help="Class type (e.g. entity, repository, service)")
    mk.add_argument("name", help="Class name")
    mk.add_argument("--stack", default="python", help="Technology stack")
    mk.add_argument("--module", help="Module name")
    mk.add_argument("--project", default="Project", help="Project name")
    mk.add_argument("--author", default="Author", help="Author name")
    mk.add_argument("--target", help="Target output path")
    mk.add_argument("--overwrite", action="store_true", help="Overwrite existing file")

    cr = sp.add_parser("create", help="Full project scaffolding")
    cr.add_argument("name", help="Project name")
    cr.add_argument("--stack", default="python", help="Technology stack")
    cr.add_argument("--project-type", default="standard", help="Project type")
    cr.add_argument("--target", help="Target output directory")
    cr.add_argument("--author", default="Author", help="Author name")
    cr.add_argument("--email", default="author@example.com", help="Author email")
    cr.add_argument("--version", default="0.1.0", help="Project version")
    cr.add_argument("--license", default="MIT", help="License")
    cr.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    cr.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Execute scaffolding")
    cr.add_argument("--overwrite", action="store_true", help="Overwrite existing project")
    cr.add_argument("--include-ai", action="store_true", help="Include AI configuration")
    cr.add_argument("--include-trainer", action="store_true", help="Include trainer files")
    cr.add_argument("--project-code", help="Project code prefix")
