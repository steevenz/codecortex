# CodeCortex Repository Domain

## Overview
The **Repository Domain** is responsible for physical codebase discovery, file tracking, and Git history synchronization. It serves as the foundation for the CodeCortex pipeline by providing a normalized view of the source files.

## Architecture
This domain follows the **CODDY Modular Monolith** standard with Proactive Domain Segregation:

- **api/**: External interface layer. Contains MCP tool registrations.
- **application/**: Orchestration layer. Contains the `RepositoryService` and structural analysis logic.
- **core/**: Domain logic and value objects. Contains DTOs and pure models.
- **infrastructure/**: Implementation details. Handles file system reading, Git history extraction, and configuration parsing.

## Key Components
- **RepositoryService**: The primary entry point for syncing repositories.
- **GitHistoryWorker**: Extracts commit metadata and links it to files.
- **RepoStructureAnalyzer**: Traverses directory trees with gitignore awareness.
- **FileReader**: Standardized file reading with hash calculation.

## Dependency Injection
All services require a `DatabaseManager` instance and follow constructor injection patterns.
