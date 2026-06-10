# KnowledgeGraph Domain - DTO Value Analysis

**Date:** 2026-05-29  
**Domain:** KnowledgeGraph  
**Purpose:** Assess JSON output (DTOs) for AI coder value

---

## DTO Analysis: KnowledgeChunk

### Fields

| Field | Type | AI Value | Justification |
|-------|------|----------|---------------|
| `id` | string | High | Unique identifier for chunk tracking and deduplication |
| `knowledge_type` | string | High | Enables AI to filter by knowledge type (constraint, decision, risk, etc.) |
| `type_label` | string | Medium | Human-readable type description for display |
| `title` | string | High | Concise summary for quick scanning and relevance assessment |
| `content` | string | High | Full extracted knowledge content for detailed understanding |
| `summary` | string | High | Truncated summary for token-efficient context injection |
| `source_file` | string | High | Enables AI to locate original documentation for verification |
| `doc_type` | string | Medium | Document type (ADR, PRD, README) for context weighting |
| `section_path` | string | Medium | Section location within document for navigation |
| `importance_score` | float | High | Composite score for prioritization (0.0-1.0) |
| `criticality` | string | High | Business impact level (high/medium/low) for risk assessment |
| `concept` | list | High | Extracted domain concepts for semantic matching |
| `related_module` | list | High | Module path references for code-knowledge linkage |
| `related_features` | list | Medium | Feature references for cross-feature impact analysis |
| `architecture_tag` | list | High | Architecture tags (security, performance, data) for categorization |
| `line_start` | int | Low | Line number for source location (limited AI value) |
| `line_end` | int | Low | Line number for source location (limited AI value) |
| `embedding` | list | Medium | Vector embedding for semantic similarity (future use) |

### Summary

**Overall Value Assessment:** 9/10 (Excellent)

**Strengths:**
- Rich metadata for AI decision-making (importance_score, criticality, architecture_tag)
- Strong code-knowledge linkage (related_module, concept)
- Source attribution (source_file, doc_type) for verification
- Truncated fields (summary, content[:300]) for token efficiency
- Type-based categorization (knowledge_type, type_label)

**Weaknesses:**
- `line_start`/`line_end` have limited AI value (navigation only)
- `embedding` field exists but not actively used
- `related_features` field exists but underutilized

**Recommendations:**
- Keep all current fields (high value for AI context)
- Consider removing `line_start`/`line_end` from to_dict() if token budget is tight
- Activate `embedding` field for semantic search enhancement
- Expand `related_features` extraction for better cross-feature analysis

---

## DTO Analysis: DocRelationship

### Fields

| Field | Type | AI Value | Justification |
|-------|------|----------|---------------|
| `source_id` | string | High | Source chunk identifier for graph traversal |
| `target_id` | string | High | Target chunk/module identifier for graph traversal |
| `relation_type` | string | High | Relationship type (introduces, refines, violates) for semantic understanding |
| `weight` | float | Medium | Confidence score for relationship strength |
| `description` | string | High | Human-readable edge description for explanation |

### Summary

**Overall Value Assessment:** 8/10 (Very Good)

**Strengths:**
- Clear relationship typing (introduces, refines, violates, affects, references)
- Weighted edges for confidence scoring
- Descriptive edges for AI explanation generation
- Enables graph traversal for impact analysis

**Weaknesses:**
- No temporal information (when relationship was established)
- No bidirectional relationship metadata

**Recommendations:**
- Keep all current fields (good for graph-based reasoning)
- Consider adding `created_at` for temporal analysis if needed
- Consider adding `bidirectional` flag for symmetric relationships

---

## DTO Analysis: Query Response

### Fields

| Field | Type | AI Value | Justification |
|-------|------|----------|---------------|
| `total` | int | High | Total results count for pagination and result assessment |
| `chunks` | list | High | Ranked knowledge chunks for task relevance |
| `types_available` | dict | Medium | Available knowledge types for filter selection |
| `query` | dict | Medium | Query metadata for result interpretation |

### Summary

**Overall Value Assessment:** 8/10 (Very Good)

**Strengths:**
- Ranked results (by importance_score + task relevance)
- Type availability for filter refinement
- Query metadata for result interpretation
- Paginated structure (limit parameter)

**Weaknesses:**
- No pagination cursor (next_cursor missing)
- No relevance scores per chunk in response
- No query explanation (why these chunks matched)

