# Scaffolder: Project Generation Engine

> **Domain:** Scaffolder
> **Package:** `src/modules/scaffolder/`
> **Version:** 1.0.0
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

Scaffolder is the **project generation engine** — creates production-ready project scaffolds with 14+ technology stacks, 34 types (28 code + 6 documentation), and full ~/.aicoders/ compliance. It provides 7 MCP tools for stack discovery, name validation, content generation, class generation, documentation generation, and full project scaffolding with dry-run safety.

## Why This Exists

- **Rapid Project Initialization:** Generate complete project structures in seconds with 14+ technology stacks
- **Decision Matrix Generation:** Generate 34 types (28 code types + 6 documentation types) with proper naming conventions per ~/.aicoders/docs/standards/documentation.md
- **Multi-Stack Support:** Python, TypeScript, JavaScript, PHP, Go, Java, Kotlin, C#, Swift, Rust, C++, Dart, Flutter
- **Standards Compliance:** Auto-generates ~/.aicoders/ compliant file headers, directory structures, and boilerplate
- **Documentation Generation:** Generate draft, planning, concept, feature, sub-feature, and AI impact documentation per standard
- **Dry-Run Safety:** Preview scaffolding operations before writing files
- **Template Engine:** Jinja2-based template rendering with shared and stack-specific templates

## Theoretical Foundation

- **Jinja2 Templating:** Template rendering engine for code generation
- **Decision Matrix:** 34 types (28 code types + 6 documentation types) mapped to architectural patterns (DDD, Layered, FSD)
- **Documentation Standard:** Follows ~/.aicoders/docs/standards/documentation.md for documentation generation
- **File Convention Mapping:** Stack-specific naming conventions (snake_case, PascalCase, kebab-case, lowercase)
- **Pydantic Settings:** Configuration management with environment variable support
- **Path Resolution:** Cross-platform path handling for Windows, macOS, Linux
- **YAML Manifest Parsing:** Stack and project type definitions from manifest.yml
- **Template Inheritance:** Shared templates overridden by stack-specific templates
- **DI Architecture:** Constructor injection for all services and adapters

## Architecture

```
src/modules/scaffolder/
├── api/              → tools.py: 7 MCP tools, cli.py: CLI commands, api_response() compliant
├── services/         → Service classes: DI via constructor, pure use-cases
│   ├── scaffold.py   → Main orchestrator for project scaffolding
│   └── cli.py        → Interactive CLI with prompts and validation
├── adapters/         → External system integrations
│   ├── stack.py      → Stack repository (manifest.yml parsing)
│   ├── template.py   → Template repository (Jinja2 resolution)
│   ├── filesystem.py → File I/O operations
│   └── git.py        → Git initialization
├── core/             → Domain logic and DTOs
│   ├── config.py     → Pydantic settings
│   ├── constants.py  → Enums and directory structures
│   ├── dtos.py       → Project, Stack, Template DTOs
│   ├── exceptions.py → Custom exceptions
│   ├── generators.py → Content generators (gitignore, pyproject, etc.)
│   ├── interfaces.py → Repository interfaces
│   ├── license.py    → License generation
│   ├── maker.py      → Decision Matrix class generation
│   └── name.py       → Name validation and normalization
└── main.py           → Backward-compatible shim
```

## Domain Boundary

- **Owns:** `scaffold_list_stacks`, `scaffold_get_stack`, `scaffold_validate_name`, `scaffold_list_licenses`, `scaffold_generate`, `scaffold_make`, `scaffold_create`
- **Does NOT own:** Template storage (datasets/templates/), Git operations (coderepository domain)
- **Depends on:** `FileHeader`, `Version`, `api_response()`, `new_request_id()`
- **Consumed by:** MCP layer via `api/tools.py`, CLI via `api/cli.py`

## CLI Architecture Note

The CLI domain uses `sc` as the alias for scaffolder commands. Users access scaffolding operations via `codecortex sc <command>`. This provides a unified interface with other domains (repo, fs, cb, kg, ide).

## ~/.aicoders/ Compliance

- **API Standard:** `api_response()` for all tool responses
- **DDD:** `api/` + `services/` + `core/` + `adapters/` separation
- **DI:** Constructor injection for all services
- **Boundary:** Data crosses layers only via DTOs
- **Error Handling:** Custom exceptions with structured error messages
- **Logging:** `CodeCortex.Scaffolder.*` logger namespace
- **Documentation:** All docs in `docs/features/scaffolder/`
- **File Headers:** Auto-generated @project, @package, @author, @copyright, @stack headers
- **Directory Structure:** 33+ standard directories per project-structure-standard.md

## Error Codes

| Prefix | Tool |
|--------|------|
| SC_0xx | scaffold_list_stacks |
| SC_01x | scaffold_get_stack |
| SC_02x | scaffold_validate_name |
| SC_03x | scaffold_list_licenses |
| SC_04x | scaffold_generate |
| SC_05x | scaffold_make |
| SC_06x | scaffold_create |
| SC_5xx | Internal error |

## 10/10 AI Coder Impact Features

