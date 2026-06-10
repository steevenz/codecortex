# Scaffold Create

**Purpose:** Create a full project scaffold — directories, templates, license, and metadata.

**Why This Exists:** Enables AI coders to generate complete project structures with 33+ directories, templates, and proper file headers in a single operation.

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

**Output Format:**
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

**Algorithm:**
1. Validate project name and normalize to display/slug/snake/pascal forms
2. Resolve stack and project type from manifest.yml
3. Build template context with 20+ Jinja2 variables
4. Create 33+ standard directories
5. Render shared templates (_shared/*.j2)
6. Render stack templates ({stack}/**/*.j2)
7. Render type-specific templates ({stack}/types/{type}/**/*.j2)
8. Write .version, LICENSE, __init__.py files
9. Prepend @project headers on code files
10. Return progress messages

**Use Case:** AI coder needs to generate complete project structures with proper directories, templates, and file headers.
