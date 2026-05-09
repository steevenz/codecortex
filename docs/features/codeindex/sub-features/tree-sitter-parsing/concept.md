# Tree-Sitter Parsing

> **Source:** `src/domain/codeindex/infrastructure/parsers/`
> **Manager:** `TreeSitterManager` in tree-sitter infra

## Concept

Tree-Sitter is an incremental, error-tolerant parser generator and runtime. Unlike traditional parsers that fail on incomplete code, Tree-Sitter produces a Concrete Syntax Tree (CST) even with syntax errors, making it ideal for IDE-like code analysis.

## Why Tree-Sitter?

| Aspect | Tree-Sitter | Regex | Full Compiler Frontend |
|--------|------------|-------|----------------------|
| Error tolerance | High (produces partial tree) | N/A | Low (fails on errors) |
| Speed | Millisecond per file | Fast | Seconds per file |
| Language coverage | 20+ languages | Any text | 1 language |
| Nested scope | Yes | No | Yes |
| AST fidelity | Full CST | Flat text | Full |

## Implementation

- Each language has its own parser class in `src/domain/codeindex/infrastructure/parsers/`
- Parser classes implement a unified interface: `extract_functions()`, `extract_classes()`, `extract_imports()`, `extract_variables()`
- `TreeSitterManager` lazily loads parsers and manages the language → parser mapping
- Queries are pre-compiled language-specific S-expressions

## Language Support Matrix

| Language | Parser File | Functions | Classes | Imports | Variables |
|----------|------------|-----------|---------|---------|-----------|
| Python | `python.py` | ✅ | ✅ | ✅ | ✅ |
| TypeScript | `typescript.py` | ✅ | ✅ | ✅ | ✅ |
| JavaScript | `javascript.py` | ✅ | ✅ | ✅ | ✅ |
| JSX/TSX | `tsx.py` | ✅ | ✅ | ✅ | ✅ |
| Go | `go.py` | ✅ | ✅ | ✅ | ✅ |
| Rust | `rust.py` | ✅ | ✅ | ✅ | ✅ |
| Java | `java.py` | ✅ | ✅ | ✅ | ✅ |
| Kotlin | `kotlin.py` | ✅ | ✅ | ✅ | ✅ |
| PHP | `php.py` | ✅ | ✅ | ✅ | ✅ |
| Ruby | `ruby.py` | ✅ | ✅ | ✅ | ✅ |
| Swift | `swift.py` | ✅ | ✅ | ✅ | ✅ |
| Dart/Flutter | `dart.py` | ✅ | ✅ | ✅ | ✅ |
| C | `c.py` | ✅ | ✅ | ✅ | ✅ |
| C++ | `cpp.py` | ✅ | ✅ | ✅ | ✅ |
| C# | `c_sharp.py` | ✅ | ✅ | ✅ | ✅ |
| Elixir | `elixir.py` | ✅ | ✅ | ✅ | ✅ |
| Haskell | `haskell.py` | ✅ | ✅ | ✅ | ✅ |
| Perl | `perl.py` | ✅ | ✅ | ✅ | ✅ |
| Lua | `lua.py` | ✅ | ✅ | ✅ | ✅ |
| Zig | `zig.py` | ✅ | ✅ | ✅ | ✅ |
| Bash | `bash.py` | ✅ | ✅ | ✅ | ✅ |
| SQL | `sql.py` | ✅ | ✅ | ✅ | ✅ |
