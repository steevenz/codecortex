# Myawesomeproject — Documentation

## Structure

```
docs/
├── drafts/           # Work in progress documents
├── archives/         # Deprecated documents
├── product/          # Product management artifacts
├── architecture/     # System architecture documentation
│   ├── concepts/     # Core philosophies & ADRs
│   ├── api/          # API documentation
│   ├── codebase/     # Code structure documentation
│   └── database/     # Database schemas
├── features/         # Feature-based documentation
├── guides/           # Setup, deployment, operations
│   ├── setup/
│   ├── deployment/
│   └── operations/
├── versions/         # Versioned documentation snapshots
├── glossary.md       # Domain & technical terms
└── index.md          # Executive summary
```

## Conventions

- All folder and file names use `lowercase-dashed` format
- Documentation must be written in English
- Update documentation when code changes
- Version snapshots aligned with Semantic Versioning 2.0.0 (see `../.version`)

## Getting Started

1. Start with `architecture/concepts/` to define core principles
2. Document features in `features/{feature-name}/`
3. Use `drafts/` for work-in-progress documents
4. Move approved drafts to their final location
5. Archive obsolete documents in `archives/`
