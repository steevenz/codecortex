# Scaffold List Stacks

**Purpose:** List all available technology stacks for project scaffolding.

**Why This Exists:** Enables AI coders to discover available stacks, their file conventions, and supported project types before scaffolding.

**Parameters:** None

**Output Format:**
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

**Algorithm:**
1. Scan `datasets/templates/*/manifest.yml` for stack definitions
2. Parse each manifest.yml to extract stack metadata
3. Return list of stacks with display names, versions, and conventions

**Use Case:** AI coder needs to discover available stacks before calling `scaffold_create` or `scaffold_make`.
