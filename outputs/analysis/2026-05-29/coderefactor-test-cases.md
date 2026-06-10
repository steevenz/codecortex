# CodeRefactor Test Cases

**Date:** 2026-05-29
**Scope:** MCP tool `code_refactor` (12 actions)
**Test Coverage Goal:** 50+ scenarios across all actions

---

## Test Case Matrix

### Action: impact (Blast Radius Analysis)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| I.1 | Basic impact analysis for function | action="impact", target_symbol="src/utils.py::calculate_sum" | Returns blast radius with direct/transitive callers |
| I.2 | Impact analysis for class | action="impact", target_symbol="src/models/user.py::User" | Returns blast radius for class usage |
| I.3 | Impact for widely used symbol | action="impact", target_symbol="src/core/base.py::BaseModel" | High risk level, many affected files |
| I.4 | Impact for unused symbol | action="impact", target_symbol="src/deprecated/old.py::unused_func" | Low risk, zero or few callers |
| I.5 | Impact with line number format | action="impact", target_symbol="src/utils.py:42" | Parses line format, returns impact |

#### Error Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| I.E1 | Invalid repo_id | action="impact", repo_id="invalid-uuid" | Error: Repository not found |
| I.E2 | Non-existent symbol | action="impact", target_symbol="src/utils.py::nonexistent" | Error: Symbol not found or zero impact |
| I.E3 | Invalid target format | action="impact", target_symbol="invalid::format::extra" | Error: Invalid target format |
| I.E4 | Empty target_symbol | action="impact", target_symbol="" | Error: Target symbol required |

---

### Action: rename (Symbol Rename)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| R.1 | Rename function (Python) | action="rename", changes={"new_name": "calculate_total"} | Renames in all files, skips strings/comments |
| R.2 | Rename class (Python) | action="rename", changes={"new_name": "CustomerModel"} | Renames class definition and references |
| R.3 | Rename with dry_run | action="rename", dry_run=True, changes={"new_name": "new_name"} | Returns preview diff without applying |
| R.4 | Rename in JavaScript | action="rename", changes={"new_name": "calculateTotal"} | Renames in JS files, skips template strings |
| R.5 | Rename in TypeScript | action="rename", changes={"new_name": "UserInterface"} | Renames in TS files |

#### Error Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| R.E1 | Missing new_name | action="rename", changes={} | Error: changes.new_name required |
| R.E2 | Empty new_name | action="rename", changes={"new_name": ""} | Error: new_name cannot be empty |
| R.E3 | Invalid repo_id | action="rename", repo_id="invalid" | Error: Repository not found |
| R.E4 | Symbol not found | action="rename", target_symbol="invalid::func" | Error: Symbol not found |

---

### Action: move (Move Code Element)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| M.1 | Move function to new file | action="move", changes={"target_file": "src/utils/helpers.py"} | Moves function, updates imports |
| M.2 | Move class to domain module | action="move", changes={"target_file": "src/domain/billing/models.py"} | Moves class, updates all importers |
| M.3 | Move with dry_run | action="move", dry_run=True, changes={"target_file": "new.py"} | Returns preview without applying |
| M.4 | Move to existing file | action="move", changes={"target_file": "src/utils/common.py"} | Appends to existing file |

#### Error Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| M.E1 | Missing target_file | action="move", changes={} | Error: changes.target_file required |
| M.E2 | Source not found | action="move", target_symbol="nonexistent.py::func" | Error: Source not found |
| M.E3 | Target directory invalid | action="move", changes={"target_file": "/invalid/path.py"} | Error: Invalid target path |

---

### Action: change_signature (Change Function Signature)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| CS.1 | Add parameter with default | action="change_signature", changes={"add_params": [{"name": "debug", "default_value": "False"}]} | Adds param to signature and call sites |
| CS.2 | Remove parameter | action="change_signature", changes={"remove_params": ["old_param"]} | Removes param from signature and call sites |
| CS.3 | Reorder parameters | action="change_signature", changes={"reorder": ["c", "a", "b"]} | Reorders params in signature and calls |
| CS.4 | Add multiple params | action="change_signature", changes={"add_params": [{"name": "x"}, {"name": "y"}]} | Adds multiple params |
| CS.5 | Dry run signature change | action="change_signature", dry_run=True, changes={"add_params": [...]} | Returns preview diff |

