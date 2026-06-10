# Rename

> **Sub-Feature:** Rename
> **Action:** `rename`
> **Rating:** 5/5 (Essential) ⭐⭐⭐⭐⭐

## Purpose

Semantic rename of a symbol (class, function, method) across the entire codebase using Tree-Sitter AST parsing. Skips strings, comments, and template strings to avoid false positives.

## Why This Exists

- **AI Autonomy:** AI can fix naming conventions without manual tracking
- **Semantic Safety:** Tree-Sitter ensures only symbol references are renamed
- **Multi-Language:** Supports 16 languages with semantic understanding
- **Zero Manual Tracking:** No need to manually find and replace across files

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_id` | string | ✅ | — | Repository UUID |
| `target_symbol` | string | ✅ | — | Symbol to rename (format: `file::symbol`) |
| `changes.new_name` | string | ✅ | — | New symbol name |
| `dry_run` | bool | ❌ | `true` | Preview without applying |

## Output

```json
{
  "status": "preview",
  "message": "Rename plan: 3 file(s)",
  "changes": [
    {
      "path": "src/utils.py",
      "action": "modify",
      "description": "Rename 'calculate_sum' → 'calculate_total'",
      "diff": "--- a/src/utils.py\n+++ b/src/utils.py\n@@ -10,7 +10,7 @@\n-def calculate_sum(a, b):\n+def calculate_total(a, b):\n     return a + b"
    }
  ],
  "blast_radius": {
    "total_files": 3,
    "direct_dependents": 3,
    "confidence_score": 100
  }
}
```

## Language Support

| Language | Ext | Semantic Rename |
|----------|:---:|:---------------:|
| Python | `.py` | ✅ Tree-Sitter |
| JavaScript | `.js`, `.jsx` | ✅ skip strings/comments |
| TypeScript | `.ts` | ✅ skip strings/comments |
| TSX | `.tsx` | ✅ skip strings/comments |
| Go | `.go` | ✅ skip string/comment |
| Rust | `.rs` | ✅ skip string/comment |
| Java | `.java` | ✅ skip string/comment |
| Kotlin | `.kt`, `.kts` | ✅ skip string/comment |
| C# | `.cs` | ✅ skip string/comment |
| C++ | `.cpp`, `.hpp`, `.cc` | ✅ skip string/comment |
| C | `.c`, `.h` | ✅ skip string/comment |
| PHP | `.php` | ✅ skip string/comment |
| Ruby | `.rb` | ✅ skip string/comment |
| Swift | `.swift` | ✅ skip string/comment |
| Dart | `.dart` | ✅ skip string/comment |

## Algorithm

1. Parse target file with Tree-Sitter for target language
2. Find symbol node (class, function, method) by name
3. Generate language-specific query for symbol references
4. Execute query across all files in repository
5. Replace symbol references (skipping strings/comments)
6. Generate unified diff for each affected file
7. Return blast radius with direct + transitive callers

## Use Case

AI agents can fix naming conventions (PascalCase classes, snake_case functions) across the entire codebase with zero manual tracking.
