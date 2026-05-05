# A.E.G.I.S <small>CODEWORK v0.1.0</small>
# Repository Management: Technical Specification

This document defines the functional and non-functional requirements for the Repository Management domain.

## 📋 Functional Requirements

### 1. Project Discovery
- **Recursive Traversal**: The system must recursively scan the provided root path.
- **GitIgnore Compliance**: Must support standard `.gitignore` patterns to exclude build artifacts, dependencies (e.g., `node_modules`), and hidden files.
- **Path Resolution**: Must resolve relative paths to absolute, normalized paths to prevent duplicates.

### 2. File Classification
- **Categorization**: Every discovered file must be classified into one of the following categories:
    - `code`: Source files (e.g., `.py`, `.ts`, `.go`).
    - `doc`: Documentation files (e.g., `.md`, `.txt`).
    - `config`: Configuration files (e.g., `.yaml`, `.json`, `.env`).
    - `binary`: Non-text assets (e.g., `.png`, `.exe`).
    - `other`: Catch-all for unrecognized types.

### 3. Manifest Management
- **Hash Tracking**: Calculate SHA-256 hashes for every file to detect changes.
- **State Persistence**: Store file metadata (size, path, last_modified) in the `files` and `manifest_entries` tables.

## 🛡️ Security & Constraints

- **Path Traversal**: Must block any attempt to index paths outside the authorized project root.
- **Sensitive Data**: Automatic exclusion of credential-bearing files (e.g., `.pem`, `id_rsa`).
- **Performance**: Scanning a 10,000-file repository should complete in under 5 seconds (excluding initial hashing).
