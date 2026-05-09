# CodeIndex: LLM Impact

> How CodeIndex enriches LLM code understanding

## Before CodeIndex

An LLM with only file content can:
- Read individual files sequentially
- Guess at cross-file relationships
- Miss symbols defined in other files
- Not know which functions are unused or which imports are missing

## After CodeIndex

The LLM gains structured knowledge:

1. **Symbol Registry** — All functions, classes, and variables with their exact locations and signatures. No more guessing where a symbol is defined.

2. **Import Graph** — Every file knows what it imports and what imports it. The LLM can trace dependencies without reading every file.

3. **Scope Chains** — For any symbol reference, the LLM can see which scope it resolves to (local, enclosing class, module, imported).

4. **Type Information** — Signatures, docstrings, and decorators provide rich type context. For typed languages, the full type annotation is preserved.

5. **Framework Awareness** — The LLM knows if a function is a FastAPI route, a React hook, a Django model method, etc. This enables framework-aware suggestions.

## Concrete Improvements

| Capability | Without CodeIndex | With CodeIndex |
|-----------|------------------|----------------|
| Find function definition | Grep entire codebase | O(1) lookup from symbol table |
| Understand inheritance | Read all parent classes manually | Heritage extraction provides full hierarchy tree |
| Trace dependency chain | Manual file-by-file | Import edges provide graph walk |
| Refactor safety | Guess impact zone | Impact analysis shows exact call sites |
| Code generation context | Limited to open files | Full symbol registry available |
