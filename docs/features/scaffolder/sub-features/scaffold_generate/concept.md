# Scaffold Generate

**Purpose:** Generate a single scaffold content file (preview without writing to disk).

**Why This Exists:** Enables AI coders to preview boilerplate content (gitignore, pyproject, Dockerfile, etc.) before generating full projects.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file_type` | string | ✅ | — | Type of content (gitignore, env, pyproject, readme, requirements, dockerfile, docker_compose, setup_sh, setup_bat, setup_ps1, logger_py, author_file, ai_ignore) |
| `project_category` | string | ❌ | `standard` | Project category (standard, data_science, web_api, cli_tool, automation) |
| `project_name` | string | ❌ | `My Project` | Project display name |
| `author` | string | ❌ | `Author` | Author name |
| `email` | string | ❌ | `author@example.com` | Author email |
| `license_name` | string | ❌ | `MIT` | License string |

**Output Format:**
```json
{
  "filename": ".gitignore",
  "content": "# Python byte-compiled...\n__pycache__/\n...",
  "content_length": 1234
}
```

**Algorithm:**
1. Map file_type to generator function
2. Call generator with provided parameters
3. Return filename and generated content

**Use Case:** AI coder needs to preview boilerplate content before including it in a project scaffold.
