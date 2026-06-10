# CodeGraph Domain - Test Cases

**Date:** 2026-05-29  
**Domain:** CodeGraph  
**Scope:** MCP Tools Testing  
**Focus:** Functional validation of 6 consolidated tools

---

## Test Case Matrix

### Tool 1: graph_search

#### Happy Path Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 1.1 | Find function by exact name | action="symbol", query="process_order", symbol_type="function" | Returns functions array with matching function |
| 1.2 | Find class by exact name | action="symbol", query="UserService", symbol_type="class" | Returns classes array with matching class |
| 1.3 | Find all symbols (any type) | action="symbol", query="auth", symbol_type="any" | Returns functions, classes, variables arrays |
| 1.4 | Fuzzy search for function | action="symbol", query="proces_order", fuzzy=true, edit_distance=2 | Returns functions with approximate matches |
| 1.5 | Semantic search | action="semantic", query="payment processing", repo_path="/path" | Returns semantically related code |
| 1.6 | Find callers relation | action="relation", query_type="callers", query="process_order", repo_id="uuid" | Returns list of callers |
| 1.7 | Find callees relation | action="relation", query_type="callees", query="process_order", repo_id="uuid" | Returns list of callees |
| 1.8 | Trace execution flow | action="trace_flow", target_symbol_id="node_id", repo_id="uuid", max_depth=5 | Returns hierarchical call tree |
| 1.9 | List modules | action="modular", modular_type="module", repo_id="uuid" | Returns list of modules |
| 1.10 | Pagination with cursor | action="symbol", query="get", limit=10, cursor="xyz" | Returns paginated results with next_cursor |

#### Error Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 1.11 | Invalid action | action="invalid_action" | Returns 400 error with error_code GRPH_008 |
| 1.12 | Missing repo_id for relation | action="relation", query_type="callers", repo_id=null | Returns 400 error "repo_id required" |
| 1.13 | Missing repo_id for trace_flow | action="trace_flow", repo_id=null | Returns 400 error "repo_id required" |
| 1.14 | Missing query for symbol | action="symbol", query=null | Returns empty results or error |
| 1.15 | Invalid symbol_type | action="symbol", symbol_type="invalid" | Returns 400 error or defaults to "any" |
| 1.16 | Max depth exceeded | action="relation", max_depth=20 | Caps at max_depth=10 internally |
| 1.17 | Limit exceeded | action="symbol", limit=500 | Caps at limit=200 internally |

#### Integration Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 1.18 | Search after graph_build | action="symbol", query="function", repo_path="/built/repo" | Returns symbols from built graph |
| 1.19 | Cross-repo search | action="symbol", query="shared", repo_path="/repo1" then "/repo2" | Returns symbols from both repos |
| 1.20 | Semantic search with embeddings | action="semantic", query="database connection" | Returns semantically similar code |

---

### Tool 2: graph_query

#### Happy Path Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 2.1 | Query direct callers | query_type="callers", target="process_order" | Returns list of direct callers |
| 2.2 | Query direct callees | query_type="callees", target="process_order" | Returns list of direct callees |
| 2.3 | Query all callers (recursive) | query_type="all_callers", target="process_order", max_depth=5 | Returns recursive caller tree |
| 2.4 | Query all callees (recursive) | query_type="all_callees", target="process_order", max_depth=5 | Returns recursive callee tree |
| 2.5 | Query imports | query_type="imports", target="UserService" | Returns files that import target |
| 2.6 | Query hierarchy | query_type="hierarchy", target="BaseController" | Returns parent and child classes |
| 2.7 | Query overrides | query_type="overrides", target="authenticate" | Returns methods that override target |
| 2.8 | Query call chain | query_type="chain", target="main" | Returns call chain from target |
| 2.9 | Query module dependencies | query_type="deps", target="auth_module" | Returns module dependencies |
| 2.10 | Query complexity | query_type="complexity", target="complex_function" | Returns cyclomatic complexity |
| 2.11 | Query dead code | query_type="dead_code", target="module" | Returns unused functions |
| 2.12 | Trace execution flow | query_type="trace_flow", target="entry_point", max_depth=5 | Returns execution flow tree |
| 2.13 | Trace shortest path | query_type="trace_path", target="start", end_node="end", repo_id="uuid" | Returns shortest path between nodes |
| 2.14 | Query with context disambiguation | query_type="callers", target="process", context="orders.py" | Returns callers from specific context |
| 2.15 | Query with direction filter | query_type="callers", target="process", direction="inbound" | Returns only inbound relationships |

