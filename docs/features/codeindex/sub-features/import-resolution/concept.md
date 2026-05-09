# Import Resolution

> **Source:** `src/domain/codeindex/infrastructure/import_resolvers/`

## Concept

Import resolution maps import statements to the actual files and symbols they refer to. Each language has its own import semantics:

- **Python:** `from x import y` → `x.py` has `y`, or `x/__init__.py` exports `y`
- **TypeScript:** `import { X } from './y'` → `./y.ts` exports `X`
- **Go:** `import "pkg/path"` → Go module resolution
- **Rust:** `use crate::module::Item` → crate-relative path

## Architecture

```
import_resolvers/
├── __init__.py       # Dispatcher: selects resolver by file extension
├── python.py         # Python import resolution
├── typescript.py     # TypeScript/JS import resolution
├── go.py            # Go import resolution
├── rust.py          # Rust import resolution
├── java.py          # Java import resolution
├── php.py           # PHP import resolution
└── dart.py          # Dart/Flutter import resolution
```

Each resolver implements:
- `resolve_import(import_stmt, current_file) -> ResolvedImport` — maps import to file path
- `resolve_symbol(symbol_name, imports) -> ResolvedSymbol` — finds which import provides a symbol
- `get_source_file(specifier, base_path) -> Path` — resolves relative/absolute specifiers

## Wildcard Imports

Wildcard imports (`from os import *`) are resolved by reading the source module's `__all__` or by extracting all public symbols. Handled by `src/domain/codeindex/infrastructure/wildcard_imports.py`.
