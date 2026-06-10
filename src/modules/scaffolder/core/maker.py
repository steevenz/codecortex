"""
Maker engine — generates class files per Decision Matrix (19 types x 16 stacks).

:project: CodeCortex
:package: Modules.Scaffolder.Core.Maker
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .constants import FILE_HEADER_FORMATS, FileConvention

class ClassType(str, Enum):
    INTERFACE = "interface"
    ABSTRACT = "abstract"
    MODEL = "model"
    REPOSITORY = "repository"
    CONTROLLER = "controller"
    SERVICE = "service"
    VALUE_OBJECT = "value_object"
    DTO = "dto"
    EVENT = "event"
    LISTENER = "listener"
    JOB = "job"
    MIDDLEWARE = "middleware"
    FACTORY = "factory"
    SEEDER = "seeder"
    MIGRATION = "migration"
    ENUM = "enum"
    TRAIT = "trait"
    HELPER = "helper"
    VALIDATOR = "validator"
    MAPPER = "mapper"
    COMMAND = "command"
    PRESENTER = "presenter"
    VIEW_MODEL = "view_model"
    FILTER = "filter"
    EXCEPTION = "exception"
    PROVIDER = "provider"
    OBSERVER = "observer"
    STRATEGY = "strategy"
    # Documentation types per ~/.aicoders/docs/standards/documentation.md
    DOC_DRAFT = "doc_draft"
    DOC_PLANNING = "doc_planning"
    DOC_CONCEPT = "doc_concept"
    DOC_FEATURE = "doc_feature"
    DOC_SUBFEATURE = "doc_subfeature"
    DOC_AI_IMPACT = "doc_ai_impact"

class Nature(str, Enum):
    INTERFACE = "interface"
    ABSTRACTION = "abstract"
    CONCRETE = "concrete"
    ENUMERATION = "enum"
    TRAIT = "trait"
    HELPER_MODULE = "helper_module"

_TYPE_CONFIG: Dict[str, Dict[str, Any]] = {
    "interface": {
        "display": "Interface",
        "folder": "Contracts",
        "nature": Nature.INTERFACE,
        "parent": "Protocol",
        "doc": "Contract for {Name} implementors.",
    },
    "abstract": {
        "display": "Abstract Class",
        "folder": "Models/Entities",
        "nature": Nature.ABSTRACTION,
        "parent": "ABC",
        "doc": "Base class for {Name} implementations.",
    },
    "model": {
        "display": "Model / Entity",
        "folder": "Models/Entities",
        "nature": Nature.CONCRETE,
        "parent": "BaseModel",
        "doc": "Domain entity with identity and business rules.",
    },
    "repository": {
        "display": "Repository",
        "folder": "Repositories",
        "nature": Nature.CONCRETE,
        "parent": "Repository",
        "doc": "Data access layer for {Name} entities.",
    },
    "controller": {
        "display": "Controller",
        "folder": "Controllers/Http",
        "nature": Nature.CONCRETE,
        "parent": "APIController",
        "doc": "Handle {Name} HTTP requests and responses.",
    },
    "service": {
        "display": "Service",
        "folder": "Services",
        "nature": Nature.CONCRETE,
        "parent": "Service",
        "doc": "Business logic for {Name} operations.",
    },
    "value_object": {
        "display": "Value Object",
        "folder": "Models/ValueObjects",
        "nature": Nature.CONCRETE,
        "parent": "ValueObject",
        "doc": "Immutable value object with structural equality.",
    },
    "dto": {
        "display": "DTO",
        "folder": "DTOs",
        "nature": Nature.CONCRETE,
        "parent": "DTO",
        "doc": "Data Transfer Object for {Name}.",
    },
    "event": {
        "display": "Event",
        "folder": "Events",
        "nature": Nature.CONCRETE,
        "parent": "Event",
        "doc": "Domain event for {Name}.",
    },
    "listener": {
        "display": "Listener",
        "folder": "Listeners",
        "nature": Nature.CONCRETE,
        "parent": "Listener",
        "doc": "Handles {Name} events.",
    },
    "job": {
        "display": "Job",
        "folder": "Jobs",
        "nature": Nature.CONCRETE,
        "parent": "Job",
        "doc": "Queued job for {Name}.",
    },
    "middleware": {
        "display": "Middleware",
        "folder": "Middleware",
        "nature": Nature.CONCRETE,
        "parent": "Middleware",
        "doc": "Request/response middleware for {Name}.",
    },
    "factory": {
        "display": "Factory",
        "folder": "Factories",
        "nature": Nature.CONCRETE,
        "parent": "Factory",
        "doc": "Factory for creating {Name} instances.",
    },
    "seeder": {
        "display": "Seeder",
        "folder": "Seeders",
        "nature": Nature.CONCRETE,
        "parent": "Seeder",
        "doc": "Seeds {Name} data into the database.",
    },
    "migration": {
        "display": "Migration",
        "folder": "Migrations",
        "nature": Nature.CONCRETE,
        "parent": "Migration",
        "doc": "Database migration for {Name}.",
    },
    "enum": {
        "display": "Enum",
        "folder": "Enums",
        "nature": Nature.ENUMERATION,
        "parent": "Enum",
        "doc": "Enumeration for {Name} values.",
    },
    "trait": {
        "display": "Trait",
        "folder": "Traits",
        "nature": Nature.TRAIT,
        "parent": "",
        "doc": "Shared behaviour mixin for {Name}.",
    },
    "helper": {
        "display": "Helper",
        "folder": "Helpers",
        "nature": Nature.HELPER_MODULE,
        "parent": "",
        "doc": "Utility functions for {Name}.",
    },
    "validator": {
        "display": "Validator",
        "folder": "Validators",
        "nature": Nature.CONCRETE,
        "parent": "Validator",
        "doc": "Validation rules for {Name}.",
    },
    "mapper": {
        "display": "Mapper",
        "folder": "Mappers",
        "nature": Nature.CONCRETE,
        "parent": "Mapper",
        "doc": "Maps {Name} between layers.",
    },
    "command": {
        "display": "Command",
        "folder": "Controllers/Cli",
        "nature": Nature.CONCRETE,
        "parent": "Command",
        "doc": "CLI command for {Name}.",
    },
    "presenter": {
        "display": "Presenter",
        "folder": "Presenters",
        "nature": Nature.CONCRETE,
        "parent": "Presenter",
        "doc": "Presentation logic for {Name}.",
    },
    "view_model": {
        "display": "ViewModel",
        "folder": "ViewModels",
        "nature": Nature.CONCRETE,
        "parent": "ViewModel",
        "doc": "View data for {Name}.",
    },
    "filter": {
        "display": "Filter",
        "folder": "Filters",
        "nature": Nature.CONCRETE,
        "parent": "Filter",
        "doc": "Query filter for {Name}.",
    },
    "exception": {
        "display": "Exception",
        "folder": "Exceptions",
        "nature": Nature.CONCRETE,
        "parent": "Exception",
        "doc": "Exception for {Name} errors.",
    },
    "provider": {
        "display": "Provider",
        "folder": "Providers",
        "nature": Nature.CONCRETE,
        "parent": "ServiceProvider",
        "doc": "Service provider for {Name}.",
    },
    "observer": {
        "display": "Observer",
        "folder": "Observers",
        "nature": Nature.CONCRETE,
        "parent": "Observer",
        "doc": "Observes {Name} model events.",
    },
    "strategy": {
        "display": "Strategy",
        "folder": "Strategies",
        "nature": Nature.INTERFACE,
        "parent": "Strategy",
        "doc": "Strategy interface for {Name}.",
    },
    # Documentation types per ~/.aicoders/docs/standards/documentation.md
    "doc_draft": {
        "display": "Draft Documentation",
        "folder": "docs/drafts",
        "nature": Nature.CONCRETE,
        "parent": "",
        "doc": "Draft documentation for {Name}.",
    },
    "doc_planning": {
        "display": "Planning Documentation",
        "folder": "docs/drafts",
        "nature": Nature.CONCRETE,
        "parent": "",
        "doc": "Planning documentation for {Name}.",
    },
    "doc_concept": {
        "display": "Concept Documentation",
        "folder": "docs/features",
        "nature": Nature.CONCRETE,
        "parent": "",
        "doc": "Concept documentation for {Name} domain.",
    },
    "doc_feature": {
        "display": "Feature Documentation",
        "folder": "docs/features",
        "nature": Nature.CONCRETE,
        "parent": "",
        "doc": "Feature documentation for {Name}.",
    },
    "doc_subfeature": {
        "display": "Sub-Feature Documentation",
        "folder": "docs/features",
        "nature": Nature.CONCRETE,
        "parent": "",
        "doc": "Sub-feature documentation for {Name}.",
    },
    "doc_ai_impact": {
        "display": "AI Impact Documentation",
        "folder": "docs/features",
        "nature": Nature.CONCRETE,
        "parent": "",
        "doc": "AI impact analysis for {Name}.",
    },
}

_STACK_META: Dict[str, Dict[str, Any]] = {
    "python": {
        "ext": ".py",
        "file_conv": "snake_case",
        "dir_conv": FileConvention.SNAKE_CASE,
        "comment_style": '"""',
        "class_decl": "class {name}{parens}:",
        "import_fmt": "from {module} import {symbol}",
        "null": "None",
        "visibility": "",
        "interface_impl": "",
    },
    "typescript": {
        "ext": ".ts",
        "file_conv": "PascalCase",
        "dir_conv": FileConvention.KEBAB_CASE,
        "comment_style": "/**",
        "class_decl": "class {name}{parens} {{",
        "import_fmt": "import {{ {symbol} }} from '{module}';",
        "null": "null",
        "visibility": "public ",
        "interface_impl": "implements ",
    },
    "javascript": {
        "ext": ".js",
        "file_conv": "PascalCase",
        "dir_conv": FileConvention.KEBAB_CASE,
        "comment_style": "/**",
        "class_decl": "class {name}{parens} {{",
        "import_fmt": "const {{ {symbol} }} = require('{module}');",
        "null": "null",
        "visibility": "",
        "interface_impl": "",
    },
    "nodejs-typescript": {
        "ext": ".ts",
        "file_conv": "PascalCase",
        "dir_conv": FileConvention.KEBAB_CASE,
        "comment_style": "/**",
        "class_decl": "class {name}{parens} {{",
        "import_fmt": "import {{ {symbol} }} from '{module}';",
        "null": "null",
        "visibility": "public ",
        "interface_impl": "implements ",
    },
    "php": {
        "ext": ".php",
        "file_conv": "PascalCase",
        "dir_conv": FileConvention.PASCAL_CASE,
        "comment_style": "/**",
        "class_decl": "class {name}{parens} {{",
        "import_fmt": "use {module}\\{symbol};",
        "null": "null",
        "visibility": "public ",
        "interface_impl": "implements ",
    },
    "go": {
        "ext": ".go",
        "file_conv": "snake_case",
        "dir_conv": FileConvention.SNAKE_CASE,
        "comment_style": "//",
        "class_decl": "type {name} struct {{",
        "import_fmt": 'import "{module}"',
        "null": "nil",
        "visibility": "",
        "interface_impl": "",
    },
    "java": {
        "ext": ".java",
        "file_conv": "PascalCase",
        "dir_conv": FileConvention.LOWERCASE,
        "comment_style": "/**",
        "class_decl": "class {name}{parens} {{",
        "import_fmt": "import {module}.{symbol};",
        "null": "null",
        "visibility": "public ",
        "interface_impl": "implements ",
    },
    "kotlin": {
        "ext": ".kt",
        "file_conv": "PascalCase",
        "dir_conv": FileConvention.LOWERCASE,
        "comment_style": "/**",
        "class_decl": "class {name}{parens} {{",
        "import_fmt": "import {module}.{symbol}",
        "null": "null",
        "visibility": "",
        "interface_impl": ": ",
    },
    "csharp": {
        "ext": ".cs",
        "file_conv": "PascalCase",
        "dir_conv": FileConvention.PASCAL_CASE,
        "comment_style": "///",
        "class_decl": "class {name}{parens}",
        "import_fmt": "using {module};",
        "null": "null",
        "visibility": "public ",
        "interface_impl": " : ",
    },
    "swift": {
        "ext": ".swift",
        "file_conv": "PascalCase",
        "dir_conv": FileConvention.PASCAL_CASE,
        "comment_style": "///",
        "class_decl": "class {name}{parens} {{",
        "import_fmt": "import {module}",
        "null": "nil",
        "visibility": "",
        "interface_impl": ": ",
    },
    "rust": {
        "ext": ".rs",
        "file_conv": "snake_case",
        "dir_conv": FileConvention.SNAKE_CASE,
        "comment_style": "//!",
        "class_decl": "struct {name} {{",
        "import_fmt": "use {module}::{symbol};",
        "null": "None",
        "visibility": "",
        "interface_impl": "",
    },
    "cpp": {
        "ext": ".cpp",
        "file_conv": "snake_case",
        "dir_conv": FileConvention.SNAKE_CASE,
        "comment_style": "/**",
        "class_decl": "class {name}{parens} {{",
        "import_fmt": '#include "{module}"',
        "null": "nullptr",
        "visibility": "public:",
        "interface_impl": " : ",
    },
    "dart": {
        "ext": ".dart",
        "file_conv": "snake_case",
        "dir_conv": FileConvention.SNAKE_CASE,
        "comment_style": "///",
        "class_decl": "class {name}{parens} {{",
        "import_fmt": "import '{module}';",
        "null": "null",
        "visibility": "",
        "interface_impl": "implements ",
    },
    "flutter": {
        "ext": ".dart",
        "file_conv": "snake_case",
        "dir_conv": FileConvention.SNAKE_CASE,
        "comment_style": "///",
        "class_decl": "class {name}{parens} {{",
        "import_fmt": "import '{module}';",
        "null": "null",
        "visibility": "",
        "interface_impl": "implements ",
    },
}

