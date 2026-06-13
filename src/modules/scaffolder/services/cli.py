"""
CLI — interactive and non-interactive entry point for the scaffolding service.

:project: CodeCortex
:package: Modules.Scaffolder.Services.Cli
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Scaffolder-v1.0
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..adapters.filesystem import Filesystem
from ..adapters.git import Git
from ..adapters.stack import Stack as StackRepo
from ..adapters.template import Template as TemplateRepo
from ..core.config import PyScaffold, get_settings
from ..core.exceptions import (
    PyScaffoldError,
    StackNotFoundError,
    UnsupportedFrameworkError,
    UnsupportedTargetLanguageError,
)
from ..core.dtos import Project, ProjectType
from ..core.license import License
from ..core.name import Name
from src.core import Version
from .scaffold import Engine, FileHeader, Scaffold

logger = logging.getLogger(__name__)

class CLI:
    """Interactive CLI interface for PyScaffold."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._stack_repo = StackRepo(self._settings.templates_path)
        self._template_repo = TemplateRepo(self._settings.templates_path)
        self._engine = Engine(self._settings.templates_path)
        self._header = FileHeader()
        self._scaffold = Scaffold(
            stack_repository=self._stack_repo,
            template_repository=self._template_repo,
            template_engine=self._engine,
            file_header=self._header,
        )

    def run(self, target: Optional[str] = None) -> None:
        try:
            self._show_welcome()
            project_info = self._collect_project_info(target=target)
            self._show_summary(project_info)

            if not self._confirm("Create this project?"):
                print("Project creation cancelled.")
                return

            project = self._build_project(project_info)
            self._scaffold.scaffold(
                project,
                progress=lambda msg: print(f"  {msg}"),
            )

            if self._confirm("Create IDE skills links under .agents?", default=True):
                dry_run = self._confirm("Dry-run only (no filesystem changes)?", default=False)
                result = ensure_agents_skills_links(
                    project_root=project.target_path,
                    dry_run=dry_run,
                )
                print(
                    f"Symlink results: created={result['created']} skipped={result['skipped']} failed={result['failed']}"
                )

            if self._settings.git.auto_init:
                Git.init_repository(project.target_path)

            self._show_success(project)

        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(0)
        except PyScaffoldError as exc:
            print(f"\n❌ Error: {exc}")
            sys.exit(1)
        except Exception as exc:
            print(f"\n❌ Unexpected error: {exc}")
            sys.exit(1)

    def _show_welcome(self) -> None:
        print("=" * 70)
        print("🚀 PyScaffold — Framework-Agnostic Boilerplate Generator")
        print("=" * 70)
        print()
        print("Generate professional projects in seconds. Multi-stack. Standard-compliant.")
        print()
        print("Created by: Steeven Andrian (https://github.com/steevenz)")
        print("=" * 70)
        print()

    def _collect_project_info(self, target: Optional[str] = None) -> Dict[str, Any]:
        print("📝 Project Information")
        print()

        stacks = self._stack_repo.list_stacks()
        stack = self._select_stack(stacks, target=target)
        project_type_def = self._select_project_type(stack)

        raw_name = input("Project Name [default: My Project]: ").strip() or "My Project"
        name = Name.create(raw_name)
        if name.display != raw_name:
            print(f"→ Normalised to: {name.display}")

        default_dir = name.snake
        project_dir = input(f"Project Directory [default: {default_dir}]: ").strip() or default_dir
        while not self._is_valid_directory(project_dir):
            print("❌ Invalid. Use lowercase letters, numbers, and underscores only.")
            project_dir = input("Project Directory: ").strip() or default_dir

        project_code = input("Project Code (optional alias): ").strip() or None

        default_target = str(self._settings.default_output_path / project_dir)
        target_path = input(f"Target Directory [default: {default_target}]: ").strip() or default_target

        git_user = Git.user()
        git_name = git_user.get("name")
        git_email = git_user.get("email")
        default_author = git_name or self._settings.author.name
        default_email = git_email or self._settings.author.email

        author = input(f"Author Name [default: {default_author}]: ").strip() or default_author
        email = input(f"Email [default: {default_email}]: ").strip() or default_email

        license_type = self._select_license()

        include_ai = False
        include_trainer = False
        if project_type_def.conditional_modules.get("ai"):
            include_ai = self._confirm("Include AI/ML Modules?", default=False)
        if project_type_def.conditional_modules.get("trainer"):
            include_trainer = self._confirm("Include Training Utilities?", default=False)

        return {
            "stack": stack,
            "project_type": project_type_def,
            "name": name,
            "project_dir": project_dir,
            "project_code": project_code,
            "target_path": Path(target_path),
            "author": author,
            "email": email,
            "license": license_type,
            "include_ai": include_ai,
            "include_trainer": include_trainer,
        }

    def _select_stack(self, stacks: list, target: Optional[str] = None):
        if not stacks:
            print("❌ No stacks found. Ensure datasets/templates/ has stack folders with manifest.yml")
            sys.exit(1)

        all_stacks = stacks
        from ..core.config import get_config_manager
        cm = get_config_manager()
        active_targets = cm.list_supported_active_targets() if hasattr(cm, 'list_supported_active_targets') else []
        if active_targets:
            filtered = [s for s in stacks if s.name in active_targets]
            if filtered:
                stacks = filtered

        if target:
            resolved = cm.validate_target_language(target)
            selected = next((s for s in all_stacks if s.name == resolved), None)
            if selected is None:
                raise StackNotFoundError(resolved)
            print(f"📦 Stack: {selected.display_name} ({selected.name})")
            return selected

        if len(stacks) == 1:
            print(f"📦 Stack: {stacks[0].display_name} (only available stack)")
            return stacks[0]

        print("\n📦 Available Stacks")
        print("-" * 50)
        for i, s in enumerate(stacks, 1):
            print(f"  {i}. {s.display_name} ({s.name})")
        print("-" * 50)

        while True:
            choice = input(f"Select stack (1-{len(stacks)}) [default: 1]: ").strip() or "1"
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(stacks):
                    return stacks[idx]
            except ValueError:
                pass
            print(f"Invalid. Select 1-{len(stacks)}.")

    def _select_project_type(self, stack):
        pts = stack.project_types
        if not pts:
            print(f"❌ No project types defined for stack '{stack.name}'.")
            sys.exit(1)

        print(f"\n📋 Project Types ({stack.display_name})")
        print("-" * 70)
        print(f"{'No':<4} {'Type':<20} {'Description'}")
        print("-" * 70)
        for i, pt in enumerate(pts, 1):
            print(f"{i:<4} {pt.id:<20} {pt.description}")
        print("-" * 70)

        while True:
            choice = input(f"Select type (1-{len(pts)}) [default: 1]: ").strip() or "1"
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(pts):
                    return pts[idx]
            except ValueError:
                pass
            print(f"Invalid. Select 1-{len(pts)}.")

    def _select_license(self) -> License:
        licenses = [
            ("1", "MIT License", "MIT"),
            ("2", "Apache 2.0 License", "Apache-2.0"),
            ("3", "GPL 3.0 License", "GPL-3.0"),
            ("4", "BSD 3-Clause License", "BSD-3-Clause"),
            ("5", "Company Commercial License", "Commercial-Company"),
            ("6", "Personal Commercial License", "Commercial-Personal"),
            ("7", "Company Private License", "Private-Company"),
            ("8", "Personal Private License", "Private-Personal"),
            ("9", "No License", "None"),
        ]

        print("\n📄 License Selection")
        for num, label, _ in licenses:
            print(f"  {num}. {label}")

        while True:
            choice = input("Select License (1-9) [default: 1]: ").strip() or "1"
            for num, _, identifier in licenses:
                if choice == num:
                    return License.from_string(identifier)
            print("Invalid. Select 1-9.")

    def _show_summary(self, info: Dict[str, Any]) -> None:
        code_text = f" ({info['project_code']})" if info["project_code"] else ""
        print()
        print("📋 Project Summary")
        print("=" * 50)
        print(f"  Project Name:   {info['name'].display}{code_text}")
        print(f"  Directory:      {info['project_dir']}")
        print(f"  Target:         {info['target_path']}")
        print(f"  Stack:          {info['stack'].display_name}")
        print(f"  Type:           {info['project_type'].display_name}")
        print(f"  Author:         {info['author']} ({info['email']})")
        print(f"  License:        {info['license']}")
        print(f"  AI Modules:     {'Yes' if info['include_ai'] else 'No'}")
        print(f"  Training Utils: {'Yes' if info['include_trainer'] else 'No'}")
        print("=" * 50)
        print()

    def _show_success(self, project: Project) -> None:
        is_windows = platform.system().lower() == "windows"
        setup_script = r".\scripts\setup\setup-dev-env.ps1" if is_windows else "./scripts/setup/setup-dev-env.sh"

        print()
        print("🎉 Success")
        print("=" * 60)
        print(f"✅ Project '{project.name.display}' created successfully!")
        print(f"📁 Location: {project.target_path}")
        print(f"📋 Version:  {project.version}")
        print()
        print("Next steps:")
        print(f"  1. cd {project.target_path}")
        print(f"  2. {setup_script}")
        print("     • Creates venv, installs dependencies, configures tools")
        print()
        print("🚀 Happy coding!")
        print("=" * 60)

    def _build_project(self, info: Dict[str, Any]) -> Project:
        return Project(
            name=info["name"],
            target_path=info["target_path"],
            stack_name=info["stack"].name,
            project_type=info["project_type"],
            author=info["author"],
            email=info["email"],
            version=Version.default(),
            license=info["license"],
            include_ai=info["include_ai"],
            include_trainer=info["include_trainer"],
            project_code=info["project_code"],
        )

    @staticmethod
    def _is_valid_directory(name: str) -> bool:
        return bool(re.match(r"^[a-z0-9][a-z0-9_]*$", name))

    @staticmethod
    def _confirm(question: str, default: bool = True) -> bool:
        hint = "Y/n" if default else "y/N"
        while True:
            answer = input(f"{question} ({hint}): ").strip().lower()
            if answer == "":
                return default
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            print("Please enter 'y' or 'n'.")

