---
description: Comprehensive QA Fixing Harness for CodeCortex MCP Tools
---

# QA Fixing Harness Workflow

**Purpose:** Systematic quality assurance workflow for CodeCortex MCP tools and CLI commands  
**Scope:** Gap analysis, testing, fixes, documentation updates, and AI coder impact assessment  
**Reusable:** Applicable to any tool/domain in CodeCortex  
**Source of Truth:** Source code implementation

---

## Phase 1: Initial Assessment

### 1.1 Define Scope
- Identify target domain (e.g., coderepository, filesystem, codegraph)
- List all MCP tools in the domain
- List all CLI commands in the domain
- Set testing focus (MCP tools, CLI tools, or both)

### 1.2 Gather Documentation
- Read concept.md for the domain
- Read all tool-specific documentation files
- Read CLI documentation if applicable
- Note any cross-references or dependencies

### 1.3 Create TODO List
```yaml
- [ ] Documentation review complete
- [ ] Source code analysis complete
- [ ] Gap analysis complete
- [ ] JSON output review complete
- [ ] Test cases designed
- [ ] Test execution complete
- [ ] Fixes implemented
- [ ] Documentation updated
- [ ] Documentation restructuring complete
- [ ] Documentation rewrite following standards complete
- [ ] Impact analysis complete
- [ ] Final report generated
```

---

## Phase 2: Documentation Review

### 2.1 Document Inventory
For each tool in the domain:
- [ ] Read tool documentation file
- [ ] Extract all documented parameters
- [ ] Extract all documented operations
- [ ] Extract documented response formats
- [ ] Extract documented examples

### 2.2 Documentation Quality Check
- Parameter completeness
- Operation completeness
- Example clarity
- Response format accuracy
- Cross-reference consistency

**Output:** Documentation matrix with all documented features

---

## Phase 3: Source Code Analysis

### 3.1 Source Code Inventory
For each tool in the domain:
- [ ] Read source code implementation
- [ ] Extract all implemented parameters
- [ ] Extract all implemented operations
- [ ] Extract actual response formats
- [ ] Identify adapter classes used

### 3.2 Implementation Quality Check
- Parameter exposure in MCP tool signature
- Adapter integration correctness
- Error handling completeness
- Security validations
- Cross-platform compatibility

**Output:** Source code matrix with all implemented features

---

## Phase 4: Gap Analysis

### 4.1 Documentation vs Source Code Comparison
Compare documentation matrix with source code matrix:

| Gap Type | Description | Severity |
|----------|-------------|----------|
| Missing in Docs | Parameter/operation exists in code but not documented | Medium |
| Missing in Source | Parameter/operation documented but not implemented | High |
| Parameter Mismatch | Different names/types between docs and code | High |
| Import Error | Wrong adapter class imported | Critical |
| Duplicate Code | Unreachable or duplicate code blocks | Medium |

### 4.2 Gap Classification
- **Critical (P0):** Runtime errors, import failures, blocking bugs
- **High (P1):** Missing documented features, parameter mismatches
- **Medium (P2):** Undocumented features, documentation inconsistencies
- **Low (P3):** Nice-to-have improvements, convenience features

### 4.3 Gap Summary Report
```markdown
## Gap Analysis Summary
- Total Gaps: X
- Critical: X
- High: X
- Medium: X
- Low: X
- Documentation Accuracy: X%
```

**Output:** Detailed gap analysis with severity classification

---

## Phase 4.5: JSON Output Review Analysis

### 4.5.1 DTO Value Assessment
Analyze all JSON output (DTOs) to ensure value for AI coders:

**Assessment Criteria:**
- Field relevance for AI decision-making
- Actionability of the data provided
- Completeness of context information
- Risk assessment data presence
- Diff/change tracking capability

**Assessment Format:**
```markdown
## DTO Analysis: <DTO_Name>

**Fields:**
| Field | Type | AI Value | Justification |
|-------|------|----------|---------------|
| field1 | string | High | Enables X decision |
| field2 | int | Medium | Useful for Y |

**Summary:** [Overall value assessment]
```

### 4.5.2 JSON Output Audit Checklist
For each DTO in the domain:
- [ ] All fields documented with purpose
- [ ] Field types match implementation
- [ ] Enum values documented
- [ ] Optional fields marked clearly
- [ ] Nested structures documented
- [ ] Example JSON provided
- [ ] Error cases documented

**Output:** DTO value analysis report

---

## Phase 5: Test Case Design