#### Error Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| CS.E1 | Function not found | action="change_signature", target_symbol="invalid.py::func" | Error: Function not found |
| CS.E2 | Invalid parameter name | action="change_signature", changes={"add_params": [{"name": ""}]} | Error: Invalid parameter name |
| CS.E3 | No parameters node | action="change_signature", target_symbol="lambda_func" | Error: Function has no parameters node |

---

### Action: extract_function (Extract Code to Function)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| EF.1 | Extract basic block | action="extract_function", changes={"new_name": "helper", "start_line": 10, "end_line": 20} | Creates new function, replaces with call |
| EF.2 | Extract with variable analysis | action="extract_function", changes={"new_name": "validator", "start_line": 15, "end_line": 25} | Auto-detects parameters from used variables |
| EF.3 | Extract from class method | action="extract_function", target_symbol="src/class.py:42", changes={...} | Extracts from method context |
| EF.4 | Dry run extract | action="extract_function", dry_run=True, changes={...} | Returns preview without applying |

#### Error Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| EF.E1 | Invalid line range | action="extract_function", changes={"start_line": 100, "end_line": 10} | Error: Invalid line range |
| EF.E2 | Empty code block | action="extract_function", changes={"start_line": 5, "end_line": 5} | Error: No code to extract |
| EF.E3 | File not found | action="extract_function", target_symbol="nonexistent.py" | Error: File not found |

---

### Action: inline_function (Inline Function at Call Sites)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| IF.1 | Inline simple function | action="inline_function", target_symbol="src/utils.py::simple_func" | Replaces calls with function body, removes definition |
| IF.2 | Inline with parameters | action="inline_function", target_symbol="src/utils.py::param_func" | Substitutes parameter values in inlined code |
| IF.3 | Inline multiple call sites | action="inline_function", target_symbol="src/common.py::used_func" | Replaces all call sites |
| IF.4 | Dry run inline | action="inline_function", dry_run=True, target_symbol="..." | Returns preview without applying |

#### Error Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| IF.E1 | Function not found | action="inline_function", target_symbol="invalid::func" | Error: Function not found |
| IF.E2 | Cannot parse body | action="inline_function", target_symbol="src/broken.py::malformed" | Error: Cannot parse function body |
| IF.E3 | No call sites | action="inline_function", target_symbol="src/unused.py::unused" | Warning: No call sites found |

---

### Action: rename_file (Rename File)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| RF.1 | Rename Python file | action="rename_file", changes={"new_path": "src/utils/new_name.py"} | Renames file, updates all imports |
| RF.2 | Rename JS file | action="rename_file", changes={"new_path": "src/components/NewComponent.tsx"} | Renames TSX file, updates imports |
| RF.3 | Rename with dry_run | action="rename_file", dry_run=True, changes={...} | Returns preview without applying |
| RF.4 | Rename to different directory | action="rename_file", changes={"new_path": "src/domain/billing/service.py"} | Moves and renames, updates imports |

#### Error Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| RF.E1 | Source not found | action="rename_file", target_symbol="nonexistent.py" | Error: Source not found |
| RF.E2 | Target already exists | action="rename_file", changes={"new_path": "existing.py"} | Error: Target already exists |
| RF.E3 | Missing new_path | action="rename_file", changes={} | Error: changes.new_path required |

---

### Action: rename_folder (Rename Directory)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| RFldr.1 | Rename small folder | action="rename_folder", changes={"new_name": "new_module"} | Renames directory, updates all imports |
| RFldr.2 | Rename with dry_run | action="rename_folder", dry_run=True, changes={...} | Returns preview without applying |
| RFldr.3 | Rename nested folder | action="rename_folder", target_symbol="src/old/nested", changes={"new_name": "new"} | Renames nested directory |

#### Error Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| RFldr.E1 | Directory not found | action="rename_folder", target_symbol="nonexistent" | Error: Directory not found |
| RFldr.E2 | Target already exists | action="rename_folder", changes={"new_name": "existing"} | Error: Target already exists |
| RFldr.E3 | Large folder warning | action="rename_folder", target_symbol="large_folder", changes={...} | Warning: >50 files affected |

---

