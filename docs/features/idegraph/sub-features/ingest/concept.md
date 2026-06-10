# Ingest

**Purpose:** Run all 16 IDE parsers to harvest AI interaction data and persist to SQLite

**Why It Exists:** AI coders work across multiple IDEs — ingestion unifies all interactions into a single searchable memory graph

**Parameters:**
None (runs all parsers automatically)

**Output Format:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Ingestion completed",
  "data": {
    "output_path": "/outputs/sidecortex_ingest_20260529_100000.jsonl",
    "summary": {
      "total_engrams": 150,
      "breakdown": {
        "by_ide": {
          "cursor": 50,
          "trae": 30,
          "claude": 40,
          "gemini": 30
        },
        "by_type": {
          "vscode-extension": 120,
          "desktop": 30
        }
      },
      "total_messages": 1200
    },
    "storage": {
      "total_conversations": 150,
      "total_messages": 1200,
      "failed_runs": 0
    }
  }
}
```

**Algorithm:**
1. Initialize all 16 IDE parsers
2. Run each parser to extract conversation data
3. Deduplicate engrams by ID
4. Resolve project names from file paths
5. Persist to SQLite with workspace grouping
6. Harvest IDE configs, settings, and extensions
7. Export to JSONL for backup

**Use Case:** Initial setup or periodic refresh to ensure all IDE conversations are indexed and searchable
