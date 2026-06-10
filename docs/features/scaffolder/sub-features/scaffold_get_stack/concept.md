# Scaffold Get Stack

**Purpose:** Get detailed information for a specific technology stack.

**Why This Exists:** Enables AI coders to inspect stack details including file conventions, project types, and available templates before scaffolding.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `stack_name` | string | ✅ | — | Stack identifier (e.g., "python", "typescript") |

**Output Format:**
```json
{
  "stack": {
    "name": "python",
    "display_name": "Python",
    "version": "3.12",
    "file_conventions": {
      "directories": "snake_case",
      "modules": "snake_case.py",
      "classes": "PascalCase"
    },
    "project_types": [
      {
        "id": "standard",
        "display_name": "Standard",
        "description": "Standard Python project",
        "pattern": "layered"
      }
    ]
  }
}
```

**Algorithm:**
1. Load manifest.yml for the specified stack
2. Parse stack metadata, file conventions, and project types
3. Return detailed stack information

**Use Case:** AI coder needs to inspect stack details to choose the right project type and understand naming conventions.
