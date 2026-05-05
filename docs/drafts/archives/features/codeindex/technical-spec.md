# A.E.G.I.S <small>CODEWORK v0.1.0</small>
# CodeIndex: Technical Specification

This document defines the semantic indexing requirements and AST parsing standards for the CodeCortex engine.

## 📋 Functional Requirements

### 1. Multi-Language AST Parsing
- **Grammar Support**: Must support 20+ languages via Tree-Sitter (Python, JS/TS, Go, Rust, Java, C++, Ruby, PHP, etc.).
- **Incremental Parsing**: Support for partial parsing of large files to maintain responsiveness.
- **Source Mapping**: Every extracted symbol must include precise line and column coordinates (`start_line`, `end_line`).

### 2. Symbol Extraction
- **Classes**: Name, bases (inheritance), docstrings.
- **Functions/Methods**: Name, arguments, decorators, return types, and internal call sites.
- **Variables**: Globally scoped constants and significant local declarations.
- **Imports**: Mapping of external dependencies and internal module references.

### 3. Framework Intelligence
- **Heuristic Detection**: Automatic detection of framework patterns (e.g., Next.js Page components, Laravel Controllers).
- **Metadata Enrichment**: Adding "Framework Flags" to symbols to assist in architectural classification.

## 🛡️ Operational Constraints

- **Timeout Guard**: Maximum 15 seconds per file to prevent hangs on malicious or complex syntax trees.
- **Memory Guard**: Skip files larger than 5MB.
- **Native Fallback**: If Tree-Sitter is unavailable, provide basic indexing via native language tools (e.g., Python `ast` module).
