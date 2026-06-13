# CodeAnalysis: Code Quality Gate

> **Domain:** CodeAnalysis
> **Package:** `src/modules/codeanalysis/`
> **Version:** 2.0.0
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

CodeAnalysis is the **~/.aicoders/ quality gate** — validates source code against all coding standards and returns actionable findings with error codes, remediation steps, and a compliance_score (0–100). It provides 4 MCP tools for code analysis, search, audit, and status reporting.

## Why This Exists

- **Compliance Enforcement:** CodeAnalysis enforces ~/.aicoders/ standards across the codebase with 24 audit categories
- **AI Coder Empowerment:** Provides actionable findings with error codes and remediation for AI-assisted development
- **Quality Gate:** Returns compliance_score (0–100) for CI/CD gates
- **Multi-Layer Search:** Combines FTS, semantic, and graph search for comprehensive code discovery
- **Auto-Fix Generation:** Revolutionary feature that generates fix code with diff preview for common issues
- **Syntax Error Detection:** Detects unclosed brackets, missing semicolons, whitespace issues, and more

## Theoretical Foundation

- **AST Parsing:** Tree-Sitter for accurate symbol extraction across 22+ languages
- **SQLite FTS5:** Full-text search for fast symbol name matching
- **SentenceTransformers:** Semantic embeddings for concept similarity
- **Graph Theory:** Knowledge graph for relationship discovery and impact analysis
- **Regex Pattern Matching:** Pattern-based code search with validation
- **Token Economy:** Auto-truncation based on token budget with summary mode
- **Parallel Processing:** ThreadPoolExecutor for batch operations
- **Incremental Scanning:** File modification time-based filtering for CI/CD

## Architecture

```
src/modules/codeanalysis/
├── api/              → tools.py: 4 MCP tools, cli.py: CLI commands, api_response() compliant
├── services/         → Service classes: DI via constructor, pure use-cases
│   ├── analyze.py   → AST-aware code analysis with batch processing
│   ├── search.py    → Multi-layer search (FTS, semantic, graph, regex, symbol)
│   ├── audit.py     → 24-category compliance audit with auto-fix generation
│   └── status.py    → Project health and AI readiness scoring
├── core/            → dtos.py: typed DTOs for all public interfaces
└── analyzers/       → Domain analyzers (legacy, being phased out)
```

## Domain Boundary

- **Owns:** `code_analyze`, `code_search`, `code_audit`, `code_status`
- **Does NOT own:** `code_refactor` (handled by coderefactor domain)
- **Depends on:** `DatabaseManager`, `FilesystemService`
- **Consumed by:** MCP layer via `api/tools.py`

## CLI Architecture Note

The CLI domain is named `codebase` (not `codeanalysis`) as an intentional UX decision. This provides a unified interface for codebase operations across multiple domains (codeanalysis, codegraph, codeindex, codetester, coderefactor). Users access all codebase operations via `codecortex cb <command>`.

## ~/.aicoders/ Compliance

- **API Standard:** `api_response()` for all tool responses
- **DDD:** `api/` + `services/` + `core/` separation
- **DI:** Constructor injection for all services
- **Boundary:** Data crosses layers only via DTOs
- **Error Handling:** Guard clauses, structured errors
- **Logging:** `CodeCortex.CodeAnalysis.*` logger namespace
- **Documentation:** All docs in `docs/features/codeanalysis/`

## Audit Categories (24)

1. **secrets** — hardcoded API keys, tokens, passwords
2. **pii** — email, SSN, credit card
3. **misconfig** — debug mode, wildcard CORS
4. **vulns** — SQL injection, eval, pickle
5. **comments** — TODO, FIXME, HACK, STUB, BUG, placeholder docs
6. **naming** — PascalCase/SnakeCase compliance
7. **type_hints** — missing type hints on public API
8. **file_structure** — header DocBlock validation: @project, @package, @author, @copyright, @stack
9. **class_docblock** — class-level DocBlock: missing @package, @author, description
10. **modular** — god class, direct cross-module instantiation, missing contracts
11. **modular_structure** — folder structure compliance: root folders, module layout, plural containers
12. **architecture** — circular imports, service locator, high coupling, framework coupling, repository pattern, service pattern
13. **syntax** — unclosed brackets, mismatched brackets, mixed indentation, trailing whitespace, missing semicolons, unclosed quotes
14. **error_handling** — bare except, try without catch
15. **di_compliance** — direct instantiation instead of DI
16. **docblock** — method DocBlock validation: description, @param, @return, @throws
17. **logging** — 7 checks: get_logger() usage, log level, f-string template, error_code, identity fields null, structured context dict
18. **api_response** — 8 checks: R1 manual dict, R1 missing fields, O1 request_id, O3 error_code, R3/R4 error data/success, ID5 null identity, P1 missing links, §3 message length
19. **semver** — 8 checks: .version file exists, valid SemVer format, leading zeros, trailing whitespace, package.json/pyproject.toml version sync, release artifact naming, special chars, missing checksums
20. **pwa** (optional) — 9 checks: service worker registration, manifest existence, HTTPS enforcement, cache strategy interface, PWA icons, theme_color/background_color, touch targets ≥44px, body font ≥16px, offline page, container queries
21. **crossplatform** (optional) — 7 checks: UI imports in service layer, hardcoded screen dimensions, raw HTTP in business logic, missing responsive breakpoints, dark mode, accessibility aria attributes
22. **test_debug** — 8 checks: test file naming convention, test function pattern, debug print in tests, AAA pattern comments, tests/ directory, test type subdirs, outputs/tests/, outputs/debugs/
23. **codification** — 6 checks: UUID v4 vs v7, _code suffix for code fields, code format template, Dual Identity Architecture, auto-increment PK, human-readable code generation
24. **coding_naming** — 5 checks: directory naming per stack (§2), interface naming (§3), abstract prefix (§3), constant UPPER_SNAKE_CASE (§5), JSON/YAML snake_case (§5)

