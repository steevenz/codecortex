# Scaffold Validate Name

**Purpose:** Validate and normalize a project name.

**Why This Exists:** Ensures project names follow naming conventions and provides normalized forms (display, slug, snake, pascal) for scaffolding.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | ✅ | — | Raw project name to validate |

**Output Format:**
```json
{
  "display": "My Project",
  "slug": "my-project",
  "snake": "my_project",
  "pascal": "MyProject"
}
```

**Algorithm:**
1. Validate name length (min 2 characters)
2. Validate alphanumeric characters
3. Validate snake_case derivation is valid Python identifier
4. Generate display (Title Case), slug (kebab-case), snake (snake_case), pascal (PascalCase) forms

**Use Case:** AI coder needs to validate user-provided project names and get normalized forms for file/directory naming.
