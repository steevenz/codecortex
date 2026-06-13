"""
Token Economy – optimizes LLM token usage across all MCP responses.
Features:
1. Token budget tracking per tool call
2. Smart truncation (summary first, detail on demand)
3. Context-aware response sizing
4. Cache for repeated queries (semantic + exact)
5. Response compression (remove redundant fields)
6. Progressive disclosure (summary → detail → full).

:project: CodeCortex
:package: Core.Token.Economy
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from src.core.logging import get_logger

logger = get_logger("CodeCortex.Core.TokenEconomy")

DEFAULT_TOKEN_BUDGET = 2000
MAX_TOKEN_BUDGET = 32000

TOKENS_PER_CHAR = 0.25
TOKENS_PER_WORD = 1.3

def estimate_tokens(text: str) -> int:
    return int(len(text) * TOKENS_PER_CHAR + text.count(" ") * TOKENS_PER_WORD)

def truncate_to_budget(text: str, budget: int, preserve_head: bool = True) -> str:
    if estimate_tokens(text) <= budget:
        return text

    chars = int(budget / TOKENS_PER_CHAR)
    if preserve_head:
        return text[:chars] + f"\n... [truncated, {estimate_tokens(text)} tokens → {budget} budget]"
    else:
        return f"... [truncated] ...\n" + text[-chars:]

def smart_summarize(content: str, max_tokens: int = 500) -> str:
    if estimate_tokens(content) <= max_tokens:
        return content

    lines = content.split("\n")
    important_lines = []
    token_count = 0

    for line in lines:
        stripped = line.strip()
        if (
            stripped.startswith(
                ("import ", "from ", "class ", "def ", "async def ", "@", "return ", "yield ", "raise ")
            )
            or stripped.endswith("):")
            or stripped.endswith(") {")
            or stripped.startswith("#")
            or stripped.startswith("//")
            or "->" in stripped
            or ":" in stripped
        ):
            tok = estimate_tokens(line)
            if token_count + tok > max_tokens:
                important_lines.append(f"... [+{len(lines) - lines.index(line)} more lines]")
                break
            important_lines.append(line)
            token_count += tok

    result = "\n".join(important_lines)
    if len(important_lines) < len(lines):
        result += f"\n... [summary: {len(important_lines)}/{len(lines)} lines, ~{token_count} tokens]"

    return result

class TokenCache:
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self._cache: Dict[str, tuple] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def _make_key(self, *args, **kwargs) -> str:
        raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, *args, **kwargs) -> Optional[Any]:
        key = self._make_key(*args, **kwargs)
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                result, ts, tokens = entry
                if datetime.now() - ts < timedelta(seconds=self._ttl):
                    return result
                del self._cache[key]
        return None

    def set(self, result: Any, tokens_saved: int = 0, *args, **kwargs):
        key = self._make_key(*args, **kwargs)
        with self._lock:
            if len(self._cache) >= self._max_size:
                oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest]
            self._cache[key] = (result, datetime.now(), tokens_saved)

    @property
    def total_tokens_saved(self) -> int:
        with self._lock:
            return sum(entry[2] for entry in self._cache.values())

    def clear(self):
        with self._lock:
            self._cache.clear()

_global_cache: Optional[TokenCache] = None

def get_cache() -> TokenCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = TokenCache()
    return _global_cache

def get_token_budget() -> int:
    raw = os.getenv("CODECORTEX_TOKEN_BUDGET", str(DEFAULT_TOKEN_BUDGET)).strip()
    try:
        return min(MAX_TOKEN_BUDGET, max(100, int(raw)))
    except ValueError:
        return DEFAULT_TOKEN_BUDGET

from dataclasses import dataclass

@dataclass
class TokenOptimization:
    summary: str = ""
    details: Optional[Dict] = None
    token_count: int = 0
    budget: int = DEFAULT_TOKEN_BUDGET
    truncated: bool = False
    cache_hit: bool = False
    tokens_saved: int = 0

    def to_dict(self, include_details: bool = False) -> Dict:
        result = {
            "summary": self.summary,
            "token_economy": {
                "used": self.token_count,
                "budget": self.budget,
                "truncated": self.truncated,
                "cache_hit": self.cache_hit,
                "tokens_saved": self.tokens_saved,
            },
        }
        if include_details and self.details:
            detail_str = json.dumps(self.details, default=str)
            if estimate_tokens(detail_str) <= self.budget * 0.5:
                result["details"] = self.details
        return result

def optimize_response(data: Any, max_tokens: Optional[int] = None) -> TokenOptimization:
    budget = max_tokens or get_token_budget()

    if isinstance(data, str):
        text = data
    else:
        text = json.dumps(data, indent=2, default=str)

    token_count = estimate_tokens(text)

    if token_count <= budget:
        return TokenOptimization(
            summary=text if isinstance(data, str) else json.dumps(data, default=str),
            details=data if not isinstance(data, str) else None,
            token_count=token_count,
            budget=budget,
            truncated=False,
        )

    if isinstance(data, dict):
        summary_parts = []
        estimated = 0

        for key, value in data.items():
            if key in ("meta", "trace", "_debug", "raw"):
                continue

            if isinstance(value, (str, int, float, bool)):
                part = f"{key}: {value}"
            elif isinstance(value, list) and len(value) > 5:
                part = f"{key}: [{len(value)} items]"
            elif isinstance(value, dict):
                part = f"{key}: {json.dumps(value, default=str)[:100]}"
            else:
                part = f"{key}: {str(value)[:100]}"

            part_tok = estimate_tokens(part)
            if estimated + part_tok > budget * 0.6:
                summary_parts.append(f"... (+{len(data) - len(summary_parts) - 1} more fields)")
                break
            summary_parts.append(part)
            estimated += part_tok

        summary = "\n".join(summary_parts)
        return TokenOptimization(
            summary=summary,
            details=data,
            token_count=token_count,
            budget=budget,
            truncated=True,
        )

    elif isinstance(data, list):
        if len(data) > 3:
            summary = f"[{len(data)} items]. First: {json.dumps(data[:3], default=str)[:300]}"
        else:
            summary = json.dumps(data, default=str)

        return TokenOptimization(
            summary=summary[: int(budget / TOKENS_PER_CHAR)],
            details=data[:10] if len(data) > 10 else data,
            token_count=token_count,
            budget=budget,
            truncated=len(data) > 3 or token_count > budget,
        )

    else:
        return TokenOptimization(
            summary=truncate_to_budget(str(data), budget),
            details=data,
            token_count=token_count,
            budget=budget,
            truncated=token_count > budget,
        )