_SUPPORTED_STACKS = set(_STACK_META.keys())

def _to_file_name(domain_name: str, convention: str, ext: str) -> str:
    if convention == "PascalCase":
        return domain_name + ext
    elif convention == "kebab-case":
        s = re.sub(r"(?<=[a-z])(?=[A-Z])", "-", domain_name).lower()
        return s + ext
    elif convention == "lowercase":
        return domain_name.lower() + ext
    else:
        s = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", domain_name).lower()
        return s + ext

def _to_dir_path(canonical: str, convention: FileConvention) -> str:
    parts = canonical.replace("-", "_").split("/")
    converted = []
    for part in parts:
        if convention == FileConvention.KEBAB_CASE:
            slug = re.sub(r"(?<=[a-z])(?=[A-Z])", "-", part).lower()
            converted.append(slug.replace("_", "-"))
        elif convention == FileConvention.PASCAL_CASE:
            pascal = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", part).title().replace(" ", "")
            converted.append(pascal.replace("_", ""))
        elif convention == FileConvention.LOWERCASE:
            flat = re.sub(r"(?<=[a-z])(?=[A-Z])", "", part).lower()
            converted.append(flat.replace("_", ""))
        else:
            snaked = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", part).lower()
            converted.append(snaked)
    return "/".join(converted)