## Error Codes

| Prefix | Tool |
|--------|------|
| CA_0xx | code_analyze |
| CA_01x | code_search |
| CA_02x | code_audit |
| CA_03x | code_status |
| CA_SYN | syntax errors |
| CA_ARCH | architecture checks |
| CA_5xx | Internal error |

## 10/10 AI Coder Impact Features

1. **Auto-Fix Generation** — Generate fix code with diff preview for common issues
2. **Batch Analysis** — Parallel processing of multiple targets with configurable workers
3. **Incremental Scanning** — Only scan files modified since timestamp (10x faster for CI)
4. **Multi-Mode Search** — 5 search types: multi, symbol, regex, semantic, graph
5. **Syntax Error Detection** — Unclosed brackets, mismatched brackets, mixed indentation, trailing whitespace, missing semicolons, unclosed quotes
6. **Architectural Pattern Detection** — Circular imports, service locator, high coupling, framework coupling
7. **Smart Caching** — Query hash-based cache with TTL and sync metadata
8. **Dry-Run Safety** — Preview fixes before applying them

## Token Economy

All responses pass through `api_response()` which auto-truncates data exceeding token budget when `summary_mode=True`.

---

## Related Sub-Features

- [Code Analyze](sub-features/code_analyze/concept.md)
- [Code Search](sub-features/code_search/concept.md)
- [Code Audit](sub-features/code_audit/concept.md)
- [Code Status](sub-features/code_status/concept.md)

## Compliance Standards Map