### 5.1 Multi-Scenario Test Planning
For each tool, design test scenarios covering:

**Happy Path Scenarios:**
- Basic operation with minimal parameters
- Operation with all parameters
- Batch operations (if applicable)
- Edge cases (empty results, large datasets)

**Error Scenarios:**
- Invalid parameters
- Missing required parameters
- Non-existent paths/resources
- Permission errors

**Integration Scenarios:**
- VCS integration (git/svn)
- Database operations
- Cross-tool workflows

### 5.2 Test Case Format
```json
{
  "scenario_id": "1.1",
  "description": "Basic file write",
  "tool": "fs_manage",
  "parameters": {
    "operation": "write",
    "path": "/tmp/test.txt",
    "content": "Hello"
  },
  "expected_status": 200,
  "expected_output": "File created successfully"
}
```

**Output:** Test case matrix with 50+ scenarios per domain

---

## Phase 6: Test Execution

### 6.1 CLI Smoke Tests
Execute critical CLI commands:
```bash
python -m src.cli.<domain> <command> <args>
```

Test coverage goals:
- Minimum: 10 critical scenarios
- Ideal: All designed scenarios

### 6.2 MCP Tool Tests
Test via HTTP API or direct function calls:
```python
# Via HTTP
curl -X POST http://127.0.0.1:8001/codecortex-api/v1/sync \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{...}}'

# Via Python
result = await tool_function(**parameters)
```

### 6.3 Test Results Tracking
```markdown
## Test Execution Results
- Total Tests: X
- Passed: X
- Failed: X
- Blocked: X
- Pass Rate: X%
```

**Output:** Test execution report with pass/fail status

---

## Phase 7: Fix Implementation

### 7.1 Critical Fixes (P0)
Fix blocking issues first:
- Import errors
- Runtime crashes
- Security vulnerabilities
- Data corruption bugs

### 7.2 High Priority Fixes (P1)
Fix functional gaps:
- Add missing parameters to MCP tool signatures
- Fix parameter name mismatches
- Implement documented features
- Remove duplicate code

### 7.3 Medium Priority Fixes (P2)
Enhance completeness:
- Document undocumented features
- Update documentation to match implementation
- Add convenience parameters

### 7.4 Fix Verification
After each fix:
- [ ] Code compiles without errors
- [ ] Import statements are correct
- [ ] Parameters match adapter expectations
- [ ] Documentation is updated
- [ ] Tests pass

**Output:** Fix log with before/after code snippets

---

## Phase 8: Documentation Updates

### 8.1 Documentation Corrections
For each gap identified:
- [ ] Update parameter tables
- [ ] Add missing operation documentation
- [ ] Correct incorrect claims
- [ ] Add usage examples
- [ ] Update response format documentation

### 8.2 New Documentation Creation
Create missing documentation files:
- Tool-specific .md files
- CLI command documentation
- Integration guides
- Example workflows

### 8.3 Documentation Validation
- [ ] All parameters documented
- [ ] All operations documented
- [ ] Examples are accurate
- [ ] Cross-references are correct
- [ ] Code snippets are tested

**Output:** Updated documentation files

---

## Phase 8.5: Documentation Restructuring and Removal

### 8.5.1 Audit Documentation Structure
Identify misplaced documentation:

**Audit Checklist:**
- [ ] Check for docs in `src/modules/<domain>/` (misplaced)
- [ ] Check for docs in root directory (should be in docs/)
- [ ] Check for docs in wrong `docs/` subdirectory
- [ ] Identify duplicate documentation
- [ ] Identify orphaned documentation

**Common Misplacements:**
- `src/modules/<domain>/README.md` → should be in `docs/features/<domain>/`
- Root-level `.md` files → should be in `docs/`
- Domain docs in `docs/` without `features/` subdirectory

### 8.5.2 Documentation Removal Strategy
Remove or relocate misplaced documentation:

**Removal Criteria:**
- Duplicate content → keep most recent, delete old
- Misplaced docs → move to correct location
- Orphaned docs → delete if no longer relevant
- Outdated docs → update or archive

**Relocation Strategy:**
```
src/modules/<domain>/README.md → docs/features/<domain>/concept.md
root/<domain>.md → docs/features/<domain>/concept.md
docs/<domain>.md → docs/features/<domain>/concept.md
```

### 8.5.3 Documentation Restructuring
Restructure docs to follow standard pattern:

