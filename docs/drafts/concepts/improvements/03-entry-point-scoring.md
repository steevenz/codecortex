# Entry Point Scoring

**Domain:** CodeGraph  
**Effort:** Medium | **Impact:** High | **Priority:** 3

## Current State
CodeCortex has no concept of "entry points." Analysis focuses on relationships (edges) but doesn't score which functions are architectural entry points. This limits:
- Process detection (needs entry points as roots)
- Architectural understanding (which functions drive behavior)
- Search ranking (entry points should rank higher)

## Proposed Improvement
Port GitNexus's `entry-point-scoring.ts` algorithm to Python. Scores functions 0–100 based on:
1. **Call Ratio (40%)**: callees / (callers + 1) — pure consumers score higher
2. **Export Status (20%)**: exported/public functions score higher
3. **Name Patterns (25%)**: Matches entry point regex patterns:
   - Universal: `handle*`, `on*`, `Controller$`, `main`, `init`, `bootstrap`
   - Utility penalty: `get*`, `set*`, `is*`, Helper$, Utils$
4. **Framework Detection (15%)**: Path-based detection for Next.js, Express, Django, etc.

## Architecture
```
score_entry_point(symbol, graph)
  ├── compute_call_ratio() → 0-0.4
  ├── check_export_status() → 0-0.2
  ├── match_name_patterns(language) → 0-0.25
  ├── detect_framework(path) → 0-0.15
  └── normalize_and_return() → {score: 0-100, reasons: [...]}
```

## Key Changes in CodeCortex
- **`src/domain/codegraph/application/`**: New `entry_point_scorer.py`  
- **CodeGraph analysis report**: Include top 10 entry points in output  
- **DB schema**: Add `is_entry_point` column to `symbols` table (migration)  
- **MCP Tool**: Add `analyze_entry_points(repo_id)` tool

## Dependencies
- Pure Python (no new deps)

## Effort Breakdown
- `entry_point_scorer.py`: ~150 lines  
- DB migration: ~10 lines  
- Edit analysis report: ~30 lines  
- Tests: ~80 lines  
- **Total: ~4 hours**