| ~/.aicoders/ Standard | Checked By | Audit Category |
|----------------------|------------|----------------|
| `coding-standard.md` §1 (Class DocBlock) | code_audit | `file_structure` — @project, @package, @author, @copyright, @stack, class desc |
| `coding-standard.md` §1 (Class DocBlock) | code_audit | `class_docblock` — class-level @package, @author, description |
| `coding-standard.md` §1 (Method DocBlock) | code_audit | `docblock` — description, @param, @return, @throws |
| `coding-standard.md` §2 (Dir/File naming) | code_audit | `naming` — PascalCase/snake_case/kebab-case per language |
| `coding-standard.md` §3-5 (Visibility, Constants) | code_audit | `naming` — method/class/constant violations |
| `coding-standard.md` | code_audit | `type_hints` — missing type hints on public API |
| `coding-standard.md` (zero-placeholder) | code_audit | `comments` — TODO/FIXME/STUB/BUG, empty docstrings |
| `modular-standard.md` §1 | code_audit | `modular` — god class (3+ classes per file) |
| `modular-standard.md` §3 | code_audit | `di_compliance` — direct instantiation in classes |
| `errors-logs-standard.md` §1 | code_audit | `error_handling` — bare except, try no catch |
| `errors-logs-standard.md` §3 | code_audit | `logging` — print vs structured JSON logging |
| `security-standard.md` | code_audit | `secrets`, `pii`, `misconfig`, `vulns` |
| `api-standard.md` §2 (R1) | code_audit | `api_response` — required fields: success, status_code, message, data, meta |
| `api-standard.md` §2 (O1) | code_audit | `api_response` — request_id must use `new_request_id()` |
| `api-standard.md` §2 (O3) | code_audit | `api_response` — error_code required on >= 400 |
| `api-standard.md` §2 (R3/R4) | code_audit | `api_response` — data=None, success=False on error |
| `api-standard.md` §3 | code_audit | `api_response` — message max 120 chars |
| `project-structure-modular-standard.md` §2 | code_audit | `modular_structure` — missing root folders (.agents, src/, tests/) |
| `project-structure-modular-standard.md` §5 | code_audit | `modular_structure` — module internal structure missing subdirs/manifest/README |
| `project-structure-modular-standard.md` §8 (plural) | code_audit | `modular_structure` — container folder not plural |
| `project-structure-modular-standard.md` §8.4 | code_audit | `modular_structure` — root folder naming case |
| `project-structure-modular-standard.md` §1, §11.1 (M1) | code_audit | `modular` — god class, cross-module direct `new Class()` |
| `project-structure-modular-standard.md` §11.3 (P2) | code_audit | `modular` — missing contract/interface for services |
| `semantic-versioning.md` §5.1 | code_audit | `semver` — .version file exists, valid SemVer format, leading zeros, whitespace |
| `semantic-versioning.md` §6 | code_audit | `semver` — package.json/pyproject.toml version sync |
| `semantic-versioning.md` §7.2 | code_audit | `semver` — release artifact naming convention, special chars |
| `semantic-versioning.md` §7.4 | code_audit | `semver` — missing checksums (.sha256) for release artifacts |
| `pwa-standard.md` §3.1 | code_audit | `pwa` — HTTPS enforcement check |
| `pwa-standard.md` §3.2 | code_audit | `pwa` — Web App Manifest existence |
| `pwa-standard.md` §4.1 | code_audit | `pwa` — cache strategy pattern interface |
| `pwa-standard.md` §5.2 | code_audit | `pwa` — touch targets ≥44px, body font ≥16px |
| `pwa-standard.md` §10 | code_audit | `pwa` — offline page, PWA icons, manifest |
| `cross-platform-standard.md` §1 | code_audit | `crossplatform` — UI framework imports in service layer |
| `cross-platform-standard.md` §4 | code_audit | `crossplatform` — raw HTTP objects in business logic |
| `cross-platform-standard.md` §6 | code_audit | `crossplatform` — hardcoded dimensions, dark mode, ARIA |
| `debug-test-standard.md` §3.1 | code_audit | `test_debug` — test file/function naming convention |
| `debug-test-standard.md` §3.2 | code_audit | `test_debug` — AAA pattern (Arrange/Act/Assert) |
| `debug-test-standard.md` §3.3 | code_audit | `test_debug` — tests/ directory, type subdirs |
| `debug-test-standard.md` §0.1 | code_audit | `test_debug` — outputs/tests/, outputs/debugs/ directories |
| `codification-standard.md` §1.4 (P1) | code_audit | `codification` — Dual Identity Architecture (UUID + human-readable code) |
| `codification-standard.md` §2.3 | code_audit | `codification` — UUID v4 vs v7, auto-increment PK |
| `codification-standard.md` §3.2 | code_audit | `codification` — code format template, _code suffix |
| `coding-standard.md` §2 | code_audit | `coding_naming` — directory naming per stack |
| `coding-standard.md` §3 | code_audit | `coding_naming` — interface/abstract naming |
| `coding-standard.md` §5 | code_audit | `coding_naming` — constants UPPER_SNAKE_CASE, JSON snake_case |

## Tool Reference

### code_analyze

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `target` | string | ✅ | — | Path file/directory |
| `mode` | string | ❌ | `auto` | `overview` / `detailed` / `symbol_focus` / `auto` |
| `summary` | bool | ❌ | `null` | Auto-truncate if > 50K chars |
| `max_depth` | int | ❌ | `3` | Tree depth (max 10) |
| `focus` | string | ❌ | — | Symbol name for `symbol_focus` mode |
| `follow_depth` | int | ❌ | `1` | Call graph depth (max 3) |
| `cursor` | string | ❌ | — | Pagination token |
| `page_size` | int | ❌ | `100` | Items per page (max 500) |
| `include_docstring` | bool | ❌ | `true` | Include docstrings |
| `include_comments` | bool | ❌ | `false` | Include comment lines |
| `repo_id` | string | ❌ | — | Repository UUID |

**Modes:**
- `overview` — Directory tree with file types and languages
- `detailed` — All symbols (classes, functions) with signatures + call graph
- `symbol_focus` — Specific symbol with BFS call graph traversal (direct + transitive)
- `auto` — Picks based on target (file → detailed, dir → overview)

**Output:**
```json
{
  "mode": "detailed",
  "target": "/path/to/file.py",
  "count": 12,
  "symbols": [{
    "name": "PaymentProcessor",
    "kind": "class",
    "file": "/path/to/file.py",
    "line_start": 1,
    "line_end": 50,
    "signature": "class PaymentProcessor:",
    "calls": ["validate_payment", "charge"]
  }],
  "edges": [{"from": "process", "to": "validate", "relation": "calls"}],
  "next_cursor": null
}
```

---

### code_search

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | ✅ | — | Search query |
| `search_type` | string | ❌ | `multi` | `multi` / `symbol` / `regex` / `graph` / `semantic` |
| `limit` | int | ❌ | `50` | Max results (max 200) |
| `repo_id` | string | ❌ | — | Filter by repository |
| `file_pattern` | string | ❌ | `*` | Glob filter |
| `include_content` | bool | ❌ | `false` | Include snippets |
| `semantic` | bool | ❌ | `false` | Enable semantic embedding enrichment |
| `graph` | bool | ❌ | `false` | Enable graph relationship enrichment |
| `graph_relations` | list | ❌ | — | Relation types to include |

