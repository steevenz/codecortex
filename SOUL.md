# SOUL.md - CodeCortex MCP

## Project Purpose
To provide a production-grade, multi-IDE shared MCP server for advanced codebase intelligence, indexing, and refactoring, powered by Aegis Codework standards.

## Vibe & Voice
- **Architectural Excellence**: Modular Monolith, DDD, Loose Coupling.
- **Reliability First**: No deadlocks, no silent hangs, robust resource management.
- **Cyber-Aware**: Secure API-key authentication, path validation, and redacting sensitive info.

## Architectural Non-Negotiables
1. **Shared Proxy Pattern**: A single Node.js proxy (`index.js`) manages the lifecycle of a persistent Python backend (`main.py`).
2. **Atomic Operations**: All database writes and refactors must be atomic and handle concurrency via SQLite write-ahead logging (WAL) or locks.
3. **Async Everywhere**: Backend handlers must be strictly `async` to prevent blocking the event loop during heavy I/O or analysis.
4. **Environment-Driven**: Bootstrap and transport settings are governed by `.env` for maximum portability across IDEs.
5. **Zero-Hallucination Logging**: Traceability via `request_id` and structured JSON logs.
