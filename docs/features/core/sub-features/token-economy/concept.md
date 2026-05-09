# Token Economy

> **Source:** `src/core/token_economy.py`

## Concept

The token economy module estimates, budgets, and optimizes token usage for LLM responses. This ensures that responses fit within context windows without truncation or information loss.

## Components

| Component | Function | Description |
|-----------|----------|-------------|
| `estimate_tokens()` | Token counting | Estimates token count for strings, dicts, lists |
| `truncate_to_budget()` | Truncation | Smartly truncates content to fit within token budget |
| `smart_summarize()` | Summarization | Summarizes large content while preserving key data |
| `optimize_response()` | Optimization | Removes redundant fields, shortens keys |
| `TokenCache` | Caching | LRU cache for token estimation results |
| `mcp_response()` | Wrapper | Wraps `api_response()` with token economy |

## Token Budget

Default budget: **2000 tokens** (configurable via `CODECORTEX_TOKEN_BUDGET`)

When a response exceeds the budget:
1. **optimize_response** — Remove redundant fields, shorten repetitive arrays
2. **smart_summarize** — Summarize large text blocks (code, strings)
3. **truncate_to_budget** — Hard truncation as last resort

## Benefits

- Prevents LLM context window overflow (>100K token responses)
- Reduces token costs (pay-per-token models)
- Preserves the most relevant information
- Graceful degradation: LLM never sees truncated/incomplete JSON