**Standard Structure:**
```
docs/features/<domain>/
├── concept.md                    # Main domain doc
├── ai-impact-token-efficiency.md # Token efficiency analysis
├── sub-features/                 # Individual action/tool docs
│   ├── <action1>/concept.md
│   ├── <action2>/concept.md
│   └── ...
└── examples/                      # Usage examples
    ├── example1.md
    ├── example2.md
    └── ...
```

**Reference Standard:** `docs/features/codeanalysis/concept.md`

**Output:** Documentation restructuring report

---

## Phase 8.6: Documentation Rewrite Following Standards

### 8.6.1 Standard Template Reference
Reference `docs/features/codeanalysis/concept.md` for structure:

**Required Sections:**
1. Domain header (version, AI impact, production readiness)
2. Business context
3. Why it exists
4. Theoretical foundation
5. Architecture diagram
6. Domain boundary
7. CLI architecture note (if applicable)
8. ~/.aicoders/ compliance
9. Error codes table
10. 10/10 AI Coder Impact features
11. Related sub-features links

### 8.6.2 Rewrite Checklist
For each documentation file:
- [ ] Domain header added with version, AI impact, production readiness
- [ ] Business context section added
- [ ] Why it exists section added
- [ ] Theoretical foundation section added
- [ ] Architecture diagram added
- [ ] Domain boundary section added
- [ ] CLI architecture note added (if applicable)
- [ ] ~/.aicoders/ compliance section added
- [ ] Error codes table added
- [ ] 10/10 AI Coder Impact features added
- [ ] Related sub-features links added

### 8.6.3 Sub-Feature Documentation
For each action/tool in the domain:
- [ ] Create `sub-features/<action>/concept.md`
- [ ] Add purpose section
- [ ] Add why it exists section
- [ ] Add parameters table
- [ ] Add output format
- [ ] Add algorithm description
- [ ] Add use case

### 8.6.4 Examples Documentation
Create usage examples:
- [ ] Create `examples/` directory
- [ ] Add JSON request/response examples
- [ ] Add common use case examples
- [ ] Add error case examples

**Output:** Rewritten documentation following standards

---

## Phase 9: AI Coder Impact Analysis

### 9.1 Impact Assessment Criteria
Rate each tool on AI coder utility:

**Rating Scale:**
- **5/5 (Essential):** Critical for AI coding workflows, high frequency use
- **4/5 (High):** Very useful, common use cases
- **3/5 (Medium):** Useful but situational
- **2/5 (Low):** Niche use cases
- **1/5 (Very Low):** Rarely needed

### 9.2 Impact Dimensions
Assess each tool across dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Context Understanding | 20% | How well tool helps AI understand codebase |
| Risk Identification | 20% | How well tool helps AI identify issues |
| Architecture Guidance | 15% | How well tool helps AI understand structure |
| VCS Integration | 15% | How well tool integrates with version control |
| Repository Management | 15% | How well tool helps manage repos |
| Actionability | 10% | How clear and actionable outputs are |
| Performance | 5% | How fast tool executes |

### 9.3 Impact Report Format
```markdown
## AI Coder Impact Analysis

### Tool: <tool_name>
**Rating:** X/5

**Rationale:**
- [Specific reason 1]
- [Specific reason 2]
- [Specific reason 3]

**Strengths:**
- [Strength 1]
- [Strength 2]

**Weaknesses:**
- [Weakness 1]
- [Weakness 2]

**AI Coder Use Cases:**
- [Use case 1]
- [Use case 2]

**Recommendation:** [Specific improvement suggestion]
```

### 9.4 Overall Domain Assessment
```markdown
## Overall AI Coder Impact: ⭐⭐⭐⭐⭐ (X/5)

**Category Assessments:**
- Context Understanding: X/5
- Risk Identification: X/5
- Architecture Guidance: X/5
- VCS Integration: X/5
- Repository Management: X/5
- Actionability: X/5
- Performance: X/5
```

**Output:** Comprehensive impact analysis report

---

## Phase 9.5: AI Impact Token Efficiency Analysis

### 9.5.1 Token Efficiency Assessment
For each tool, analyze token efficiency:

**Metrics to Track:**
- Average response size (tokens)
- Average tool calls per decision
- Total tokens per decision
- Token savings percentage

**Analysis Method:**
1. Calculate token overhead per response (added fields)
2. Calculate token savings via reduced tool calls
3. Compare before/after enrichment scenarios
4. Calculate net token impact

### 9.5.2 Scenario-Based Analysis
For each tool, analyze 5 typical AI coder scenarios:

