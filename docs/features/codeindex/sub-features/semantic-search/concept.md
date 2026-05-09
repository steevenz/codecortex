# Semantic Search

> **Source:** `src/domain/codeindex/infrastructure/embeddings.py`

## Concept

Semantic search uses vector embeddings to find code by meaning rather than by exact keyword match. A query like "handle user login" can find functions named `authenticate_user`, `login_handler`, or `sign_in` — even though none contain the exact query words.

## How It Works

```
Query: "payment retry logic"
         │
         ▼
  sentence-transformers ──────> embedding [384-dim vector]
         │
         ▼
  Cosine similarity against ───> Top-K results
  all indexed code chunks
         │
         ▼
  Rank by score ──────────────> Response
```

## Architecture

- **Model:** `all-MiniLM-L6-v2` (384-dim embeddings, 80MB)
- **Loading:** Lazy singleton — model loads on first query, not on server start
- **Chunking:** Code is split by function/class boundaries (not arbitrary token windows)
- **Storage:** Embeddings stored as numpy `.npy` files alongside SQLite
- **Fallback:** If model unavailable (no GPU/RAM), gracefully returns empty results
- **Speed:** ~50ms per query after model loaded

## Impact

| Aspect | Without Semantic Search | With Semantic Search |
|--------|------------------------|---------------------|
| Find login code | Must search for "login", "auth", "signin" separately | One query: "user authentication" |
| Find config loading | Must know exact function name | Query: "load configuration from file" |
| Cross-language | Language-specific queries | Concept-based, works across languages |