**Recommendations:**
- Add `next_cursor` for pagination
- Add `relevance_score` per chunk for transparency
- Add `query_explanation` for AI decision justification

---

## DTO Analysis: Extraction Response

### Fields

| Field | Type | AI Value | Justification |
|-------|------|----------|---------------|
| `documents_scanned` | int | Medium | Scan coverage metric for quality assessment |
| `chunks_extracted` | int | High | Extraction count for result evaluation |
| `relationships_built` | int | Medium | Graph density metric for relationship analysis |
| `by_type` | dict | High | Type distribution for knowledge balance assessment |
| `summary` | string | High | Human-readable summary for quick status check |
| `sources` | list | High | Source file list for coverage verification |

### Summary

**Overall Value Assessment:** 9/10 (Excellent)

**Strengths:**
- Comprehensive extraction metrics
- Type distribution for knowledge balance
- Source attribution for coverage verification
- Human-readable summary for quick status

**Weaknesses:**
- No extraction time metric
- No failed documents count
- No extraction confidence metrics

**Recommendations:**
- Add `extraction_time_ms` for performance monitoring
- Add `failed_documents` count for quality assessment
- Add `avg_confidence` metric for extraction quality

---

## DTO Analysis: Status Response

### Fields

| Field | Type | AI Value | Justification |
|-------|------|----------|---------------|
| `total_chunks` | int | High | Total knowledge count for coverage assessment |
| `by_type` | dict | High | Type distribution for knowledge balance |
| `sources` | list | High | Source file list for coverage verification |

### Summary

**Overall Value Assessment:** 8/10 (Very Good)

**Strengths:**
- Simple and focused
- Type distribution for balance assessment
- Source attribution for coverage verification

**Weaknesses:**
- No last extraction timestamp
- No extraction confidence metrics
- No relationship count

**Recommendations:**
- Add `last_extracted_at` for freshness assessment
- Add `relationship_count` for graph density
- Add `avg_importance_score` for quality assessment

---

## DTO Analysis: Relationships Response

### Fields

| Field | Type | AI Value | Justification |
|-------|------|----------|---------------|
| `nodes` | list | High | Knowledge nodes for graph visualization |
| `edges` | list | High | Relationship edges for graph traversal |
| `total` | int | Medium | Total edges count for graph density |
| `focus` | string | Medium | Focus topic for subgraph context |

### Summary

**Overall Value Assessment:** 8/10 (Very Good)

**Strengths:**
- Graph structure (nodes + edges) for visualization
- Focus-based subgraph for targeted analysis
- Weighted edges for confidence assessment

**Weaknesses:**
- No node metadata in edges response
- No edge direction indicators
- No graph statistics (density, centrality)

**Recommendations:**
- Add node metadata to edges response
- Add `direction` field for edge direction
- Add graph statistics (density, centrality) for analysis

---

## Overall DTO Value Assessment

### Summary

**Domain DTO Value:** 8.5/10 (Very Good)

**Key Strengths:**
1. Rich metadata for AI decision-making (importance_score, criticality, architecture_tag)
2. Strong code-knowledge linkage (related_module, concept)
3. Source attribution (source_file, doc_type) for verification
4. Type-based categorization (knowledge_type, type_label)
5. Graph structure for relationship analysis

**Key Weaknesses:**
1. Missing pagination cursors (next_cursor)
2. Missing relevance scores in query response
3. Missing temporal information (created_at, last_extracted_at)
4. Limited graph statistics
5. Some low-value fields (line_start, line_end)

**Token Efficiency:**
- Good use of truncated fields (content[:300], summary[:200])
- Limited list slicing (concept[:5], related_module[:5])
- Could improve by removing low-value fields from to_dict()

**AI Coder Actionability:**
- High: Can prioritize by importance_score and criticality
- High: Can filter by knowledge_type and architecture_tag
- High: Can trace to source files for verification
- Medium: Can traverse relationships for impact analysis
- Low: Limited graph statistics for complex analysis

**Recommendations:**
1. Add pagination cursors for large result sets
2. Add relevance scores to query response
3. Add temporal information for freshness assessment
4. Add graph statistics for relationship analysis
5. Consider removing low-value fields (line_start, line_end) from to_dict()
6. Activate embedding field for semantic search