**Example Scenarios:**
- Fixing syntax errors
- Analyzing code structure
- Searching for code patterns
- Checking project health
- Fixing compliance issues

**Calculation Format:**
```markdown
| Scenario | Without Enrichment | With Enrichment | Savings |
|----------|-------------------|----------------|---------|
| Scenario 1 | X tokens | Y tokens | Z% |
```

### 9.5.3 Token Efficiency Report Format
```markdown
## AI Impact Token Efficiency Analysis

### Tool: <tool_name>
**Rating:** X/5

**Token Efficiency Metrics:**
- Avg Response Size: ~X tokens
- Avg Tool Calls per Decision: X
- Total Tokens per Decision: X
- Token Savings: X%

**Enrichment Cost:**
- Added Fields: [list of fields]
- Token Overhead: ~X tokens per response

**Token Savings:**
- Scenario 1: X tokens saved (Y%)
- Scenario 2: X tokens saved (Y%)
- Average: X tokens saved (Y%)

**Conclusion:** [Summary of token efficiency impact]
```

### 9.5.4 Overall Token Efficiency Assessment
```markdown
## Overall Token Efficiency: ⭐⭐⭐⭐⭐ (X/5)

**Domain-Level Metrics:**
- Avg Response Size: ~X tokens
- Avg Tool Calls per Decision: X
- Total Tokens per Decision: X
- Token Savings: X%

**Key Findings:**
- [Finding 1]
- [Finding 2]
- [Finding 3]
```

**Output:** Token efficiency analysis report saved to `docs/features/<domain>/ai-impact-token-efficiency.md`

---

## Phase 10: Final Report Generation

---

## Phase 10: Final Report Generation

### 10.1 Report Structure
Generate comprehensive final report:

```markdown
# <Domain> Domain - Comprehensive QA Report

**Date:** YYYY-MM-DD
**Tester:** QA Expert (Cascade)
**Scope:** <Domain> - X MCP tools + Y CLI commands
**Perspective:** AHLI MCP Expert & AI Coder Specialist
**Source of Truth:** Source code implementation

---

## Executive Summary

**Overall Grade:** A/B/C/D/F

[Brief summary paragraph]

**Key Findings:**
- Documentation Accuracy: X%
- Test Execution: X/X passed
- AI Coder Impact: ⭐⭐⭐⭐⭐ (X/5)
- Critical Issues: X
- Minor Issues: X

---

## 1. Gap Analysis Summary

[Gap analysis details]

---

## 2. Test Execution Results

[Test execution details]

---

## 3. AHLI MCP Expert Assessment

[AI coder impact analysis]

---

## 4. Key Insights for AI Coder Assistance

[Key insights]

---

## 5. Recommendations

[P0, P1, P2 recommendations]

---

## 6. Conclusion

[Final assessment and production readiness]
```

### 10.2 Report Location
Save report to: `outputs/analysis/YYYY-MM-DD/<domain>-qa-report-final.md`

### 10.3 Supporting Artifacts
- Gap analysis: `outputs/analysis/YYYY-MM-DD/<domain>-gap-analysis.md`
- Test cases: `outputs/analysis/YYYY-MM-DD/<domain>-test-cases.md`
- AI impact: `outputs/analysis/YYYY-MM-DD/<domain>-ai-impact.md`
- AI impact token efficiency: `docs/features/<domain>/ai-impact-token-efficiency.md`

**Note:** AI impact token efficiency document should follow the pattern established by codegraph and codeanalysis domains, saved in the domain's docs/features/ directory.

---

## Appendix: Quick Reference

### Common Fix Patterns

#### Pattern 1: Missing Parameter in MCP Tool
**Problem:** Parameter documented but not in tool signature
**Fix:** Add parameter to function signature and pass to adapter
```python
# Before
async def tool_name(required_param: str) -> dict:
    params = {"required_param": required_param}
    return Adapter.process(params)

# After
async def tool_name(required_param: str, missing_param: str = "default") -> dict:
    params = {"required_param": required_param, "missing_param": missing_param}
    return Adapter.process(params)
```

#### Pattern 2: Wrong Import
**Problem:** Importing non-existent class
**Fix:** Correct import to match actual class name
```python
# Before
from src.modules.domain.adapters.adapter import WrongName

# After
from src.modules.domain.adapters.adapter import CorrectName
```

#### Pattern 3: Parameter Name Mismatch
**Problem:** Documentation says `max_changes`, code uses `max_events`
**Fix:** Align parameter names
```python
# Change parameter name to match documentation and adapter expectation
```

