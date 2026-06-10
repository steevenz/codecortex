# Harvest

**Purpose:** Automatically discover and harvest IDE configurations, settings, and extensions

**Why It Exists:** AI coders need to understand their IDE setup across multiple tools — harvesting provides a complete inventory

**Parameters:**
None (automatically discovers all IDE installations)

**Output Format:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Harvest completed",
  "data": {
    "ides": 4,
    "configs": 12,
    "extensions": 45,
    "settings": 8
  }
}
```

**Algorithm:**
1. Run all 16 IDE parsers to find installations
2. For each IDE, harvest:
   - Configurations (settings.json, keybindings.json)
   - Extensions (installed extensions list)
   - Settings (workspace-specific settings)
3. Persist to SQLite with IDE metadata
4. Return harvest statistics

**Use Case:** Create a complete inventory of IDE configurations and extensions for backup or migration