def _parens_for_stack(name: str, nature: Nature, stack_meta: Dict[str, Any], base: str) -> str:
    stack = stack_meta
    if nature == Nature.INTERFACE and stack["class_decl"].startswith("class"):
        if stack.get("interface_impl"):
            return f" {stack['interface_impl']}{base}" if base else ""
        return ""
    if nature == Nature.ABSTRACTION:
        if base:
            if stack["ext"] == ".py":
                return f"({base})"
            return f" extends {base}"
        return "()" if stack["ext"] == ".py" else ""
    if base:
        if stack["ext"] == ".py":
            return f"({base})"
        if stack["ext"] == ".go":
            return ""
        if stack["ext"] in (".ts", ".js"):
            return f" extends {base}"
    if stack["ext"] == ".py":
        return ":"
    return ""

def _build_header(
    project_name: str,
    package_path: str,
    author: str,
    description: str,
    stack: str,
) -> str:
    fmt = FILE_HEADER_FORMATS.get(stack)
    if not fmt:
        return ""
    try:
        return fmt.format(
            project_name=project_name,
            package_path=package_path,
            author=author,
            description=description,
        )
    except KeyError:
        return ""

def _build_imports(nature: Nature, base: str, stack: str, stack_meta: Dict[str, Any]) -> str:
    if not base:
        return ""
    sm = stack_meta
    if nature in (Nature.INTERFACE, Nature.TRAIT, Nature.HELPER_MODULE):
        return ""

    if stack == "python":
        imports = []
        if base in ("ABC", "Protocol"):
            imports.append("from abc import ABC, abstractmethod")
        elif base == "BaseModel":
            imports.append("from pydantic import BaseModel")
        elif base == "Enum":
            imports.append("from enum import Enum")
        elif base == "ValueObject":
            imports.append("from dataclasses import dataclass")
        return "\n".join(imports) + "\n\n" if imports else ""

    if stack == "go":
        return ""

    if stack in ("csharp", "java"):
        if base:
            return sm["import_fmt"].format(module=f"System.{base}") + "\n\n"

    return ""