def find_syc_concept_path(start: Optional[Path] = None) -> Path:
    if start is None:
        start = Path(__file__).resolve()

    for base in [start, *start.parents]:
        candidate = base / "docs" / "concepts" / "syc-concept.md"
        if candidate.exists():
            return candidate

    raise FileNotFoundError("syc-concept.md not found in any parent directory")

def parse_syc_concept_markdown(markdown: str, scope: str = "project") -> Tuple[str, Dict[str, str]]:
    scope = scope.strip().lower()
    if scope not in ("workspace", "project"):
        raise ValueError("scope must be 'workspace' or 'project'")

    ide_paths: Dict[str, str] = {}
    canonical = ".agents/skills"

    canonical_pattern = re.compile(
        rf"Cross IDE {scope} based agents skills placed in <{scope}-root>/(.+)",
        re.IGNORECASE,
    )

    ide_pattern = re.compile(
        rf"^(Trae|Antigravity|Cursor|Windsurf) IDE specific {scope} based agents skills placed in <{scope}-root>/(\S+)",
        re.IGNORECASE,
    )

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        m = canonical_pattern.search(line)
        if m:
            canonical = m.group(1).strip().rstrip("/")
            continue

        m = ide_pattern.search(line)
        if m:
            ide = m.group(1).lower()
            path = m.group(2).strip().rstrip("/")
            ide_paths[ide] = path

    if "trae" not in ide_paths:
        ide_paths["trae"] = ".trae/skills"
    if "cursor" not in ide_paths:
        ide_paths["cursor"] = ".cursor/skills"
    if "windsurf" not in ide_paths:
        ide_paths["windsurf"] = ".windsurf/skills"
    if "antigravity" not in ide_paths:
        ide_paths["antigravity"] = ".antigravity/skills"

    return canonical, ide_paths

