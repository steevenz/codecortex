# KnowledgeGraph Domain - Test Cases

**Date:** 2026-05-29  
**Domain:** KnowledgeGraph  
**Scope:** 1 MCP tool (4 actions) + 4 CLI commands

---

## Test Case Matrix

### MCP Tool: knowledge_graph

#### Action: extract

| Scenario ID | Description | Parameters | Expected Status | Expected Output |
|-------------|-------------|------------|----------------|-----------------|
| 1.1 | Basic extraction from valid repo | action=extract, repo_path=/valid/path | 200 | chunks_extracted > 0, by_type populated |
| 1.2 | Extraction with type filter | action=extract, repo_path=/valid/path, knowledge_types=[constraint, decision] | 200 | only constraint and decision types extracted |
| 1.3 | Extraction from non-existent path | action=extract, repo_path=/invalid/path | 404 | error_code=KG_002 |
| 1.4 | Extraction without repo_path | action=extract | 400 | error_code=KG_001 |
| 1.5 | Extraction from empty repo | action=extract, repo_path=/empty/path | 200 | chunks_extracted=0, summary="no knowledge extracted" |
| 1.6 | Extraction from repo with only code files | action=extract, repo_path=/code-only/path | 200 | chunks_extracted=0, documents_scanned=0 |
| 1.7 | Extraction from repo with mixed docs | action=extract, repo_path=/mixed/path | 200 | chunks_extracted > 0, multiple types in by_type |
| 1.8 | Extraction with all 8 types | action=extract, repo_path=/full/path | 200 | all 8 types present in by_type |
| 1.9 | Extraction with large repo (100+ docs) | action=extract, repo_path=/large/path | 200 | documents_scanned > 100, reasonable time |
| 1.10 | Extraction with nested docs | action=extract, repo_path=/nested/path, max_depth=5 | 200 | documents_scanned includes nested docs |

#### Action: query

| Scenario ID | Description | Parameters | Expected Status | Expected Output |
|-------------|-------------|------------|----------------|-----------------|
| 2.1 | Basic query with task | action=query, task="payment processing" | 200 | chunks[], total > 0 |
| 2.2 | Query with type filter | action=query, task="payment", knowledge_types=[constraint] | 200 | only constraint type chunks |
| 2.3 | Query with min_importance | action=query, task="payment", min_importance=0.7 | 200 | all chunks have importance_score >= 0.7 |
| 2.4 | Query with limit | action=query, task="payment", limit=5 | 200 | total <= 5 |
| 2.5 | Query without task | action=query | 400 | error_code=KG_003 |
| 2.6 | Query with no results | action=query, task="nonexistent topic" | 200 | total=0, chunks=[] |
| 2.7 | Query with source_file filter | action=query, task="payment", source_file="docs/arch.md" | 200 | chunks from specific file only |
| 2.8 | Query with max limit (200) | action=query, task="payment", limit=200 | 200 | total <= 200 |
| 2.9 | Query with limit > 200 | action=query, task="payment", limit=300 | 200 | limit capped to 200 |
| 2.10 | Query with complex task description | action=query, task="how to handle database constraints in payment service" | 200 | relevant chunks ranked by relevance |

#### Action: status

| Scenario ID | Description | Parameters | Expected Status | Expected Output |
|-------------|-------------|------------|----------------|-----------------|
| 3.1 | Status with data | action=status | 200 | total_chunks > 0, by_type populated |
| 3.2 | Status with no data | action=status | 200 | total_chunks=0, by_type empty |
| 3.3 | Status with repo_path filter | action=status, repo_path=/specific/path | 200 | filtered by repo (if implemented) |
| 3.4 | Status after extraction | action=status (after extract) | 200 | total_chunks matches extraction count |
| 3.5 | Status with multiple types | action=status | 200 | by_type has multiple entries |

#### Action: relationships

