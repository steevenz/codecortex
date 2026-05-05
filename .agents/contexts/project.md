---
name: codecortex
description: Architectural Intelligence Engine
owner: Steeven Andrian
version: 1.1.0
---

# Project Manifest

## Metadata
- **Domain**: Architectural Analysis / AI Coding Agent Infrastructure
- **Stack**: Python 3.11+, FastAPI, SQLite, Node.js (Proxy)
- **Standards**: Aegis Codework v4.1 (Modular Monolith / DDD)

## Repository Structure
- `src/domain/`: Bounded contexts (coderepository, codeindex, codegraph, graphify, refactor).
- `src/core/`: Shared utilities and cross-cutting concerns.
- `database/`: Persistence layer (Hub-and-Spoke).
- `scripts/server/js/`: Node.js shared-server orchestration.
- `.agents/`: Agentic governance and session state.

## Operational Modes
- **Stdio**: Standard MCP transport.
- **SSE/HTTP**: Production transport for shared multi-client access.