def _same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except Exception:
        return False

def _create_dir_link(link_path: Path, target_path: Path) -> None:
    if platform.system().lower() == "windows":
        try:
            os.symlink(str(target_path), str(link_path), target_is_directory=True)
            return
        except OSError:
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return

    os.symlink(str(target_path), str(link_path))

def ensure_agents_skills_links(
    project_root: Path,
    dry_run: bool = False,
    scope: str = "project",
    config_path: Optional[Path] = None,
) -> Dict[str, Any]:
    log = logging.getLogger(__name__)

    config = config_path or find_syc_concept_path()
    markdown = config.read_text(encoding="utf-8")
    canonical_rel, ide_paths = parse_syc_concept_markdown(markdown=markdown, scope=scope)

    canonical_target = (project_root / canonical_rel).resolve()
    agents_dir = (project_root / ".agents").resolve()

    actions: list[Dict[str, Any]] = []
    created = 0
    skipped = 0
    failed = 0

    def record(status: str, **fields: Any) -> None:
        actions.append({"status": status, **fields})

    for d in [agents_dir, canonical_target]:
        if d.exists():
            record("exists", path=str(d))
            skipped += 1
            continue
        if dry_run:
            record("dry_run_create_dir", path=str(d))
            skipped += 1
            continue
        d.mkdir(parents=True, exist_ok=True)
        log.info("Created directory", extra={"path": str(d), "operation": "mkdir"})
        record("created_dir", path=str(d))
        created += 1

    for ide, rel_link in ide_paths.items():
        link_path = (project_root / rel_link).resolve()
        target_path = canonical_target

        if link_path.exists():
            if _same_path(link_path, target_path):
                log.info(
                    "Symlink already correct",
                    extra={
                        "operation": "symlink",
                        "ide": ide,
                        "link_path": str(link_path),
                        "target_path": str(target_path),
                        "status": "ok",
                    },
                )
                record("ok", ide=ide, link_path=str(link_path), target_path=str(target_path))
                skipped += 1
                continue

            log.error(
                "Symlink path exists but does not match target",
                extra={
                    "operation": "symlink",
                    "ide": ide,
                    "link_path": str(link_path),
                    "target_path": str(target_path),
                    "status": "exists_mismatch",
                },
            )
            record("failed_exists_mismatch", ide=ide, link_path=str(link_path), target_path=str(target_path))
            failed += 1
            continue

        if dry_run:
            log.info(
                "Dry-run: would create symlink",
                extra={
                    "operation": "symlink",
                    "ide": ide,
                    "link_path": str(link_path),
                    "target_path": str(target_path),
                    "status": "dry_run",
                },
            )
            record("dry_run", ide=ide, link_path=str(link_path), target_path=str(target_path))
            skipped += 1
            continue

        link_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            _create_dir_link(link_path=link_path, target_path=target_path)
            log.info(
                "Created symlink",
                extra={
                    "operation": "symlink",
                    "ide": ide,
                    "link_path": str(link_path),
                    "target_path": str(target_path),
                    "status": "created",
                },
            )
            record("created", ide=ide, link_path=str(link_path), target_path=str(target_path))
            created += 1
        except Exception as exc:
            log.error(
                "Failed to create symlink",
                extra={
                    "operation": "symlink",
                    "ide": ide,
                    "link_path": str(link_path),
                    "target_path": str(target_path),
                    "status": "failed",
                    "error_type": type(exc).__name__,
                },
            )
            record(
                "failed",
                ide=ide,
                link_path=str(link_path),
                target_path=str(target_path),
                error_type=type(exc).__name__,
            )
            failed += 1

    return {
        "config_path": str(config),
        "canonical_target": str(canonical_target),
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "actions": actions,
    }