### Action: move_file (Move File)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| MF.1 | Move file (copy) | action="move_file", changes={"target_dir": "src/utils/", "delete_source": false} | Copies file, updates imports |
| MF.2 | Move file (move) | action="move_file", changes={"target_dir": "src/utils/", "delete_source": true} | Moves file, updates imports |
| MF.3 | Move with dry_run | action="move_file", dry_run=True, changes={...} | Returns preview without applying |
| MF.4 | Move to new directory | action="move_file", changes={"target_dir": "src/domain/billing/"} | Creates directory if needed, moves file |

#### Error Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| MF.E1 | Source not found | action="move_file", target_symbol="nonexistent.py" | Error: Source not found |
| MF.E2 | Target exists | action="move_file", changes={"target_dir": "existing/"} | Error: Target already exists |
| MF.E3 | Missing target_dir | action="move_file", changes={} | Error: changes.target_dir required |

---

### Action: modularize (Split Monolith into DDD Modules)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| MOD.1 | Modularize Python file | action="modularize", changes={"target_domain": "src/domain/", "strategy": "auto"} | Splits into domain-aligned modules |
| MOD.2 | Modularize with custom domain | action="modularize", changes={"target_domain": "src/domain/billing/"} | Splits into billing domain |
| MOD.3 | Modularize with dry_run | action="modularize", dry_run=True, changes={...} | Returns preview without applying |
| MOD.4 | Modularize mixed domain file | action="modularize", target_symbol="monolith.py", changes={...} | Detects multiple domains, splits accordingly |

#### Error Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| MOD.E1 | Source not found | action="modularize", target_symbol="nonexistent.py" | Error: Source not found |
| MOD.E2 | Unsupported language | action="modularize", target_symbol="file.unknown" | Error: Unsupported language |
| MOD.E3 | No extractable symbols | action="modularize", target_symbol="empty.py" | Error: No extractable symbols found |

---

### Action: preview (Workflow Alias)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| PR.1 | Preview rename | action="preview", changes={"preview_action": "rename", "new_name": "new"} | Returns rename preview with dry_run=True |
| PR.2 | Preview move | action="preview", changes={"preview_action": "move", "target_file": "new.py"} | Returns move preview |
| PR.3 | Preview with default action | action="preview", changes={} | Defaults to rename preview |

---

### Action: apply (Workflow Alias)

#### Happy Path Scenarios
| ID | Description | Parameters | Expected Result |
|----|-------------|------------|-----------------|
| AP.1 | Apply rename | action="apply", changes={"apply_action": "rename", "new_name": "new"} | Executes rename with dry_run=False |
| AP.2 | Apply move | action="apply", changes={"apply_action": "move", "target_file": "new.py"} | Executes move with dry_run=False |
| AP.3 | Apply with default action | action="apply", changes={} | Defaults to rename apply |

---

## Integration Scenarios

| ID | Description | Workflow | Expected Result |
|----|-------------|----------|-----------------|
| INT.1 | Full rename workflow | impact → preview → apply | Safe rename with impact analysis |
| INT.2 | Full move workflow | impact → preview → apply | Safe move with impact analysis |
| INT.3 | Batch file operations | rename_file → move_file | Sequential file operations |
| INT.4 | Modularize after analysis | impact → modularize | DDD split with impact awareness |
| INT.5 | Extract then inline | extract_function → inline_function | Test refactoring reversibility |

---

## Test Execution Priority

### Critical (Must Test First)
1. I.1 - Basic impact analysis
2. R.1 - Basic rename (Python)
3. R.3 - Rename with dry_run
4. RF.1 - Rename file
5. RF.3 - Rename file with dry_run

### High Priority
6. M.1 - Move function
7. CS.1 - Add parameter
8. EF.1 - Extract function
9. IF.1 - Inline function
10. MOD.1 - Modularize file

### Medium Priority
11-30. All other happy path scenarios
31-40. Error scenarios for each action
41-50. Integration scenarios

---

## Total Test Count: 50+ Scenarios

- **Happy Path:** 30 scenarios
- **Error Scenarios:** 15 scenarios
- **Integration Scenarios:** 5 scenarios
- **Total:** 50 scenarios

**Coverage Goals:**
- Minimum: 10 critical scenarios
- Ideal: All 50 scenarios
- Success Criteria: 80% pass rate (40/50)