| Scenario ID | Description | Parameters | Expected Status | Expected Output |
|-------------|-------------|------------|----------------|-----------------|
| 4.1 | All relationships | action=relationships | 200 | edges[], total > 0 |
| 4.2 | Relationships with focus | action=relationships, focus="payment" | 200 | edges related to payment topic |
| 4.3 | Relationships with no data | action=relationships (no chunks) | 200 | total=0, edges=[] |
| 4.4 | Relationships with limit | action=relationships, limit=10 | 200 | total <= 10 |
| 4.5 | Relationships with invalid focus | action=relationships, focus="nonexistent" | 200 | total=0, edges=[] |
| 4.6 | Relationships after extraction | action=relationships (after extract) | 200 | edges built from extracted chunks |
| 4.7 | Relationships with specific relation type | action=relationships (filter by type) | 200 | edges of specific type (if implemented) |

#### Error Cases

| Scenario ID | Description | Parameters | Expected Status | Expected Output |
|-------------|-------------|------------|----------------|-----------------|
| 5.1 | Invalid action | action=invalid | 400 | error_code=KG_004 |
| 5.2 | Database connection error | any action (with DB down) | 500 | error_code=KG_500 |
| 5.3 | Malformed repo_path | action=extract, repo_path="malformed:::path" | 404/500 | error_code=KG_002 or KG_500 |

---

### CLI Commands

#### Command: kg extract

| Scenario ID | Description | Arguments | Expected Status | Expected Output |
|-------------|-------------|-----------|----------------|-----------------|
| 6.1 | Basic extraction | kg extract /valid/path | success | chunks_extracted > 0 |
| 6.2 | Extraction with types | kg extract /valid/path --types constraint decision | success | only specified types extracted |
| 6.3 | Extraction from invalid path | kg extract /invalid/path | error | KG_PATH_ERROR |
| 6.4 | Extraction without path | kg extract | error | argparse error |
| 6.5 | Extraction with all types | kg extract /valid/path --types concept constraint decision flow risk invariant anti_pattern principle | success | all 8 types extracted |

#### Command: kg query

| Scenario ID | Description | Arguments | Expected Status | Expected Output |
|-------------|-------------|-----------|----------------|-----------------|
| 7.1 | Basic query | kg query "payment processing" | success | chunks[], total > 0 |
| 7.2 | Query with types | kg query "payment" --types constraint | success | only constraint type chunks |
| 7.3 | Query with min_importance | kg query "payment" --min-importance 0.7 | success | all chunks have importance_score >= 0.7 |
| 7.4 | Query with limit | kg query "payment" --limit 5 | success | total <= 5 |
| 7.5 | Query without task | kg query | error | argparse error |
| 7.6 | Query with no results | kg query "nonexistent topic" | success | total=0 |

#### Command: kg status

| Scenario ID | Description | Arguments | Expected Status | Expected Output |
|-------------|-------------|-----------|----------------|-----------------|
| 8.1 | Status with data | kg status | success | total_chunks > 0 |
| 8.2 | Status with no data | kg status (before extraction) | success | total_chunks=0 |
| 8.3 | Status after extraction | kg status (after extract) | success | total_chunks matches extraction |

#### Command: kg relationships

| Scenario ID | Description | Arguments | Expected Status | Expected Output |
|-------------|-------------|-----------|----------------|-----------------|
| 9.1 | All relationships | kg relationships | success | edges[], total > 0 |
| 9.2 | Relationships with focus | kg relationships --focus payment | success | edges related to payment |
| 9.3 | Relationships with no data | kg relationships (no chunks) | success | total=0 |
| 9.4 | Relationships after extraction | kg relationships (after extract) | success | edges built from chunks |

---

## Integration Scenarios