1. **Stack Discovery** — List all available stacks with project types and file conventions
2. **Name Validation** — Validate and normalize project names with display/slug/snake/pascal forms
3. **Content Generation** — Generate 13+ boilerplate files (gitignore, pyproject, Dockerfile, etc.)
4. **Code Generation** — Generate 28 code types per Decision Matrix with proper naming
5. **Documentation Generation** — Generate 6 documentation types (draft, planning, concept, feature, sub-feature, AI impact) per ~/.aicoders/docs/standards/documentation.md
6. **Multi-Stack Support** — 14+ technology stacks with stack-specific conventions
7. **Dry-Run Safety** — Preview scaffolding operations before writing files
8. **Template Context** — 20+ Jinja2 variables for template rendering
9. **Project Patterns** — Support for Layered, DDD, and FSD architectural patterns
10. **Full Project Scaffolding** — Complete project structure with 33+ directories

## Tool Reference

### scaffold_list_stacks

**Parameters:** None

**Output:**
```json
{
  "stacks": [{
    "name": "python",
    "display_name": "Python",
    "version": "3.12",
    "file_conventions": {
      "directories": "snake_case",
      "modules": "snake_case.py",
      "classes": "PascalCase"
    },
    "project_types": ["standard", "web_api", "cli_tool"]
  }]
}
```

---

### scaffold_get_stack

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `stack_name` | string | ✅ | — | Stack identifier (e.g., "python", "typescript") |

**Output:**
```json
{
  "stack": {
    "name": "python",
    "display_name": "Python",
    "version": "3.12",
    "file_conventions": {...},
    "project_types": [...]
  }
}
```

---

### scaffold_validate_name

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | ✅ | — | Raw project name to validate |

**Output:**
```json
{
  "display": "My Project",
  "slug": "my-project",
  "snake": "my_project",
  "pascal": "MyProject"
}
```

---

### scaffold_list_licenses

**Parameters:** None

**Output:**
```json
{
  "licenses": [
    {"id": "MIT", "name": "Mit"},
    {"id": "Apache-2.0", "name": "Apache 2.0"},
    {"id": "GPL-3.0", "name": "Gpl 3.0"}
  ]
}
```

---

### scaffold_generate

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file_type` | string | ✅ | — | Type of content (gitignore, env, pyproject, readme, etc.) |
| `project_category` | string | ❌ | `standard` | Project category (standard, data_science, web_api, cli_tool, automation) |
| `project_name` | string | ❌ | `My Project` | Project display name |
| `author` | string | ❌ | `Author` | Author name |
| `email` | string | ❌ | `author@example.com` | Author email |
| `license_name` | string | ❌ | `MIT` | License string |

**Output:**
```json
{
  "filename": ".gitignore",
  "content": "# Python byte-compiled...",
  "content_length": 1234
}
```

---

### scaffold_make

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | ✅ | — | Type (28 code types: interface, abstract, model, repository, controller, service, value_object, dto, event, listener, job, middleware, factory, seeder, migration, enum, trait, helper, validator, mapper, command, presenter, view_model, filter, exception, provider, observer, strategy; 6 documentation types: doc_draft, doc_planning, doc_concept, doc_feature, doc_subfeature, doc_ai_impact) |
| `name` | string | ✅ | — | Domain concept name (e.g., "User", "Order") |
| `stack` | string | ❌ | `python` | Technology stack |
| `module` | string | ❌ | — | Optional module context for DDD projects |
| `project_name` | string | ❌ | `Project` | Project name for headers |
| `author` | string | ❌ | `Author` | Author name for headers |
| `target_path` | string | ❌ | — | Absolute path to write file |
| `overwrite` | bool | ❌ | `false` | Overwrite existing files |

**Output:**
```json
{
  "type": "repository",
  "type_display": "Repository",
  "stack": "python",
  "class_name": "UserRepository",
  "file_name": "user_repository.py",
  "relative_path": "repositories/user_repository.py",
  "absolute_path": "/path/to/repositories/user_repository.py",
  "content": "# @project...\nclass UserRepository:",
  "content_length": 456,
  "written": true
}
```

---

### scaffold_create

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | ✅ | — | Project name |
| `stack` | string | ❌ | `python` | Technology stack |
| `project_type` | string | ❌ | `standard` | Project type within stack |
| `target_path` | string | ❌ | — | Absolute output path |
| `author` | string | ❌ | — | Author name |
| `email` | string | ❌ | — | Author email |
| `version` | string | ❌ | — | SemVer string |
| `license` | string | ❌ | `MIT` | License identifier |
| `include_ai` | bool | ❌ | `false` | Include src/ai/ module |
| `include_trainer` | bool | ❌ | `false` | Include src/trainer/ module |
| `project_code` | string | ❌ | — | Optional project code |
| `overwrite` | bool | ❌ | `false` | Allow overwriting |
| `dry_run` | bool | ❌ | `true` | Validate only, no files written |

**Output:**
```json
{
  "dry_run": false,
  "target_path": "/path/to/my-project",
  "name": "My Project",
  "slug": "my-project",
  "stack": "python",
  "project_type": "standard",
  "version": "0.1.0",
  "license": "MIT",
  "progress": ["Created directories", "Rendered templates", "Wrote files"]
}
```

---

## Related Sub-Features

- [Scaffold List Stacks](sub-features/scaffold_list_stacks/concept.md)
- [Scaffold Get Stack](sub-features/scaffold_get_stack/concept.md)
- [Scaffold Validate Name](sub-features/scaffold_validate_name/concept.md)
- [Scaffold List Licenses](sub-features/scaffold_list_licenses/concept.md)
- [Scaffold Generate](sub-features/scaffold_generate/concept.md)
- [Scaffold Make](sub-features/scaffold_make/concept.md)
- [Scaffold Create](sub-features/scaffold_create/concept.md)