#### Error Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 2.16 | Invalid query_type | query_type="invalid_type" | Returns 400 error or default behavior |
| 2.17 | Missing repo_id for trace_path | query_type="trace_path", repo_id=null | Returns 400 error "repo_id required" |
| 2.18 | Missing end_node for trace_path | query_type="trace_path", end_node=null | Returns 400 error or partial results |
| 2.19 | Invalid direction | direction="invalid" | Returns 400 error or defaults to "both" |
| 2.20 | Target not found | target="nonexistent_function" | Returns empty results or 404 |

#### Integration Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 2.21 | Query after graph_build | query_type="callers", target="built_function" | Returns callers from built graph |
| 2.22 | Cross-tool workflow | graph_search → graph_query → graph_audit | End-to-end analysis workflow |
| 2.23 | Query with repo_path scope | query_type="callers", target="function", repo_path="/path" | Returns callers from scoped repo |

---

### Tool 3: graph_audit

#### Happy Path Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 3.1 | Full audit (all types) | repo_id="uuid", audit_types=["all"] | Returns all audit findings |
| 3.2 | God nodes audit | repo_id="uuid", audit_types=["god_nodes"], degree_threshold=10 | Returns god nodes with in-degree > threshold |
| 3.3 | Security audit | repo_id="uuid", audit_types=["security"] | Returns security hygiene findings |
| 3.4 | Dead code audit | repo_id="uuid", audit_types=["dead_code"], limit=50 | Returns unused functions |
| 3.5 | Complexity audit | repo_id="uuid", audit_types=["complexity"], limit=50 | Returns most complex functions |
| 3.6 | Communities audit | repo_id="uuid", audit_types=["communities"] | Returns community clusters |
| 3.7 | Coupling audit | repo_id="uuid", audit_types=["coupling"], limit=50 | Returns surprising connections |
| 3.8 | Circular dependencies audit | repo_id="uuid", audit_types=["circular_deps"] | Returns circular dependency chains |
| 3.9 | Multiple audit types | repo_id="uuid", audit_types=["god_nodes", "security", "dead_code"] | Returns findings for specified types |
| 3.10 | Audit with markdown summary | repo_id="uuid", include_summary=true | Returns findings + markdown report |
| 3.11 | Custom threshold | repo_id="uuid", audit_types=["god_nodes"], degree_threshold=20 | Returns god nodes with custom threshold |
| 3.12 | Scoped audit with repo_path | repo_id="uuid", repo_path="/subdir", audit_types=["dead_code"] | Returns dead code in scoped path |

#### Error Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 3.13 | Missing repo_id | repo_id=null | Returns 400 error |
| 3.14 | Invalid audit_type | audit_types=["invalid_type"] | Returns empty results for invalid type |
| 3.15 | Negative threshold | degree_threshold=-5 | Returns 400 error or defaults to 10 |
| 3.16 | Limit too high | limit=10000 | Caps at reasonable limit internally |

#### Integration Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 3.17 | Audit after graph_build | repo_id="uuid" from graph_build | Returns audit findings for built graph |
| 3.18 | Audit with community detection | audit_types=["communities", "coupling"] | Returns community + coupling analysis |
| 3.19 | Incremental audit | audit_types=["security"] then audit_types=["god_nodes"] | Returns incremental findings |

---

### Tool 4: graph_build

