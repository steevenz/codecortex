# Tree-Sitter Parsing

> **Source:** `src/domain/codeindex/infrastructure/parsers/`
> **Manager:** `src/core/tree_sitter_manager.py` -> `TreeSitterManager.get_language_safe()`

## Concept

Tree-Sitter is an incremental, error-tolerant parser generator and runtime. Unlike traditional parsers that fail on incomplete code, Tree-Sitter produces a Concrete Syntax Tree (CST) even with syntax errors, making it ideal for IDE-like code analysis.

## Why Tree-Sitter?

| Aspect | Tree-Sitter | Python `ast` | Regex |
|--------|------------|-------------|-------|
| Error tolerance | High (partial tree) | Low (syntax error = crash) | N/A |
| Speed | ~1ms per file | ~0.5ms per file | Fast |
| Languages | 27+ | 1 (Python only) | Any text |
| Nested scope | Yes | Yes | No |
| AST fidelity | Full CST | Full AST | Flat text |

## Architecture

```
TreeSitterParser (dispatch)
  +-- language_specific_parser (dedicated class per language)
  |   +-- PythonTreeSitterParser  -> python.py
  |   +-- JavascriptTreeSitterParser -> javascript.py
  |   +-- ...
  |   +-- TypescriptJSXTreeSitterParser -> typescriptjsx.py
  +-- _GenericFunctionParser (for non-TS languages)
  |   +-- vue -> parse_vue()
  |   +-- cobol -> parse_cobol()
  +-- generic_ts (for TS-without-dedicated-class)
      +-- parse_generic(path, language_name)  # julia, lua, objc, etc.
```

## Language Support Matrix

### Dedicated Tree-Sitter Parser (19 languages)

All 19 dedicated parsers now output the standard format consumed by the converter:
`functions[]`, `classes[]`, `variables[]`, `imports[]`, `function_calls[]` with `args`, `class_context`, `bases`, and `docstring`.

| Language | Source File | class_context | Notes |
|----------|-----------|---------------|-------|
| Python | `python.py` | Yes | `_get_class_context()` walks parent chain for method detection. Module-level docstring via `ast.get_docstring(tree)` fallback. Variables include `augmented_assignment` (x += 1). |
| JavaScript | `javascript.py` | Yes | JSDoc extraction via `_get_jsdoc_comment()` prev_sibling walk |
| TypeScript | `typescript.py` | Yes | JSDoc extraction via `_get_jsdoc_comment()` prev_sibling walk |
| TSX | `typescriptjsx.py` | Yes | JSDoc extraction via `_get_jsdoc_comment()` prev_sibling walk |
| Go | `go.py` | Yes | |
| Rust | `rust.py` | Yes | `_find_variables` with `(let_declaration pattern: (identifier) @name)` query (was hardcoded `"variables": []`) |
| C++ | `cpp.py` | Yes | |
| C | `c.py` | Yes | Full implementation (was STUB returning error). 180 lines. Functions, structs, enums, imports, calls, variables. |
| Java | `java.py` | Yes | |
| Ruby | `ruby.py` | Yes | |
| C# | `csharp.py` | Yes | |
| PHP | `php.py` | Yes | |
| Kotlin | `kotlin.py` | Yes | |
| Scala | `scala.py` | Yes | |
| Swift | `swift.py` | Yes | |
| Haskell | `haskell.py` | Yes | `args` extracted from tree-sitter parameter nodes (was hardcoded `[]`) |
| Dart/Flutter | `dart.py` | Yes | |
| Perl | `perl.py` | Yes | `args` extracted from tree-sitter parameter nodes (was hardcoded `[]`) |
| Elixir | `elixir.py` | Yes | Variables query: `(match left: (identifier))` -- only capture `=` assignments (was `(identifier)` capturing every node causing overflow). `args` extracted from parameter nodes. |

### Generic Tree-Sitter (6 languages)

Parsed via `parse_generic()` in `generic_ts.py`. All 6 now output standard format `functions[]`/`classes[]`/`variables[]`/`imports[]`/`function_calls[]` with `args`, `class_context`, `bases`. Previously they only output a `symbols` key (never stored in SQLite).

| Language | Language Name | class_context | Notes |
|----------|-------------|---------------|-------|
| Julia | `julia` | Yes | Standard format with all keys |
| Lua | `lua` | Yes | Standard format with all keys |
| Objective-C | `objc` | Yes | Standard format with all keys |
| PowerShell | `powershell` | Yes | Standard format with all keys |
| Verilog | `verilog` | Yes | Standard format with all keys |
| Zig | `zig` | Yes | Standard format with all keys |

### Non-Tree-Sitter (2 languages)

Parsed via dedicated functions without Tree-Sitter grammar.

| Language | Parser | Method |
|----------|--------|--------|
| Vue (`.vue`) | `parse_vue()` | Regex-based SFC structure extraction + tree-sitter JS/TS for script parsing. Outputs standard `functions[]`/`classes[]`/`variables[]`/`imports[]`/`function_calls[]` format (was `symbols` key). |
| Cobol (`.cob`, `.cbl`, `.cobol`, `.cpy`, `.copybook`) | `parse_cobol()` | Regex-based division parsing |

### CSS/SCSS Support

CSS/SCSS parsers existed but `ts_parsers` did not map `.css`, `.scss`, `.sass`, `.less` extensions. Now mapped and dispatched via `tree_sitter_parser.py`. CSS parser includes `(call_expression function: (function_name) @name)` query for `url()`, `var()`, `calc()` etc (was no calls extraction).

## Parser Cache Thread Safety

`_parser_cache` uses `threading.Lock` to prevent race conditions when multiple WorkerPool threads initialize parsers concurrently. The lock ensures that parser instances are created exactly once, eliminating double-create races.

## Python Fallback Chain

1. **Primary:** Tree-Sitter Python parser -> full AST with imports, classes, functions, calls, variables
2. **Fallback:** Python `ast` builtin (`_parse_python_builtin()` in `service.py`) -> triggered when Tree-Sitter grammar import fails
3. Both paths produce identical output schema, ensuring downstream consumers are unaffected
4. Python ast fallback now extracts:
   - Variables: `ast.Assign`, `ast.AnnAssign`, `ast.AugAssign`, tuple unpacking
   - class_context via pre-built range index (was always empty)
   - Module-level docstring via `ast.get_docstring(tree)`

## Class Context Detection

All 19 dedicated parsers + all 6 generic parsers support `class_context` detection, enabling:
- Correct `symbol_type = "method"` (not "function")
- Qualified `code_ref = "x.py:method:Calculator.add@5"`
- `parent_id` linking method -> class in the symbols table
- INHERITS edge from method to parent class
- Scope resolution tree building class -> method hierarchy

The Python parser's `_get_class_context()` walks up the tree-sitter CST from each function node:

```
function_definition
  +- parent: block
      +- parent: class_definition  <- found! -> return class name "Calculator"
```

## JSDoc Extraction (TypeScript + TSX)

`_get_jsdoc_comment()` walks `prev_sibling` chain from each function/class node to find adjacent comment blocks. Returns the JSDoc comment text as the `docstring` field. Previously `docstring: None` was hardcoded for JS/TS/TSX.