def _build_class_body(
    name: str,
    type_id: str,
    nature: Nature,
    stack: str,
    stack_meta: Dict[str, Any],
) -> str:
    sm = stack_meta
    ext = sm["ext"]
    indent = "    "

    # Handle documentation types separately
    if type_id.startswith("doc_"):
        return _build_document_body(name, type_id, stack_meta)

    if nature == Nature.INTERFACE:
        if ext == ".py":
            return (f"{indent}@abstractmethod\n"
                    f"{indent}def execute(self) -> None:\n"
                    f"{indent}{indent}...\n")
        return f"{indent}execute(): void;\n"

    if nature == Nature.ABSTRACTION:
        if ext == ".py":
            return (f"{indent}def __init__(self) -> None:\n"
                    f"{indent}{indent}super().__init__()\n\n"
                    f"{indent}@abstractmethod\n"
                    f"{indent}def execute(self) -> None:\n"
                    f"{indent}{indent}...\n")
        return f"{indent}abstract execute(): void;\n"

    if nature == Nature.TRAIT:
        if ext == ".py":
            return (f"{indent}def shared_method(self) -> None:\n"
                    f"{indent}{indent}pass\n")
        return f"{indent}sharedMethod(): void {{\n    }}\n"

    if nature == Nature.HELPER_MODULE:
        return (f"{indent}@staticmethod\n"
                f"{indent}def {name.lower()}_util() -> None:\n"
                f"{indent}{indent}pass\n")

    if nature == Nature.ENUMERATION:
        if ext == ".py":
            return f"{indent}DEFAULT = \"default\"\n"
        return f"{indent}DEFAULT = \"default\"\n"

    if nature == Nature.CONCRETE:
        return _concrete_body(name, type_id, ext, stack, indent)

    return ""

