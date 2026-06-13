# Architecture — Myawesomeproject

> **Standard:** CODDY-Architecture-v1.0
> **Project:** Myawesomeproject
> **Stack:** python
> **Pattern:** layered

## Domain Map

```
myawesomeproject/
├── src/
│   ├── core/           → Business logic, domain entities
│   ├── api/            → API endpoints, controllers
│   ├── services/       → Business services
│   └── adapters/       → External integrations
├── tests/
│   ├── Unit/            → Unit tests
│   ├── Integration/     → Integration tests
│   └── Feature/         # Feature tests
├── docs/
│   ├── architecture/    → Architecture docs
│   ├── features/        # Feature docs
│   └── guides/          # User guides
└── scripts/
    ├── setup/           # Setup scripts
    ├── migration/       # Migration scripts
    └── maintenance/    # Maintenance scripts
```

## Clean Architecture Layers

```
api/        → Input adapters (MCP tools, CLI commands)
core/       → Business logic, domain entities, services
adapters/   → External service wrappers (storage, 3rd-party APIs)
models/     → DTOs (dataclasses for layer crossings)
```

## Dependency Injection

All services use constructor injection:
- StackRepository → injected via constructor
- TemplateRepository → injected via constructor
- TemplateEngine → injected via constructor
- FileHeader → injected via constructor

## Domain Boundaries

- Owns: Project-specific business logic
- Does NOT own: External 3rd-party SDKs (wrapped in adapters)
- Dependencies: External services via adapters only
