# Search

**Purpose:** Advanced search for ingested AI conversation memories with keyword, glob, regex, fuzzy, boolean, and multi-field capabilities

**Why It Exists:** AI coders need to quickly find previous conversations across multiple IDEs and projects. Basic keyword search is insufficient — they need pattern matching, approximate matching, and the ability to search specific fields like code blocks, diffs, and file paths.

## Search Modes

| Mode | Prefix/Syntax | Example | Use Case |
|------|--------------|---------|----------|
| **Keyword** (default) | plain text | `authentication` | Simple substring match |
| **Glob** | `*` `?` `[]` | `*.py`, `src/**` | Match file paths by pattern |
| **Regex** | `/pattern/flags` | `/auth.* /i` | Complex pattern matching |
| **Fuzzy** | `~word~` | `~auth~` | Approximate spelling match |
| **Boolean** | `AND` `OR` `NOT` | `auth AND oauth NOT facebook` | Combine/exclude terms |
| **Field Prefix** | `field:` | `title:auth`, `code:def validate` | Search specific fields |

## Search Fields

| Field | Searches | Example Query |
|-------|---------|---------------|
| `all` (default) | Title, content, code, diffs, tools, source, project | `authentication` |
| `title` | Conversation title only | `title:auth bug` |
| `content` | Message content only | `content:JWT token` |
| `code` | Code blocks in messages | `code:def validate` |
| `diffs` | Code diffs in messages | `diffs:+import` |
| `tools` | Tool use in messages | `tools:file_read` |
| `source` | Source file path | `source:*.py` |
| `project` | Project name/path | `project:myapp` |

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | ✅ | — | Search query (auto-detects mode) |
| `project_name` | string | ❌ | — | Filter by project name |
| `ide_name` | string | ❌ | — | Filter by IDE name |
| `workspace_key` | string | ❌ | — | Filter by workspace key |
| `search_mode` | string | ❌ | `keyword` | Force mode: keyword, glob, regex, fuzzy, boolean |
| `search_fields` | string | ❌ | `all` | Comma-separated fields to search |
| `date_from` | ISO timestamp | ❌ | — | Filter: created after this time |
| `date_to` | ISO timestamp | ❌ | — | Filter: created before this time |
| `min_messages` | int | ❌ | — | Filter: minimum message count |
| `max_messages` | int | ❌ | — | Filter: maximum message count |
| `limit` | int | ❌ | `20` | Max results (max 200) |

## Output Format (Enhanced)

```json
{
  "success": true,
  "status_code": 200,
  "message": "Found 5 matches",
  "data": {
    "items": [{
      "id": "engram-123",
      "title": "Fix authentication bug",
      "source": "cursor",
      "project_name": "my-project",
      "workspace_key": "abc123...",
      "created_at": "2026-05-29T10:00:00Z",
      "score": 0.92,
      "matched_fields": ["title", "content"],
      "snippets": [
        "...Fix JWT authentication bug in auth.py..."
      ]
    }],
    "count": 5,
    "search_mode": "keyword",
    "query": "authentication"
  }
}
```

## Algorithm

1. **Mode Detection:** Auto-detect search mode from query syntax
2. **Candidate Fetch:** Query SQLite with project/IDE/date filters
3. **Field Extraction:** Extract searchable text per field from each engram
4. **Matching:** Apply mode-specific matcher (LIKE, fnmatch, regex, fuzzy, boolean)
5. **Scoring:** Score based on match count and field relevance
6. **Filtering:** Apply date range, message count, artifact filters
7. **Ranking:** Sort by score descending, return top N

## CLI Examples

```bash
# Basic keyword search
codecortex ig search "authentication" --project myapp --limit 10

# Glob pattern for file paths
codecortex ig search "*.py" --search-mode glob --search-fields source

# Regex for complex patterns
codecortex ig search "/def validate.*/" --search-mode regex --search-fields code

# Fuzzy match for approximate spelling
codecortex ig search "~authentification~" --search-mode fuzzy

# Boolean operators
codecortex ig search "auth AND oauth NOT facebook" --search-mode boolean

# Search specific field
codecortex ig search "title:JWT" --search-fields title

# Date range + message count
codecortex ig search "bug" --date-from 2026-05-01 --date-to 2026-05-29 --min-messages 5

# Combine: code search in specific project
codecortex ig search "code:def validate" --project myapp --search-fields code
```

## Use Cases

- **Find previous auth work:** `auth` → finds all conversations mentioning auth
- **Find Python files:** `*.py` (glob) → conversations about Python files
- **Find specific function:** `code:def validate` → where validate was discussed
- **Find recent bugs:** `bug` --date-from 2026-05-20 → recent bug fixes
- **Exclude unrelated:** `auth NOT facebook` → auth without Facebook OAuth
- **Find long discussions:** `design` --min-messages 20 → substantial design talks
