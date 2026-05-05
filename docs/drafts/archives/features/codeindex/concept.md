# A.E.G.I.S <small>CODEWORK v0.1.0</small>
# CodeIndex: Concept

The **CodeIndex** domain is the semantic brain of CodeCortex. It transforms raw source code into a structured, queryable set of symbols and relationships using advanced AST parsing.

## 📄 Overview

CodeIndex goes beyond file-level metadata to understand the *content* and *intent* of the code. By parsing the Abstract Syntax Tree (AST), it identifies the building blocks of the software—classes, functions, interfaces, and variables—and maps their internal structure.

### Key Philosophy: "Semantic Depth"
CodeIndex ensures that CodeCortex doesn't just see a file, but understands the logic within it:
- **Symbolic Resolution**: Identifying definitions and references.
- **Structural Nesting**: Understanding the hierarchy of components (e.g., methods within classes).
- **Metadata Awareness**: Capturing signatures, docstrings, and decorators for rich context.

### Business Value
- **Intelligent Search**: Search for code by its actual function name or type, not just string matching.
- **Contextual Awareness**: Provides AI agents with the exact location and signature of logic they need to modify.
- **Language Agnostic**: A single interface for 20+ languages.
