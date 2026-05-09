# CodeIndex: Semantic Code Indexing

> **Domain:** CodeIndex
> **Package:** `src/domain/codeindex/`

## Business Context

CodeIndex is the **parser and extractor** layer. It transforms raw source code files into structured, queryable data (symbols, imports, relationships) that powers every other domain. Without CodeIndex, CodeGraph would have no symbols to graph, CodeRefactor would have no references to rename, and semantic search would have nothing to index.

## Why This Exists

- **AST > Regex:** Regular expressions can't understand nested scopes, resolve qualified names, or distinguish between a function definition and a function call. Tree-Sitter gives us a concrete syntax tree that matches the language parser.
- **Cross-File Understanding:** A class defined in one file and extended in another — CodeIndex's scope resolution connects them.
- **Language Agnosticism:** 20+ languages through a unified parsing API. One pipeline, many grammars.
- **Performance:** LRU AST caching and thread pool parallelization make indexing large codebases feasible.

## Theoretical Foundation

- **Tree-Sitter:** Incremental, error-tolerant parsing. Unlike ANTLR or hand-written parsers, Tree-Sitter can parse incomplete or syntactically invalid files (common during development) and still produce a useful AST.
- **Abstract Syntax Tree (AST):** A tree representation of source code where each node is a syntactic construct (function definition, variable declaration, class declaration). The AST omits semicolons, whitespace, and other purely syntactic tokens.
- **Symbol Resolution:** The process of mapping a name reference to its definition, accounting for scope boundaries, imports, and the order of declarations.

---

## Related Sub-Features

- [Tree-Sitter Parsing](sub-features/tree-sitter-parsing/concept.md)
- [Framework Detection](sub-features/framework-detection/concept.md)
- [Semantic Search](sub-features/semantic-search/concept.md)
- [Scope Resolution](sub-features/scope-resolution/concept.md)
- [Import Resolution](sub-features/import-resolution/concept.md)
- [AST Cache](sub-features/ast-cache/concept.md)
- [Worker Pool](sub-features/worker-pool/concept.md)