**Search types:**
- `multi` — Multi-layer search combining FTS + optional semantic + graph (default)
- `symbol` — `LIKE` query with cursor-based pagination
- `regex` — Compiled regex against symbol names (with validation)
- `graph` — CTE recursive call graph traversal (BFS, max depth 3)
- `semantic` — Cosine similarity on pre-indexed embeddings (requires `embeddings` table)

**Output:**
```json
{
  "items": [{"symbol": "PaymentProcessor", "kind": "class", "file": "pay.py", "line": 1, "confidence": 1.0}],
  "next_cursor": 50,
  "total": 120
}
```

---

### code_audit

The core quality gate — scans code against 22 ~/.aicoders/ compliance categories.

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `target` | string | ✅ | — | Path file/directory |
| `scan_categories` | array | ❌ | `[all 15]` | Categories to scan |
| `severity_threshold` | string | ❌ | `medium` | `low` / `medium` / `high` / `critical` |
| `entropy_threshold` | float | ❌ | `4.5` | Shannon entropy for secrets |
| `include_comments` | bool | ❌ | `false` | Include comment text |
| `max_file_size_kb` | int | ❌ | `1024` | Max file size (max 5000) |
| `files` | array | ❌ | — | Specific files (scans all if omitted) |
| `output_format` | string | ❌ | `json` | `json` / `csv` / `report` |
| `use_ast` | bool | ❌ | `true` | Use cached AST for accuracy |
| `use_aiignore` | bool | ❌ | `true` | Read `.aiignore` for excludes |
| `repository_id` | string | ❌ | — | Persist findings to DB |
| `since` | string | ❌ | — | ISO 8601 for incremental scan |

**22 Audit Categories:**

| # | Category | Code Prefix | What It Detects | ~/.aicoders/ Rule |
|---|----------|-------------|-----------------|-------------------|
| 1 | `secrets` | CA_SEC | AWS keys, GitHub tokens, private keys, password vars | security-standard.md |
| 2 | `pii` | CA_PII | Email, SSN, credit cards | security-standard.md |
| 3 | `misconfig` | CA_MIS | Debug enabled, wildcard CORS | security-standard.md |
| 4 | `vulns` | CA_VUL | SQL injection, eval, pickle, unsafe yaml.load | security-standard.md |
| 5 | `comments` | CA_CMT | TODO/FIXME/HACK/STUB/BUG, empty docstrings | coding-standard.md (zero-placeholder) |
| 6 | `naming` | CA_NAM | Non-PascalCase classes, non-snake_case functions | coding-standard.md §2-5 |
| 7 | `type_hints` | CA_TYP | Missing type hints on public method params | coding-standard.md |
| 8 | `file_structure` | CA_STR | File header: @project, @package, @author, @copyright, @stack, class desc | coding-standard.md §1 |
| 9 | `class_docblock` | CA_DOC0x | Class DocBlock: @package, @author, description | coding-standard.md §1 |
| 10 | `modular` | CA_MOD | God class, direct cross-module new Class(), missing contracts | project-structure-modular-standard.md §1, §11.1 |
| 11 | **`modular_structure`** | **CA_MDL** | **Root folders, module layout, plural containers, naming per §2, §5, §8** | project-structure-modular-standard.md §2, §5, §8 |
| 12 | `error_handling` | CA_ERR | Bare except, try without catch | errors-logs-standard.md §1 |
| 13 | `di_compliance` | CA_DI | Direct instantiation instead of constructor DI | modular-standard.md §3 |
| 14 | `docblock` | CA_DOC | Method DocBlock: description, @param, @return, @throws | coding-standard.md §1 |
| 15 | `logging` | CA_LOG | **7 checks**: get_logger(), log level, f-string, error_code, identity null, structured dict | errors-logs-standard.md §3 + logging-standard.md |
| 16 | **`api_response`** | CA_API | **8 checks**: R1 manual dict, R1 fields, O1, O3, R3/R4, ID5, P1, §3 length | api-standard.md §2-4 |
| 17 | **`semver`** | CA_SEM | **6 checks**: .version file/format, leading zeros, whitespace, package.json/pyproject.toml sync, release naming, checksums | semantic-versioning.md |
| 18 | **`pwa`** (opt) | CA_PWA | **8 checks**: manifest, HTTPS, cache strategy pattern, touch targets, font-size, offline page, icons, container queries | pwa-standard.md |
| 19 | **`crossplatform`** (opt) | CA_CRO | **6 checks**: UI in service layer, hardcoded dimensions, raw HTTP in business, responsive breakpoints, dark mode, ARIA | cross-platform-standard.md |
| 20 | **`test_debug`** | CA_TD | **8 checks**: test naming, func pattern, debug prints, AAA, tests/ dir, type subdirs, outputs/tests/, outputs/debugs/ | debug-test-standard.md |
| 21 | **`codification`** | CA_COD | **6 checks**: UUID v4 vs v7, _code suffix, code format template, Dual Identity Architecture, auto-increment PK, code gen format | codification-standard.md |
| 22 | **`coding_naming`** | CA_CNAM | **5 checks**: directory casing per stack, interface naming, abstract prefix, UPPER_SNAKE_CONSTANTS, JSON/YAML snake_case | coding-standard.md §2-5 |
| 23 | **`architecture`** | CA_ARCH | **6 checks**: circular imports, service locator, high coupling, framework coupling, repository pattern, service pattern | modular-standard.md + clean-architecture |
| 24 | **`syntax`** | CA_SYN | **8 checks**: unclosed brackets, mismatched brackets, mixed indentation, trailing whitespace, missing semicolons, unclosed quotes, blank line whitespace | syntax-standard |

