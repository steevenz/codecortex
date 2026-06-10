# Documentation Standard

> **Standard:** Aegis-Documentation-v1.0
> **Applies to:** All domain documentation in `docs/features/{domain}/`

## 1. File Structure

```
docs/features/{domain}/
├── concept.md                    # Main domain documentation (MANDATORY)
├── ai-impact-token-efficiency.md # AI impact analysis (MANDATORY)
└── sub-features/
    ├── {action1}/
    │   └── concept.md            # Per-action documentation (MANDATORY)
    ├── {action2}/
    │   └── concept.md
    └── ...
```

## 2. concept.md Required Sections

### Header Block (top of file)
```markdown
# {DomainName}: {Short Description}

> **Domain:** {DomainName}
> **Package:** `src/modules/{domain}/`
> **Version:** {semver}
> **AI Coder Impact:** {0-10} ⭐
> **Production Readiness:** {0-100}% 🎯
```

### Required Sections

1. **Business Context** — Why this domain exists, what problem it solves
2. **Why This Exists** — Bullet list of specific pain points
3. **Architecture** — Directory tree showing module structure
4. **Domain Boundary** — What this domain owns/doesn't own, dependencies
5. **CLI Architecture Note** — CLI domain name and aliases
6. **~/.aicoders/ Compliance** — How this domain follows standards
7. **Error Codes** — Table of all error codes with severity + description
8. **AI Coder Impact Features** — 10-12 features, each with one-line description
9. **Token Economy** — How token efficiency is managed
10. **Related Sub-Features** — Links to sub-feature docs
11. **Related Domains** — Links to related domain docs

### Sub-feature concept.md Required Sections

1. **Purpose** — One-line description
2. **Why It Exists** — Context for the action
3. **Parameters** — Table with Field, Type, Required, Default, Description
4. **Output Format** — JSON example with realistic data
5. **Algorithm** — Step-by-step execution flow
6. **Use Case** — Scenario + workflow
7. **Error Cases** — Table of error codes

## 3. Versioning

- Main `concept.md` MUST have version header
- Version follows semver: `major.minor.patch`
- Breaking changes → major version bump
- New features → minor version bump
- Doc fixes → patch version bump

## 4. AI Impact Scoring

- **Impact score (0-10):** Based on AI coder utility
- **Production readiness (0-100%):** Based on test coverage, error handling, documentation completeness
- Scores MUST be justified by the 10/12 features listed

## 5. Compliance Checklist

- [ ] `concept.md` exists at domain root
- [ ] Version header present with semver
- [ ] All 11 required sections present
- [ ] Sub-feature docs exist for each action
- [ ] `ai-impact-token-efficiency.md` exists
- [ ] No orphaned/outdated docs in the directory
- [ ] All cross-links work (no broken references)
- [ ] Error codes documented in table format
- [ ] Output format shows realistic JSON example