def run_cli() -> None:
    cli = CLI()
    cli.run()

def _print_supported_targets() -> None:
    from ..core.config import get_config_manager
    cm = get_config_manager()
    targets = cm.list_supported_targets()
    if not targets:
        print("No supported_targets configured.")
        return
    print("Supported target stacks:")
    for key in sorted(targets.keys()):
        meta = targets.get(key, {})
        if isinstance(meta, dict):
            display = meta.get("display_name", key)
            status = meta.get("status", "")
            print(f"  - {key} ({display}) [{status}]")
        else:
            print(f"  - {key}")

def _looks_like_path(value: str) -> bool:
    if not value:
        return False
    if value.startswith("."):
        return True
    return (":" in value) or ("/" in value) or ("\\" in value)

def _create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=True, prog="pyscaffold")
    parser.add_argument("--list-targets", action="store_true")
    parser.add_argument("--stack", type=str, help="Stack key (e.g., java, python, go).")
    parser.add_argument("--framework", type=str, help="Framework name (stack-specific).")
    parser.add_argument("--target", type=str, help="Target directory path to create the project in.")
    parser.add_argument("--name", type=str, help="Project name override (defaults to target folder name).")
    parser.add_argument("--author", type=str, help="Author name override (defaults to git config or config.yml).")
    parser.add_argument("--email", type=str, help="Author email override (defaults to git config or config.yml).")
    parser.add_argument("--license", type=str, help="License identifier (e.g., MIT, Apache-2.0, None).")
    parser.add_argument("--no-git", action="store_true", help="Skip git init.")
    return parser