def _build_document_body(name: str, type_id: str, stack_meta: Dict[str, Any]) -> str:
    """Generate documentation content based on documentation type per ~/.aicoders/docs/standards/documentation.md."""
    indent = "    "
    domain_pascal = "".join(w[0].upper() + w[1:] for w in re.split(r"[\s\-_]+", name.strip()) if w)
    domain_lower = domain_pascal.lower()
    domain_upper = domain_pascal.upper()
    domain_slug = re.sub(r"(?<=[a-z])(?=[A-Z])", "-", domain_pascal).lower()
    
    if type_id == "doc_draft":
        return f"""# {domain_pascal} - Draft Documentation

> **Status:** Draft
> **Created:** {name}
> **Last Updated:** {name}

## Overview

Draft documentation for {domain_pascal}.

## Notes

- This is a draft document
- Content will be finalized in the planning phase
- Use this for brainstorming and initial ideas

## TODO

- [ ] Define scope
- [ ] Research requirements
- [ ] Create structure
- [ ] Write content
"""

    if type_id == "doc_planning":
        return f"""# {domain_pascal} - Planning Documentation

> **Status:** Planning
> **Created:** {name}
> **Last Updated:** {name}

## Overview

Planning documentation for {domain_pascal}.

## Objectives

1. Define clear objectives
2. Identify stakeholders
3. Create timeline
4. Define success criteria

## Requirements

- Functional requirements
- Non-functional requirements
- Technical constraints
- Business constraints

## Timeline

- Phase 1: Research (Week 1)
- Phase 2: Design (Week 2)
- Phase 3: Implementation (Week 3-4)
- Phase 4: Testing (Week 5)
"""

    if type_id == "doc_concept":
        return f"""# {domain_pascal}: {domain_pascal}

> **Domain:** {domain_lower}
> **Package:** `src/`
> **Version:** 1.0.0
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

{domain_pascal} domain provides core functionality for the project.

## Why This Exists

- Provides essential business logic
- Enables key user workflows
- Supports system integration

## Architecture

```
{domain_lower}/
├── core/           → Business logic, domain entities
├── api/            → API endpoints, controllers
├── services/       → Business services
└── adapters/       → External integrations
```

## Domain Boundary

- Owns: All {domain_lower}-specific code and documentation
- Does NOT own: External dependencies, 3rd-party SDKs
- Dependencies: External services via adapters only

## CLI Architecture Note

CLI domain name: {domain_lower}
Aliases: {domain_lower[:3]}

## ~/.aicoders/ Compliance

- Follows Aegis-Architecture-v1.0 standards
- Constructor injection for all services
- DTOs for all layer crossings
- Adapters wrap all 3rd-party dependencies

## Error Codes

| Prefix | Tool |
|--------|------|
| {domain_upper}_001 | Validation errors |
| {domain_upper}_002 | Not found errors |
| {domain_upper}_500 | Internal errors |

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

- Feature documentation
- Sub-feature documentation
- AI impact analysis
"""

    if type_id == "doc_feature":
        return f"""# {domain_pascal} Feature Documentation

> **Feature:** {domain_pascal}
> **Status:** Active
> **Created:** {name}
> **Last Updated:** {name}

## Feature Overview

{domain_pascal} feature provides core functionality for the project.

## User Stories

1. As a user, I want to use {domain_pascal} to achieve specific goal
2. As a developer, I want to integrate {domain_pascal} with other systems
3. As an admin, I want to configure {domain_pascal} settings

## Acceptance Criteria

- [ ] Feature is functional
- [ ] Feature is performant
- [ ] Feature is secure
- [ ] Feature is documented

## Implementation Notes

- Technical implementation details
- Integration points
- Configuration options
"""

    if type_id == "doc_subfeature":
        return f"""# {domain_pascal} Sub-Feature Documentation

> **Sub-Feature:** {domain_pascal}
> **Status:** Active
> **Created:** {name}
> **Last Updated:** {name}

## Sub-Feature Overview

{domain_pascal} sub-feature provides specific functionality within the domain.

## Purpose

Detailed description of the sub-feature.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| param1 | string | Yes | - | Description |
| param2 | int | No | 0 | Description |

## Algorithm

1. Step 1: Initialize
2. Step 2: Process
3. Step 3: Return result

## Use Case

Scenario + workflow for using this sub-feature.

## Error Cases

| Error Code | Description | Severity |
|------------|-------------|----------|
| {domain_upper}_001 | Invalid input | High |
| {domain_upper}_002 | Not found | High |
| {domain_upper}_500 | Internal error | Critical |
"""

    if type_id == "doc_ai_impact":
        return f"""# {domain_pascal} AI Impact Analysis

> **Domain:** {domain_lower}
> **Version:** 1.0.0
> **Date:** {name}

## Executive Summary

{domain_pascal} provides high AI coder utility with 10/10 impact score.

## Token Efficiency

- Enrichment cost per response: 300 tokens
- Token savings via reduced tool calls: 40%
- Token savings via enriched JSON output: 50%

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

## Token Savings Analysis

| Scenario | Without Enrichment | With Enrichment | Savings |
|----------|-------------------|----------------|---------|
| Feature discovery | 5 calls × 200 tokens = 1000 tokens | 1 call × 300 tokens = 300 tokens | 70% |
| Sub-feature documentation | 4 calls × 200 tokens = 800 tokens | 1 call × 350 tokens = 350 tokens | 56% |
| AI impact analysis | 3 calls × 200 tokens = 600 tokens | 1 call × 400 tokens = 400 tokens | 33% |

## Conclusion

{domain_pascal} is highly optimized for AI coder interaction with 70% average token savings.
"""

    return f"# {domain_pascal} Documentation\n\n> **Type:** {type_id}\n> **Created:** {name}\n\n## Overview\n\nDocumentation for {domain_pascal}.\n\n## Notes\n\n- This is a placeholder documentation file\n- Content should be updated as the project evolves\n- Follow the documentation standard in ~/.aicoders/docs/standards/documentation.md\n"