#### Happy Path Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 4.1 | Basic graph build | repo_path="/path/to/repo" | Returns build stats + repo_id |
| 4.2 | Build with modular detection | repo_path="/path", detect_modular=true | Returns modular structure analysis |
| 4.3 | Build with dependency graph | repo_path="/path", build_dependency_graph=true | Returns module dependency graph |
| 4.4 | Build with core contracts | repo_path="/path", include_core_contracts=true | Includes core/Contracts/ nodes |
| 4.5 | Build with HMVC-P scan | repo_path="/path", scan_hmvc_p=true | Returns HMVC-P structure |
| 4.6 | Build with custom max_depth | repo_path="/path", max_depth=10 | Scans submodules to custom depth |
| 4.7 | Build without cache | repo_path="/path", use_cache=false | Forces fresh build |
| 4.8 | Build with stats | repo_path="/path", include_stats=true | Returns node/edge counts |
| 4.9 | Build with provided repo_id | repo_path="/path", repo_id="custom-uuid" | Uses provided repo_id |
| 4.10 | Build existing repo (cache hit) | repo_path="/path", use_cache=true | Returns cached results if recent |

#### Error Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 4.11 | Invalid path | repo_path="/nonexistent/path" | Returns 400 error "Path not found" |
| 4.12 | Path is file not directory | repo_path="/path/to/file.py" | Returns 400 error |
| 4.13 | Empty repository | repo_path="/empty/repo" | Returns build with 0 nodes/edges |
| 4.14 | Permission denied | repo_path="/protected/path" | Returns 403 error or file system error |

#### Integration Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 4.15 | Build then query | graph_build → graph_query | Query works on built graph |
| 4.16 | Build then audit | graph_build → graph_audit | Audit works on built graph |
| 4.17 | Rebuild after code changes | graph_build → modify code → graph_build (use_cache=false) | Updated graph reflects changes |

---

### Tool 5: graph_relationship

#### Happy Path Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 5.1 | Explore all relationships | repo_id="uuid", target_node="UserService" | Returns all relationships |
| 5.2 | Filter by relation type | repo_id="uuid", target_node="UserService", relation_type=["calls"] | Returns only CALLS relationships |
| 5.3 | Explore inbound only | repo_id="uuid", target_node="UserService", direction="inbound" | Returns only incoming relationships |
| 5.4 | Explore outbound only | repo_id="uuid", target_node="UserService", direction="outbound" | Returns only outgoing relationships |
| 5.5 | Explore with depth | repo_id="uuid", target_node="UserService", depth=2 | Returns relationships at depth 2 |
| 5.6 | Filter by modular type | repo_id="uuid", target_node="UserService", modular_type="service" | Returns only service relationships |
| 5.7 | Include community detection | repo_id="uuid", target_node="UserService", include_community=true | Returns relationships + community info |
| 5.8 | Filter by confidence | repo_id="uuid", target_node="UserService", min_confidence="EXTRACTED" | Returns only high-confidence relationships |
| 5.9 | Pagination | repo_id="uuid", target_node="UserService", limit=50, cursor="xyz" | Returns paginated results |
| 5.10 | Multiple relation types | repo_id="uuid", target_node="UserService", relation_type=["calls", "imports"] | Returns CALLS + IMPORTS relationships |

#### Error Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 5.11 | Missing repo_id | repo_id=null | Returns 400 error |
| 5.12 | Missing target_node | target_node=null | Returns 400 error |
| 5.13 | Invalid direction | direction="invalid" | Returns 400 error or defaults to "both" |
| 5.14 | Invalid confidence | min_confidence="invalid" | Returns 400 error or defaults |
| 5.15 | Depth too high | depth=20 | Caps at reasonable depth internally |

#### Integration Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 5.16 | Explore after graph_build | repo_id from graph_build | Explores relationships in built graph |
| 5.17 | Cross-tool workflow | graph_search → graph_relationship → graph_refactor | End-to-end exploration workflow |