def _resolve_stack_key(raw_stack: str) -> str:
    from ..core.config import get_config_manager
    cm = get_config_manager()
    normalized = (raw_stack or "").strip().lower()
    if not normalized:
        raise UnsupportedTargetLanguageError(target="", supported=cm.list_supported_active_targets())
    try:
        return cm.validate_target_language(normalized)
    except UnsupportedTargetLanguageError:
        return normalized

def _resolve_project_type_id(stack_name: str, framework: Optional[str]) -> str:
    fw = (framework or "").strip().lower()
    if not fw:
        return "standard"
    if fw == "standard":
        return "standard"
    if stack_name == "java" and fw in {"maven"}:
        return "standard"
    if stack_name == "kotlin" and fw in {"gradle", "gradle-kts", "gradle_kts"}:
        return "standard"
    raise UnsupportedFrameworkError(stack=stack_name, framework=fw, supported=["standard"])

def _run_non_interactive(
    *,
    stack_name: str,
    target_dir: str,
    framework: Optional[str],
    name: Optional[str],
    author: Optional[str],
    email: Optional[str],
    license_id: Optional[str],
    no_git: bool,
) -> bool:
    settings = get_settings()
    stack_repo = StackRepo(settings.templates_path)
    template_repo = TemplateRepo(settings.templates_path)
    engine = Engine(settings.templates_path)
    header = FileHeader()
    scaffold = Scaffold(
        stack_repository=stack_repo,
        template_repository=template_repo,
        template_engine=engine,
        file_header=header,
    )

    stack = stack_repo.get_stack(stack_name)
    if stack is None:
        raise StackNotFoundError(stack_name)

    project_type_id = _resolve_project_type_id(stack_name, framework)
    pt = next((p for p in stack.project_types if p.id == project_type_id), None)
    if pt is None:
        raise PyScaffoldError(f"Project type '{project_type_id}' not found for stack '{stack_name}'.")

    target_path = Path(target_dir).expanduser().resolve()
    raw_name = (name or target_path.name or "My Project").strip()
    project_name = Name.create(raw_name)

    resolved_author = (author or "").strip()
    resolved_email = (email or "").strip()

    if not resolved_author:
        git_name = Git.get_user_name()
        resolved_author = (git_name or settings.author.name or "Unknown").strip()

    if not resolved_email:
        git_email = Git.get_user_email()
        resolved_email = (git_email or settings.author.email or "").strip()

    resolved_license_id = (license_id or "MIT").strip()
    license_type = License.from_string(resolved_license_id)

    project = Project(
        name=project_name,
        target_path=target_path,
        stack_name=stack.name,
        project_type=pt,
        author=resolved_author,
        email=resolved_email,
        version=Version.default(),
        license=license_type,
    )

    scaffold.scaffold(project, progress=None)

    if settings.git.auto_init and not no_git:
        Git.init_repository(project.target_path)

    return True

def main(ui_mode: Optional[str] = None, target: Optional[str] = None) -> bool:
    logger.info("Starting PyScaffold")
    try:
        parser = _create_argument_parser()
        args, _unknown = parser.parse_known_args(sys.argv[1:])

        if args.list_targets:
            _print_supported_targets()
            return True

        if args.stack or args.framework or args.target:
            if not args.stack or not args.target:
                raise PyScaffoldError("Non-interactive mode requires --target <path> and --stack <stack>.")

            stack_key = _resolve_stack_key(args.stack)
            return _run_non_interactive(
                stack_name=stack_key,
                target_dir=args.target,
                framework=args.framework,
                name=args.name,
                author=args.author,
                email=args.email,
                license_id=args.license,
                no_git=bool(args.no_git),
            )

        legacy_stack: Optional[str] = None
        if target:
            legacy_stack = target
        elif args.target and not _looks_like_path(args.target):
            legacy_stack = _resolve_stack_key(args.target)
        elif args.target and _looks_like_path(args.target):
            raise PyScaffoldError("Missing --stack. Use: pyscaffold --target <path> --stack <stack> [--framework <name>].")

        cli = CLI()
        cli.run(target=legacy_stack)
        return True
    except SystemExit:
        return False
    except Exception as exc:
        logger.error("PyScaffold failed: %s", exc, exc_info=True)
        print(f"❌ Fatal error: {exc}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
