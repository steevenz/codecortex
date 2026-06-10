# Extract Action

**Purpose:** Extract engineering knowledge from documentation (PRDs, ADRs, READMEs, architecture guides)

## Why It Exists

Extracts 8 types of engineering knowledge from documentation using pattern-based extraction (no LLM dependency).

**Supported file formats:**
- **Text/Markup:** `.md`, `.rst`, `.txt`, `.adoc`
- **Structured Text:** `.csv`, `.json`, `.log`
- **Word:** `.docx`
- **PDF:** `.pdf`
- **Excel:** `.xlsx`, `.xls`
- **PowerPoint:** `.pptx`, `.ppt`

All formats are normalized to markdown-like text before knowledge extraction. This surfaces tribal knowledge buried in documentation that AI coders need for context-aware code generation.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be "extract" |
| `repo_path` | string | ✅ | — | Repository root path to scan |
| `repo_id` | string | ❌ | `null` | Repository identifier for tracking |
| `knowledge_types` | list | ❌ | `null` | Limit to specific types (concept, constraint, decision, flow, risk, invariant, anti_pattern, principle) |

## Output Format

```json
{
  "success": true,
  "status_code": 200,
  "message": "Extracted 47 knowledge chunks from 12 docs",
  "data": {
    "documents_scanned": 12,
    "chunks_extracted": 47,
    "relationships_built": 89,
    "by_type": {
      "concept": 12,
      "constraint": 8,
      "decision": 6,
      "flow": 5,
      "risk": 4,
      "invariant": 3,
      "anti_pattern": 2,
      "principle": 7
    },
    "avg_confidence": 0.78,
    "summary": "12 concepts, 8 constraints, 6 decisions, 5 flows, 4 risks, 3 invariants, 2 anti-patterns, 7 principles",
    "sources": [
      "docs/architecture/adr-001.md",
      "docs/architecture/adr-002.md",
      "docs/guides/payment-flow.md",
      "README.md"
    ],
    "repo_id": "my-repo"
  }
}
```

## Algorithm

1. **Document Discovery:** Uses `DocumentParser.scan_directory()` to discover supported files (max_depth=5)
   - Scans: `docs/`, `doc/`, `documentation/`, `adr/`, `specs/`, `proposals/`, `rfcs/`, `design/`, `wiki/`, root
   - Supports: `.md`, `.rst`, `.txt`, `.adoc`, `.csv`, `.json`, `.log`, `.docx`, `.pdf`, `.xlsx`, `.xls`, `.pptx`, `.ppt`
2. **Incremental Check:** Computes SHA-256 hash of each file; skips unchanged files (tracked in extraction_log)
3. **Parallel Extraction:** Uses `ThreadPoolExecutor` for multi-document extraction (max_workers=4)
4. **Pattern Extraction:** Runs 8 type-specific regex extractors per document
5. **Inline Dedup:** Prevents duplicate extractions within the same document
6. **Scoring:** Applies 6-dimension importance scoring + confidence scoring
7. **Cross-Document Dedup:** Uses content fingerprint deduplication across all chunks
8. **Relationship Building:** Builds type-based edges (decision→constraint, principle→decision) and tag-based relationships
9. **Dual-Layer Storage:** Stores chunks in SQLite + high-importance chunks (score ≥ 0.6) to GoldenKnowledgeStore
10. **Repo Metadata:** Updates repo_metadata with extraction stats

## Use Case

**Scenario:** AI coder needs architectural context before refactoring payment service

**Workflow:**
1. Extract knowledge from docs/ directory
2. Query for "payment service constraints"
3. AI coder receives constraints, decisions, and risks related to payment service
4. AI coder applies constraints during refactoring

## Error Cases

| Error Code | Description |
|------------|-------------|
| KG_001 | repo_path required for extract |
| KG_002 | Path not found |
| KG_500 | Internal error |