| Scenario ID | Description | Steps | Expected Outcome |
|-------------|-------------|-------|------------------|
| 10.1 | Extract → Query workflow | 1. Extract from repo<br>2. Query with task | Query returns chunks from extracted knowledge |
| 10.2 | Extract → Status workflow | 1. Extract from repo<br>2. Check status | Status shows extraction coverage |
| 10.3 | Extract → Relationships workflow | 1. Extract from repo<br>2. Get relationships | Relationships built from extracted chunks |
| 10.4 | Full pipeline | 1. Extract<br>2. Status<br>3. Query<br>4. Relationships | All actions work in sequence |
| 10.5 | Incremental extraction | 1. Extract from repo<br>2. Add new doc<br>3. Extract again | New chunks added, old chunks preserved (idempotent) |
| 10.6 | Cross-tool integration | 1. Extract knowledge<br>2. Use code_search to find related code | Knowledge and code linked via related_module |

---

## Edge Cases

| Scenario ID | Description | Parameters | Expected Behavior |
|-------------|-------------|------------|-------------------|
| 11.1 | Very long content (>1000 chars) | action=extract with long doc | Content truncated to 1000 chars |
| 11.2 | Very long title (>80 chars) | action=extract with long title | Title truncated in to_dict() |
| 11.3 | Many concepts (>5) | action=extract with concept-rich doc | Concepts truncated to 5 in to_dict() |
| 11.4 | Many modules (>3) | action=extract with module-rich doc | Modules truncated to 3 in to_dict() |
| 11.5 | Many tags (>5) | action=extract with tag-rich doc | Tags truncated to 5 in to_dict() |
| 11.6 | Special characters in content | action=extract with special chars | Content cleaned, markdown artifacts removed |
| 11.7 | Empty document | action=extract with empty md file | No chunks extracted |
| 11.8 | Document with only headers | action=extract with headers only | No chunks extracted (no content) |
| 11.9 | Document with malformed markdown | action=extract with malformed md | Extracts what it can, no crash |
| 11.10 | Concurrent extractions | Multiple extract actions | Thread-safe, no data corruption |

---

## Performance Scenarios

| Scenario ID | Description | Parameters | Expected Performance |
|-------------|-------------|------------|---------------------|
| 12.1 | Large repo extraction (1000 docs) | action=extract, repo_path=/large/path | Completes in < 30s |
| 12.2 | Query with many results | action=query, task="common term", limit=200 | Returns in < 1s |
| 12.3 | Relationship graph with many edges | action=relationships (1000+ chunks) | Returns in < 2s |
| 12.4 | Status with large dataset | action=status (10000+ chunks) | Returns in < 1s |
| 12.5 | Batch extraction | Multiple extract calls | No memory leak, handles gracefully |

---

## Security Scenarios

| Scenario ID | Description | Parameters | Expected Behavior |
|-------------|-------------|------------|-------------------|
| 13.1 | Path traversal attempt | action=extract, repo_path=../../../etc/passwd | Path validation, 404 or error |
| 13.2 | SQL injection in task | action=query, task="'; DROP TABLE knowledge_chunks--" | Sanitized, no SQL injection |
| 13.3 | XSS in content | action=extract with malicious content | Content sanitized, stored safely |
| 13.4 | Large payload DoS | action=extract with 10GB file | File size check, rejected |
| 13.5 | Unicode in paths | action=extract, repo_path=/path/with/üñïcödé | Handles correctly |

---

## Test Summary

**Total Test Scenarios:** 50+

**Breakdown:**
- MCP Tool extract: 10 scenarios
- MCP Tool query: 10 scenarios
- MCP Tool status: 5 scenarios
- MCP Tool relationships: 7 scenarios
- MCP Tool error cases: 3 scenarios
- CLI extract: 5 scenarios
- CLI query: 6 scenarios
- CLI status: 3 scenarios
- CLI relationships: 4 scenarios
- Integration: 6 scenarios
- Edge cases: 10 scenarios
- Performance: 5 scenarios
- Security: 5 scenarios

**Coverage Goals:**
- Minimum: 20 critical scenarios
- Ideal: All 50+ scenarios
- Production readiness: 80% pass rate required
