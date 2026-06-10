# Scaffold Make

**Purpose:** Generate a class file for any of the 34 Decision Matrix types (28 code types + 6 documentation types).

**Why This Exists:** Enables AI coders to generate properly structured class files (interfaces, repositories, services, DTOs, etc.) and documentation files (drafts, planning, concepts, features, sub-features, AI impact analysis) with correct naming conventions and file headers per ~/.aicoders/docs/standards/documentation.md.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | ✅ | — | Class type (28 code types: interface, abstract, model, repository, controller, service, value_object, dto, event, listener, job, middleware, factory, seeder, migration, enum, trait, helper, validator, mapper, command, presenter, view_model, filter, exception, provider, observer, strategy; 6 documentation types: doc_draft, doc_planning, doc_concept, doc_feature, doc_subfeature, doc_ai_impact) |
| `name` | string | ✅ | — | Domain concept name (e.g., "User", "Order", "Payment") |
| `stack` | string | ❌ | `python` | Technology stack (python, typescript, javascript, php, go, java, kotlin, csharp, swift, rust, cpp, dart, flutter) |
| `module` | string | ❌ | — | Optional module context for DDD projects |
| `project_name` | string | ❌ | `Project` | Project name for file headers |
| `author` | string | ❌ | `Author` | Author name for file headers |
| `target_path` | string | ❌ | — | Absolute path to write file |
| `overwrite` | bool | ❌ | `false` | Overwrite existing files |

**Output Format:**
```json
{
  "type": "repository",
  "type_display": "Repository",
  "stack": "python",
  "class_name": "UserRepository",
  "file_name": "user_repository.py",
  "relative_path": "repositories/user_repository.py",
  "absolute_path": "/path/to/repositories/user_repository.py",
  "content": "# @project...\nclass UserRepository:\n    ...",
  "content_length": 456,
  "written": true
}
```

**Algorithm:**
1. Validate type and stack
2. Map type to folder location and parent class
3. Generate class name from domain concept
4. Apply stack-specific naming conventions
5. Generate file header with @project metadata
6. For documentation types: generate content per ~/.aicoders/docs/standards/documentation.md
7. For code types: generate class code with proper structure
8. Write to target_path if provided

**Use Case:** AI coder needs to generate class files with proper structure and naming conventions, or generate documentation files (drafts, planning, concepts, features, sub-features, AI impact analysis) following the documentation standard.
