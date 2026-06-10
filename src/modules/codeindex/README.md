# CodeCortex CodeIndex Domain

## Overview
The **CodeIndex Domain** is the parsing and indexing engine for CodeCortex. It uses tree-sitter to extract AST symbols, resolve scopes, resolve imports, and generate embeddings for semantic search across 22 programming languages and 11 framework parsers.

## Architecture
DDD + Hexagonal Architecture:
- **api/**: MCP tool registrations (1 tool: `index_repository`)
- **services/**: Indexing orchestration and framework detection
- **parsers/**: Language-specific tree-sitter parsers (22 languages) and framework parsers (11 frameworks)
- **core/**: Converters and data types

## Supported Languages (22)
Python, TypeScript, TSX, JavaScript, C, C++, C#, Go, Rust, Java, Kotlin, Scala, Swift, Ruby, PHP, Elixir, Dart, Haskell, Perl, COBOL, CSS, Vue

## Supported Frameworks (11)
Angular, ASP.NET, Django, Express, Flutter, Laravel, NestJS, Next.js, Rails, React, Symfony, Vue

## Key Components
- **CodeIndexService**: Primary indexing orchestration with incremental and parallel processing
- **TreeSitterParser**: Unified tree-sitter parsing for all 22 languages
- **ScopeResolver**: Variable/function/class scope resolution
- **ImportResolver**: Resolve imports across the codebase (including wildcards)
- **EmbeddingGenerator**: CodeBERT/sentence-transformers embeddings for semantic search
- **FrameworkDetector**: Auto-detect project frameworks
- **WorkerPool**: Parallel file processing with configurable concurrency

## Features
- Incremental indexing (only changed files)
- Parallel processing (configurable worker threads)
- AST caching with LRU eviction
- Scope resolution with nested and global support
- Wildcard import resolution (`from module import *`)
- Semantic embeddings for natural language code search

## Tools
| Tool | Description |
|------|-------------|
| `index_repository` | Index a repository: AST parsing, symbol extraction, and optional embeddings |

## Dependencies
- **coderepository**: Repository metadata and file discovery
- **codegraph**: Graph service for relationship extraction during indexing
- **core**: Tree-sitter manager, database, errors, telemetry, token economy