#### Pattern 4: Duplicate Code Block
**Problem:** Unreachable duplicate elif block
**Fix:** Remove duplicate, keep first occurrence
```python
# Remove the duplicate block at lines 274-279
# Keep the block at lines 246-251
```

### Documentation Template

```markdown
# <tool_name>

**Purpose:** [One-line description]

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| param1 | string | Yes | - | Description |
| param2 | boolean | No | false | Description |

**Operations:**
- operation1: Description
- operation2: Description

**Response Format:**
```json
{
  "success": true,
  "data": {...}
}
```

**Examples:**
[3-5 usage examples]

**Error Cases:**
| Error Code | Description |
|------------|-------------|
| ERR_001 | Description |
```

---

## Workflow Execution Checklist

Use this checklist to ensure all phases are complete:

### Phase 1: Initial Assessment
- [ ] Scope defined
- [ ] Documentation gathered
- [ ] TODO list created

### Phase 2: Documentation Review
- [ ] All tool docs read
- [ ] Documentation matrix created
- [ ] Quality check complete

### Phase 3: Source Code Analysis
- [ ] All source files read
- [ ] Source code matrix created
- [ ] Implementation check complete

### Phase 4: Gap Analysis
- [ ] Documentation vs code comparison done
- [ ] Gaps classified by severity
- [ ] Gap summary report generated

### Phase 4.5: JSON Output Review
- [ ] DTO value assessment complete
- [ ] JSON output audit checklist complete
- [ ] DTO value analysis report generated

### Phase 5: Test Case Design
- [ ] Happy path scenarios designed
- [ ] Error scenarios designed
- [ ] Integration scenarios designed
- [ ] Test case matrix created

### Phase 6: Test Execution
- [ ] CLI smoke tests executed
- [ ] MCP tool tests executed
- [ ] Test results tracked
- [ ] Test execution report generated

### Phase 7: Fix Implementation
- [ ] P0 fixes implemented
- [ ] P1 fixes implemented
- [ ] P2 fixes implemented
- [ ] All fixes verified

### Phase 8: Documentation Updates
- [ ] Documentation corrections made
- [ ] New documentation created
- [ ] Documentation validated

### Phase 8.5: Documentation Restructuring and Removal
- [ ] Documentation structure audited
- [ ] Misplaced docs identified
- [ ] Duplicate docs removed
- [ ] Orphaned docs deleted
- [ ] Docs relocated to correct locations
- [ ] Restructuring report generated

### Phase 8.6: Documentation Rewrite Following Standards
- [ ] Standard template reference reviewed
- [ ] Main concept.md rewritten with all required sections
- [ ] Sub-feature docs created for each action
- [ ] Examples directory created
- [ ] Usage examples added
- [ ] All docs follow codeanalysis standard

### Phase 9: AI Coder Impact Analysis
- [ ] All tools rated
- [ ] Impact dimensions assessed
- [ ] Impact report generated

### Phase 9.5: AI Impact Token Efficiency Analysis
- [ ] Token efficiency metrics calculated
- [ ] Scenario-based analysis completed
- [ ] Token efficiency report generated
- [ ] Report saved to docs/features/<domain>/ai-impact-token-efficiency.md

### Phase 10: Final Report
- [ ] Final report generated
- [ ] Supporting artifacts saved
- [ ] TODO list completed

---

## Success Criteria

A QA fixing harness is considered successful when:

1. **Gap Analysis:** All critical and high gaps identified and documented
2. **Test Coverage:** Minimum 80% of designed scenarios executed
3. **Fix Rate:** 100% of P0 fixes, 90% of P1 fixes, 70% of P2 fixes completed
4. **Documentation:** 100% documentation accuracy achieved
5. **Impact Analysis:** All tools rated with detailed rationale
6. **Token Efficiency:** Token efficiency analysis completed with scenario-based savings calculated
7. **Production Readiness:** Domain achieves 85%+ production readiness score

---

## Notes

- **Source of Truth:** Always trust source code over documentation
- **Safety First:** Always use dry_run parameters when available
- **Incremental Fixes:** Fix P0 first, then P1, then P2
- **Documentation Driven:** Update docs immediately after code changes
- **AI Coder Focus:** Prioritize features that enhance AI coder utility
- **Cross-Platform:** Test on Windows, macOS, and Linux when possible
- **Security:** Validate path traversal, SSRF, and input sanitization