---

### Tool 6: graph_refactor

#### Happy Path Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 6.1 | Impact analysis | repo_id="uuid", action="impact", refactor_type="split_module", target_node="UserService" | Returns impact analysis |
| 6.2 | Preview refactor | repo_id="uuid", action="preview", refactor_type="extract_component", target_node="AuthService" | Returns preview of changes |
| 6.3 | Apply refactor (dry run) | repo_id="uuid", action="apply", refactor_type="reroute_dependency", target_node="PaymentService", dry_run=true | Returns simulation |
| 6.4 | Apply refactor (live) | repo_id="uuid", action="apply", refactor_type="extract_interface", target_node="Validator", dry_run=false | Applies changes |
| 6.5 | Split module refactor | repo_id="uuid", action="impact", refactor_type="split_module", target_node="Utils" | Returns split impact |
| 6.6 | Extract component refactor | repo_id="uuid", action="preview", refactor_type="extract_component", target_node="AuthHandler" | Returns component extraction preview |
| 6.7 | Reroute dependency refactor | repo_id="uuid", action="impact", refactor_type="reroute_dependency", target_node="Database" | Returns rerouting impact |
| 6.8 | Extract interface refactor | repo_id="uuid", action="preview", refactor_type="extract_interface", target_node="PaymentGateway" | Returns interface extraction preview |
| 6.9 | Inline module refactor | repo_id="uuid", action="impact", refactor_type="inline_module", target_node="Helper" | Returns inlining impact |
| 6.10 | Refactor with options | repo_id="uuid", action="preview", refactor_type="split_module", target_node="Service", options={"split_by": "domain"} | Returns preview with custom options |

#### Error Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 6.11 | Missing repo_id | repo_id=null | Returns 400 error |
| 6.12 | Invalid action | action="invalid_action" | Returns 400 error |
| 6.13 | Invalid refactor_type | refactor_type="invalid_type" | Returns 400 error |
| 6.14 | Missing target_node | target_node=null | Returns 400 error |
| 6.15 | Invalid options | options={"invalid": "value"} | Returns 400 error or ignores invalid options |

#### Integration Scenarios

| ID | Scenario | Parameters | Expected Result |
|----|-----------|------------|-----------------|
| 6.16 | Refactor after audit | graph_audit → graph_refactor | Refactor based on audit findings |
| 6.17 | Impact → Preview → Apply workflow | action="impact" → action="preview" → action="apply" | Complete refactor workflow |
| 6.18 | Refactor with relationship exploration | graph_relationship → graph_refactor | Refactor based on relationship analysis |

---

## CLI Test Cases

**Finding:** CodeGraph has **no CLI commands** - MCP-only interface.

**Test Result:** N/A (CLI not implemented)

**Recommendation:** Document that CodeGraph is MCP-only, or implement CLI commands for common operations.

---

## Test Execution Plan

### Priority 1: Critical Path Tests (Must Pass)

1. graph_search - All 5 actions (symbol, relation, trace_flow, modular, semantic)
2. graph_query - Core query types (callers, callees, hierarchy, trace_flow)
3. graph_audit - All 7 audit types
4. graph_build - Basic build with stats
5. graph_relationship - Basic exploration
6. graph_refactor - Impact analysis

### Priority 2: Integration Tests (Should Pass)

7. graph_build → graph_query workflow
8. graph_build → graph_audit workflow
9. graph_search → graph_query workflow
10. graph_audit → graph_refactor workflow

### Priority 3: Edge Cases (Nice to Have)

11. All error scenarios
12. Pagination scenarios
13. Cross-repo scenarios
14. Large dataset scenarios

---

## Test Coverage Goals

- **Minimum:** 20 critical scenarios (Priority 1)
- **Ideal:** 50+ scenarios (Priority 1 + 2)
- **Comprehensive:** All 80+ scenarios (Priority 1 + 2 + 3)

**Current Status:** Test cases designed, ready for execution.