---

## DocBlock Validation Detail

The `code_audit` tools performs **three levels** of documentation validation per coding-standard.md §1:

### Level 1: File Header (Class DocBlock)

Expected format at the **top of every file**:
```
/**
 * @project   CodeCortex
 * @package   Domain/CodeAnalysis/Application
 * @author    Steeven Andrian
 * @copyright (c) 2026 CODDY Codework
 * @standard  CODDY-CrossStack-v1.0
 * @stack     Python
 * * Class CodeAuditService – Single Responsibility: ~/.aicoders/ compliance gate.
 */
```

**Validation:**
- `@project` — Project name (required)
- `@package` — Namespace path (required)
- `@author` — Git user.name (required)
- `@copyright` — Copyright statement (required)
- `@stack` — Language stack (required if @package contains `/` or `\`)
- `* * Class ... – ...` — Class description line with single-responsibility statement

Missing any of these → `CA_STR_010` through `CA_STR_015`.

### Level 2: Method DocBlock

Expected format **before every public method**:
```
/**
 * Process payment and update ledger.
 * @param  int      $user_id     User identifier
 * @param  float    $amount      Transaction amount
 * @param  str      $currency    ISO 4217 currency code
 * @return Dict[str, Any]
 * @throws ValueError  If amount is negative
 */
def process_payment(user_id: int, amount: float, currency: str) -> Dict[str, Any]:
```

**Validation:**
1. **Description** — Business logic explanation of WHAT the method does
2. **`@param`** — Every actual parameter must have a matching `@param type name description`
3. **`@return`** — Must exist (use `None` for void methods, except `__init__`)
4. **`@throws`** — Required if method body contains `raise`/`throw`

**Scoring:**
- Missing docstring entirely → `CA_DOC_001` (medium severity)
- Missing description → `CA_DOC_020` (low)
- Missing `@param` for parameter → `CA_DOC_021` (low)
- Missing `@return` → `CA_DOC_022` (low)
- Missing `@throws` when raising → `CA_DOC_023` (low)

### Level 3: Class DocBlock

Expected format **before every class**:
```
/**
 * Service for processing payments.
 * @package Domain/Billing
 * @author  Steeven Andrian
 */
class PaymentProcessor:
```

**Validation:**
- DocBlock exists → `CA_DOC_010`
- `@package` present → `CA_DOC_011`
- `@author` present → `CA_DOC_012`
- Description present → `CA_DOC_013`

### Comment Tags (zero-placeholder policy)

Per coding-standard.md zero-placeholder policy, these tags are flagged:

| Tag | Severity | Code | When |
|-----|----------|------|------|
| `TODO:` | high | CA_CMT_001 | Unfinished task |
| `FIXME:` | critical | CA_CMT_002 | Known bug |
| `HACK:` | medium | CA_CMT_003 | Temporary workaround |
| `XXX:` | high | CA_CMT_004 | Deprecated code |
| `STUB:` | high | CA_CMT_005 | Placeholder implementation |
| `WIP:` | medium | CA_CMT_006 | Work in progress |
| `BUG:` | critical | CA_CMT_007 | Known bug |
| `"""` empty | medium | CA_CMT_008 | Placeholder docstring |

### Complete Error Code Reference

| Code | Severity | Category | Message |
|------|----------|----------|---------|
| CA_SEC_001-004 | critical/high | secrets | Hardcoded AWS key, GitHub token, private key, password var |
| CA_PII_001-003 | medium-critical | pii | Email, SSN, credit card |
| CA_MIS_001 | medium | misconfig | Debug mode enabled |
| CA_MIS_002 | high | misconfig | Wildcard CORS |
| CA_VUL_001-004 | varying | vulns | SQL injection, eval, pickle, yaml.load |
| CA_CMT_001-007 | varying | comments | Zero-placeholder tags |
| CA_CMT_008 | medium | comments | Empty/placeholder docstring |
| CA_NAM_001 | medium | naming | Class not PascalCase |
| CA_NAM_002 | low | naming | Function not snake_case |
| CA_TYP_001 | medium | type_hints | Parameter missing type hint |
| CA_STR_001 | low | file_structure | No header DocBlock |
| CA_STR_010 | medium | file_structure | Missing @project |
| CA_STR_011 | medium | file_structure | Missing @package |
| CA_STR_012 | medium | file_structure | Missing @author |
| CA_STR_013 | medium | file_structure | Missing @copyright |
| CA_STR_014 | low | file_structure | Missing @stack (nested package) |
| CA_STR_015 | low | file_structure | Missing class description line |
| CA_DOC_010 | medium | class_docblock | Class missing DocBlock |
| CA_DOC_011 | low | class_docblock | Missing @package |
| CA_DOC_012 | low | class_docblock | Missing @author |
| CA_DOC_013 | low | class_docblock | Missing class description |
| CA_DOC_001 | medium | docblock | Method missing docstring |
| CA_DOC_020 | low | docblock | Missing description |
| CA_DOC_021 | low | docblock | Missing @param for parameter |
| CA_DOC_022 | low | docblock | Missing @return |
| CA_DOC_023 | low | docblock | Missing @throws (raises exception) |
| CA_MOD_001 | medium | modular | God file (3+ classes) |
| CA_MOD_002 | medium | modular | Direct cross-module instantiation `new Class()` (M1) |
| CA_MOD_003 | low | modular | Service missing contract/interface (P2) |
| CA_MDL_001 | medium | modular_structure | Missing required root folder/file |
| CA_MDL_002 | low | modular_structure | Module missing manifest (module.json) |
| CA_MDL_003 | low | modular_structure | Module missing README.md |
| CA_MDL_004 | low | modular_structure | Module limited HMVC-P structure |
| CA_MDL_005 | medium | modular_structure | Container folder not plural |
| CA_MDL_006 | low | modular_structure | Root folder wrong naming case |
| CA_ERR_001 | high | error_handling | try without except |
| CA_ERR_002 | medium | error_handling | Bare except |
| CA_DI_001 | medium | di_compliance | Direct instantiation not injection |
| CA_LOG_001 | low | logging | print() instead of logger |
| CA_LOG_002 | low | logging | String-based not structured |
| CA_LOG_010 | medium | logging | Uses logging.getLogger() instead of get_logger() |
| CA_LOG_011 | low | logging | Invalid log level (not debug/info/warn/error/fatal) |
| CA_LOG_012 | medium | logging | f-string in log message — must be static template |
| CA_LOG_013 | high | logging | Error level log missing error_code |
| CA_LOG_014 | low | logging | Identity field set to None in log (should omit) |
| CA_API_001 | high | api_response | Manual response dict instead of api_response() |
| CA_API_002 | medium | api_response | request_id not generated via new_request_id() |
| CA_API_003 | medium | api_response | Error response missing error_code |
| CA_API_005 | high | api_response | Error response with data != None or success=True |
| CA_API_009 | high | api_response | api_response() missing required field |
| CA_API_007 | medium | api_response | List data without pagination links (P1) |
| CA_API_008 | low | api_response | Identity field set to None (ID5 — should omit) |
| CA_API_010 | low | api_response | message exceeds 120 chars |
| CA_SEM_001 | high | semver | Missing .version file or invalid SemVer format |
| CA_SEM_002 | medium | semver | Leading zeros in version number |
| CA_SEM_003 | low | semver | Trailing whitespace/newlines in .version |
| CA_SEM_004 | medium | semver | Release artifact missing checksum (.sha256) |
| CA_SEM_005 | medium | semver | Release artifact naming convention violation |
| CA_SEM_006 | low | semver | Special characters in release filename |
| CA_PWA_002 | high | pwa | Missing Web App Manifest |
| CA_PWA_003 | high | pwa | Missing HTTPS enforcement |
| CA_PWA_004 | medium | pwa | Cache/fetch without strategy pattern |
| CA_PWA_005 | low | pwa | No PWA icons directory |
| CA_PWA_007 | medium | pwa | Touch target < 44px |
| CA_PWA_008 | low | pwa | Body font-size < 16px |
| CA_PWA_009 | low | pwa | Missing @container queries |
| CA_PWA_010 | medium | pwa | No offline page |
| CA_CRO_001 | high | crossplatform | UI framework imports in service/core layer |
| CA_CRO_003 | medium | crossplatform | Hardcoded screen dimensions |
| CA_CRO_004 | high | crossplatform | Raw HTTP objects in business logic |
| CA_CRO_006 | low | crossplatform | No responsive breakpoints |
| CA_CRO_007 | low | crossplatform | Missing prefers-color-scheme dark mode |
| CA_CRO_008 | medium | crossplatform | Interactive elements missing ARIA |
| CA_TD_001 | medium | test_debug | Test file naming convention mismatch |
| CA_TD_002 | low | test_debug | Test file missing test functions |
| CA_TD_003 | low | test_debug | Debug print/console.log in test files |
| CA_TD_004 | low | test_debug | Missing AAA pattern comments |
| CA_TD_005 | medium | test_debug | Missing tests/ directory |
| CA_TD_006 | low | test_debug | Missing test type subdirectory |
| CA_TD_007 | low | test_debug | Missing outputs/tests/ directory |
| CA_TD_008 | low | test_debug | Missing outputs/debugs/ directory |
| CA_COD_001 | high | codification | UUID v4 instead of v7 |
| CA_COD_002 | low | codification | Code field missing _code suffix |
| CA_COD_003 | low | codification | Code generation not following template format |
| CA_COD_004 | medium | codification | Missing human-readable code (Dual Identity Architecture) |
| CA_COD_005 | medium | codification | Auto-increment PK instead of UUID v7 |
| CA_CNAM_001 | low | coding_naming | Directory naming mismatch per stack (§2) |
| CA_CNAM_002 | low | coding_naming | Interface naming convention violation (§3) |
| CA_CNAM_003 | low | coding_naming | Abstract class missing Abstract prefix (§3) |
| CA_CNAM_004 | low | coding_naming | Constant not UPPER_SNAKE_CASE (§5) |
| CA_CNAM_005 | low | coding_naming | JSON/YAML key not snake_case (§5) |
| CA_ARCH_001 | medium | architecture | Potential circular dependency detected |
| CA_ARCH_002 | low | architecture | Service Locator pattern — prefer DI |
| CA_ARCH_003 | low | architecture | High coupling indicator — many imports |
| CA_ARCH_004 | medium | architecture | Framework coupling in domain layer |
| CA_ARCH_005 | low | architecture | Repository pattern detected (positive) |
| CA_ARCH_006 | low | architecture | Service pattern detected (positive) |
| CA_SYN_001 | critical | syntax | Mismatched bracket (e.g., `{` closed with `]`) |
| CA_SYN_002 | critical | syntax | Unmatched closing bracket |
| CA_SYN_003 | critical | syntax | Unclosed bracket (missing closing brace) |
| CA_SYN_004 | high | syntax | Mixed indentation (tabs and spaces) |
| CA_SYN_005 | low | syntax | Trailing whitespace detected |
| CA_SYN_006 | medium | syntax | Potentially missing semicolon (JS/C-like) |
| CA_SYN_007 | critical | syntax | Unclosed string quote |
| CA_SYN_008 | low | syntax | Blank line contains whitespace |

### Modular Structure Compliance Detail

The `modular_structure` category validates the **project folder structure** against `project-structure-modular-standard.md`:

| Check | Code | Severity | Filesystem Scan | Example Finding |
|-------|------|----------|-----------------|-----------------|
| **Required root folders** (§2) | CA_MDL_001 | medium | Checks `.agents`, `src/`, `tests/`, `docs/`, `.gitignore`, `README.md` | "Missing required root folder: '.agents'" |
| **Module manifest** (§5.1) | CA_MDL_002 | low | Checks `module.json`/`package.json` in `Modules/*/` | "Module 'Payment' missing manifest file" |
| **Module README** (§5) | CA_MDL_003 | low | Checks `README.md` in `Modules/*/` | "Module 'Payment' missing README.md" |
| **Module HMVC-P structure** (§5) | CA_MDL_004 | low | Checks Controllers/, Models/, Services/ exist | "Module 'Payment' has limited HMVC-P structure" |
| **Plural containers** (§8) | CA_MDL_005 | medium | Checks `Controller` vs `Controllers` naming | "Container folder 'Controller' should be plural: 'Controllers'" |
| **Root case** (§8.4) | CA_MDL_006 | low | Checks `App/` vs `app/` casing | "Root folder 'Config' should be lowercase: 'config'" |

**Detection algorithm** (`_check_modular_structure`):
1. Collect all directory paths from the file walk
2. Check root-level for required directories/files (§2)
3. Walk `Modules/*/`, `Plugins/*/`, `Widgets/*/` for internal structure (§5)
4. Verify container folders use plural naming (§8)
5. Verify root folder PascalCase/lowercase consistency (§8.4)

**Plus** the existing `modular` category (per-file) validates:
- **CA_MOD_001**: God files with 3+ classes (§1 SRP)
- **CA_MOD_002**: Direct `new Class()` cross-module instantiation (§11.1 M1)
- **CA_MOD_003**: Missing contract/interface for services (§11.3 P2)

### API Response Compliance Detail

The `api_response` category validates code against 6 rules from `api-standard.md`:

| Rule | Code | Severity | Detection Method | Example Finding |
|------|------|----------|-----------------|-----------------|
| **R1** | CA_API_001 | high | Detects `return {"success":…}` without `api_response()` | "Manual response dict instead of api_response()" |
| **R1** | CA_API_009 | high | Detects `api_response()` call missing `success`, `status_code`, `message`, `data`, or `request_id` | "api_response() missing required field 'data'" |
| **O1** | CA_API_002 | medium | Detects `request_id` that doesn't use `new_request_id()` | "request_id should be generated via new_request_id()" |
| **O3** | CA_API_003 | medium | Detects error response with `status_code >= 400` missing `error_code` | "Error response (status=500) missing error_code" |
| **R3/R4** | CA_API_005 | high | Detects error response with `data != None` or `success=True` | "Error response should have data=None, got '{...}'" |
| **§3** | CA_API_010 | low | Detects `message` exceeding 120 characters | "message exceeds 120 chars (245)" |

**Detection algorithm** (`_check_api_response`):
1. Scan each line for `api_response(` calls
2. Extract all keyword arguments via regex
3. Validate required fields exist (R1)
4. If `status_code >= 400`: check `data=None` (R3), `success=False` (R4), `error_code` present (O3)
5. Check `request_id` format starts with `req_` or `new_request_id(` (O1)
6. Check `message` length <= 120 chars (§3)
7. Also detect inline dicts with `{"success":…, "data":…}` pattern that bypass `api_response()`

**Correct usage** (api-standard.md §2 compliant):
```python
return api_response(
    success=True,
    status_code=200,
    message="User profile retrieved",
    data={"id": "usr_123", "name": "John"},
    request_id=new_request_id(),
)
```

**With pagination (P1/P2):**
```python
return api_response(
    success=True,
    status_code=200,
    message="Tasks retrieved",
    data=[{"id": "t1", "title": "Write docs"}],
    request_id=new_request_id(),
    links={
        "self": "/api/v1/tasks?page=2",
        "next": "/api/v1/tasks?page=3",
        "prev": "/api/v1/tasks?page=1",
    },
    pagination={"page": 2, "per_page": 20, "total": 95},
)
```

**With identity fields (ID5):**
```python
return api_response(
    success=True,
    status_code=200,
    message="Organization settings retrieved",
    data=settings_dict,
    request_id=new_request_id(),
    user_id="usr_456",            # only when authenticated
    organization_id="org_acme",   # only when org-scoped
    # tenant_id and workspace_id omitted (not relevant)
)
```

**Error response** (R3, R4, O3 compliant):
```python
return api_response(
    success=False,
    status_code=422,
    message="Validation failed",
    data=None,                    # R3: must be null on error
    request_id=new_request_id(),
    error_code="VAL_001",         # O3: required on error
)
```

### Compliance Score

```
score = 100
       - critical_count * 15
       - high_count * 10
       - medium_count * 5
       - low_count * 2
```

Ranges: 0–100. Higher = more compliant. Used to track improvement over time.

**Output:**
```json
{
  "compliance_score": 73,
  "scanned_files": 15,
  "summary": {"critical": 2, "high": 5, "medium": 3, "low": 2},
  "findings": [{
    "category": "file_structure",
    "severity": "medium",
    "file": "src/services.py",
    "line": 1,
    "code": "CA_STR_012",
    "message": "Missing @author tag in file header",
    "details": {"missing_tag": "@author"},
    "context": "",
    "remediation": "Add '@author' to file header DocBlock",
    "standard_ref": "coding-standard.md §1 (Class DocBlock)",
    "confidence": 0.95
  }, {
    "category": "docblock",
    "severity": "low",
    "file": "src/services.py",
    "line": 42,
    "code": "CA_DOC_021",
    "message": "Parameter 'user_id' missing @param tag in 'get_user'",
    "details": {"method": "get_user", "param": "user_id"},
    "context": "",
    "remediation": "Add '@param  int  user_id  description'",
    "standard_ref": "coding-standard.md §1 (Method DocBlock)",
    "confidence": 0.85
  }],
  "recommendations": {
    "gitignore_entries": [".env"],
    "secrets_to_rotate": ["AKIAIOSFODNN7..."]
  }
}
```

---

### code_status

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `path` | string | ✅ | — | Repository path (required) |
| `repo_id` | string | ❌ | — | Repository UUID |
| `include_metrics` | bool | ❌ | `true` | LOC, comment ratio, languages |
| `include_vcs` | bool | ❌ | `true` | Git branch, commit, changes |
| `include_symbols` | bool | ❌ | `true` | Symbol counts by kind |
| `language` | string | ❌ | — | Filter by language |

**Output:**
```json
{
  "summary": {
    "files": 42,
    "total_lines": 8500,
    "code_lines": 6200,
    "comment_lines": 1300,
    "comment_ratio": 15.3,
    "languages": {".py": 30, ".js": 12}
  },
  "symbols": {"class": 10, "function": 45},
  "graph_stats": {"nodes": 55, "edges": 120, "density": 0.04},
  "vcs": {"type": "git", "branch": "main", "commit": "a1b2c3d4", "uncommitted_changes": 3}
}
```

## ~/.aicoders/ Compliance (Self-Audit)

| Standard | Status | Evidence |
|----------|--------|----------|
| Architecture (DDD + Hexagonal) | ✅ | `api/` + `application/` + `core/` |
| API Standard (`api_response`) | ✅ | All 4 tools use `api_response()` |
| DI Pattern | ✅ | Constructor injection for all 4 services |
| Boundary Integrity | ✅ | DTOs: `AnalyzeResult`, `AuditFinding`, etc. |
| Coding Standard (naming, docblocks) | ✅ | snake_case methods, DocBlock header + method blocks |
| Error Handling | ✅ | Guard clauses + try/except + error codes |
| Structured Logging | ✅ | `CodeCortex.CodeAnalysis.*` logger names |
| Zero-Placeholder Policy | ✅ | No TODOs/FIXMEs in production code |