def _concrete_body(name: str, type_id: str, ext: str, stack: str, indent: str) -> str:
    name_lower = name[0].lower() + name[1:] if name else name

    if type_id in ("model", "value_object", "dto", "view_model"):
        if ext == ".py":
            return (f"{indent}def __init__(self) -> None:\n"
                    f"{indent}{indent}super().__init__()\n"
                    f"{indent}{indent}self.id: int = 0\n")

    if type_id == "controller":
        if ext == ".py":
            return (f"{indent}async def index(self) -> dict:\n"
                    f"{indent}{indent}return {{\"data\": []}}\n")

    if type_id == "service":
        if ext == ".py":
            return (f"{indent}async def execute(self) -> None:\n"
                    f"{indent}{indent}pass\n")
        return f"{indent}async execute(): Promise<void> {{\n    }}\n"

    if type_id == "repository":
        if ext == ".py":
            return (f"{indent}async def find_by_id(self, id: int) -> dict | None:\n"
                    f"{indent}{indent}return None\n")

    if type_id == "event":
        if ext == ".py":
            return (f"{indent}def __init__(self, payload: dict) -> None:\n"
                    f"{indent}{indent}super().__init__()\n"
                    f"{indent}{indent}self.payload = payload\n")

    if type_id == "listener":
        if ext == ".py":
            return (f"{indent}async def handle(self, event: dict) -> None:\n"
                    f"{indent}{indent}pass\n")

    if type_id == "job":
        if ext == ".py":
            return (f"{indent}async def handle(self) -> None:\n"
                    f"{indent}{indent}pass\n")

    if type_id == "middleware":
        if ext == ".py":
            return (f"{indent}async def before(self, request: dict) -> dict:\n"
                    f"{indent}{indent}return request\n")

    if type_id == "factory":
        if ext == ".py":
            return (f"{indent}@staticmethod\n"
                    f"{indent}def create() -> dict:\n"
                    f"{indent}{indent}return {{\"type\": \"{name_lower}\"}}\n")

    if type_id == "seeder":
        if ext == ".py":
            return (f"{indent}def run(self) -> None:\n"
                    f"{indent}{indent}pass\n")

    if type_id == "migration":
        if ext == ".py":
            return (f"{indent}def up(self) -> None:\n"
                    f"{indent}{indent}pass\n\n"
                    f"{indent}def down(self) -> None:\n"
                    f"{indent}{indent}pass\n")

    if type_id == "mapper":
        if ext == ".py":
            return (f"{indent}def to_dto(self, entity: dict) -> dict:\n"
                    f"{indent}{indent}return entity\n")

    if type_id == "validator":
        if ext == ".py":
            return (f"{indent}def validate(self, data: dict) -> bool:\n"
                    f"{indent}{indent}return True\n")

    if ext == ".py":
        return f"{indent}def execute(self) -> None:\n{indent}{indent}pass\n"

    return ""

