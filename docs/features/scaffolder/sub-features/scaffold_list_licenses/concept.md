# Scaffold List Licenses

**Purpose:** List all available license types for generated projects.

**Why This Exists:** Enables AI coders to discover available license options before scaffolding.

**Parameters:** None

**Output Format:**
```json
{
  "licenses": [
    {"id": "MIT", "name": "Mit"},
    {"id": "Apache-2.0", "name": "Apache 2.0"},
    {"id": "GPL-3.0", "name": "Gpl 3.0"},
    {"id": "BSD-3-Clause", "name": "Bsd 3 Clause"},
    {"id": "Commercial-Company", "name": "Commercial Company"},
    {"id": "Commercial-Personal", "name": "Commercial Personal"},
    {"id": "Private-Company", "name": "Private Company"},
    {"id": "Private-Personal", "name": "Private Personal"},
    {"id": "None", "name": "None"}
  ]
}
```

**Algorithm:**
1. Return all enum values from LicenseIdentifier
2. Format enum names as human-readable titles

**Use Case:** AI coder needs to discover available license options before calling `scaffold_create`.
