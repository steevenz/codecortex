# Modularize

> **Sub-Feature:** Modularize
> **Action:** `modularize`
> **Rating:** 5/5 (Essential) ⭐⭐⭐⭐⭐

## Purpose

Split a monolithic file into domain-aligned modules using Tree-Sitter cluster analysis and AI-assisted domain inference. Applies DDD structure with language-specific naming conventions.

## Why This Exists

- **Monolith Split:** AI can split monolithic files into domain-aligned modules
- **DDD Structure:** Generates DDD-aligned directory structure
- **Domain Inference:** AI-assisted clustering based on symbol names and keywords
- **Naming Conventions:** Language-specific naming per ~/.aicoders/ standards

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_id` | string | ✅ | — | Repository UUID |
| `target_symbol` | string | ✅ | — | Monolithic file to split |
| `changes.target_domain` | string | ✅ | — | Target domain directory |
| `changes.strategy` | string | ❌ | `auto` | `auto` / `manual` |
| `dry_run` | bool | ❌ | `true` | Preview without applying |

## Output

```json
{
  "status": "preview",
  "message": "Modularize: 4 domain(s), 12 file(s)",
  "changes": [
    {
      "path": "src/domain/billing/services/payment_processor.py",
      "action": "add",
      "description": "Create billing/payment_processor.py"
    },
    {
      "path": "src/utils/monolith.py",
      "action": "mark_deprecated",
      "description": "Source monolith.py split into 4 domains"
    }
  ]
}
```

## 5-Phase AI-Assisted Flow

### Phase 1: Analyze (Tree-Sitter)
- Parse file → extract all classes, functions, methods
- Detect coupling: which symbols reference each other?

### Phase 2: Cluster (Domain Inference)
- Infer domain from symbol names + code keywords:
  - `auth` → login, register, session, token, user, permission
  - `payment` → invoice, billing, transaction, receipt, refund
  - `notification` → email, sms, push, notif, alert, webhook
  - `database` → repository, query, migration, model, entity
  - `api` → controller, route, endpoint, handler, middleware
  - `infrastructure` → logger, config, cache, queue, metric
  - `core` → (fallback for uncategorized symbols)
- Group symbols by domain cluster → one file per cluster

### Phase 3: Generate (Naming Convention)
- Apply language-specific naming per ~/.aicoders/ standards:
  - Python → snake_case dir + snake_case file
  - JS/TS → kebab-case dir + PascalCase file
  - PHP → PascalCase dir + PascalCase file
  - Go → snake_case dir + snake_case file
  - Java → lowercase dir + PascalCase file
- Generate `__init__.py` (Python) or `index.ts` (JS/TS) with exports

### Phase 4: Create
- Write new files to target domain directory
- Source file preserved (backward compat)

### Phase 5: Commit & Reindex
- Git commit with descriptive message
- Auto DB reindex for all new files

## Example

```python
# BEFORE: src/services/monolith.py (800 lines, mixed domains)
class PaymentProcessor: ...    # billing
class InvoiceGenerator: ...    # billing
class EmailNotifier: ...       # notification
class UserValidator: ...       # user
class AuditLogger: ...         # infrastructure

# AFTER: src/domain/billing/
services/
  payment_processor.py     # class PaymentProcessor
  invoice_generator.py     # class InvoiceGenerator
__init__.py                # public API exports

# AFTER: src/domain/notification/
services/
  email_notifier.py        # class EmailNotifier
__init__.py

# AFTER: src/domain/user/
services/
  user_validator.py        # class UserValidator
__init__.py

# AFTER: src/infrastructure/audit/
logger.py                  # class AuditLogger
```

## Use Case

AI agents can split monolithic files into domain-aligned modules with DDD structure and language-specific naming conventions.