def _close_brace(stack_meta: Dict[str, Any], indent: int = 0) -> str:
    ext = stack_meta["ext"]
    if ext == ".py":
        return ""
    decl = stack_meta["class_decl"]
    if "{" in decl:
        return "\n}"
    return ""

def make_class(
    type_id: str,
    name: str,
    stack: str = "python",
    module: Optional[str] = None,
    project_name: str = "Project",
    author: str = "Author",
    target_path: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    resolved_type = type_id.strip().lower().replace("-", "_")
    if resolved_type not in _TYPE_CONFIG:
        available = sorted(_TYPE_CONFIG.keys())
        return {
            "success": False,
            "error": f"Unknown type '{type_id}'. Available: {', '.join(available)}",
        }

    resolved_stack = stack.strip().lower()
    if resolved_stack not in _STACK_META:
        available = sorted(_STACK_META.keys())
        return {
            "success": False,
            "error": f"Unsupported stack '{stack}'. Supported: {', '.join(available)}",
        }

    config = _TYPE_CONFIG[resolved_type]
    sm = _STACK_META[resolved_stack]
    nature = config["nature"]
    base = config.get("parent", "")

    domain_pascal = "".join(w[0].upper() + w[1:] for w in re.split(r"[\s\-_]+", name.strip()) if w)
    if not domain_pascal:
        return {"success": False, "error": "Name must contain at least one alphanumeric segment"}

    file_name = _to_file_name(domain_pascal, sm["file_conv"], sm["ext"])
    canon_folder = config["folder"]
    if module:
        dir_path = f"{module}/{_to_dir_path(canon_folder, sm['dir_conv'])}" if canon_folder else module
    else:
        dir_path = _to_dir_path(canon_folder, sm["dir_conv"]) if canon_folder else ""
    rel_path = f"{dir_path}/{file_name}" if dir_path else file_name

    package_path = dir_path.replace("/", ".")

    description = config["doc"].format(Name=domain_pascal)

    header = _build_header(project_name, package_path, author, description, resolved_stack)

    imports = _build_imports(nature, base, resolved_stack, sm)

    parens = _parens_for_stack(domain_pascal, nature, sm, base)

    class_line = sm["class_decl"].format(name=domain_pascal, parens=parens) if "parens" in sm["class_decl"] else sm["class_decl"].format(name=domain_pascal)

    body = _build_class_body(domain_pascal, resolved_type, nature, resolved_stack, sm)

    closing = _close_brace(sm)

    result_parts = []
    if header:
        result_parts.append(header)
    result_parts.append(imports)
    result_parts.append(class_line)
    if body:
        result_parts.append(body)
    if closing:
        result_parts.append(closing)
    elif sm["ext"] not in (".go", ".rs"):
        pass

    content = "\n".join(result_parts)
    if sm["ext"] == ".php" and not content.lstrip().startswith("<?php"):
        content = "<?php\n" + content

    written = False
    abs_path: Optional[str] = None
    if target_path:
        abs_target = Path(target_path).resolve()
        full_path = abs_target / rel_path
        if full_path.exists() and not overwrite:
            return {
                "success": False,
                "error": f"File already exists: {rel_path}. Set overwrite=true to allow.",
                "content": content,
                "relative_path": rel_path,
            }
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        written = True
        abs_path = str(full_path)

    return {
        "success": True,
        "type": resolved_type,
        "type_display": config["display"],
        "stack": resolved_stack,
        "class_name": domain_pascal,
        "file_name": file_name,
        "relative_path": rel_path,
        "absolute_path": abs_path,
        "content": content,
        "content_length": len(content),
        "written": written,
    }

def list_types() -> List[Dict[str, Any]]:
    result = []
    for tid, cfg in sorted(_TYPE_CONFIG.items()):
        result.append({
            "id": tid,
            "display": cfg["display"],
            "nature": cfg["nature"].value,
            "folder": cfg["folder"],
            "doc": cfg["doc"],
        })
    return result

def list_stacks() -> List[str]:
    return sorted(_STACK_META.keys())
