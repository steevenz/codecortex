"""
Core domain layer for the scaffolding module.

:project: CodeCortex
:package: Modules.Scaffolder.Core
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Scaffolder-v1.0
"""
from .config import PyScaffold, get_settings, reset_settings
from .constants import StackType, ProjectPattern, LicenseIdentifier, FileConvention
from .dtos import Project, Stack, Template, ProjectType, FileConventions
from .exceptions import PyScaffoldError, InvalidNameError, ValidationError
from .generators import gitignore, env_boilerplate, pyproject, readme, requirements, dockerfile, docker_compose, setup_sh, setup_bat, setup_ps1, copy_boilerplate
from .interfaces import StackRepository, TemplateRepository
from .license import License
from .maker import make_class, ClassType, list_types as maker_list_types, list_stacks as maker_list_stacks
from .name import Name
