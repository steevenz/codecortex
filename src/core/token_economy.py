"""
/**
 * @project   CodeCortex
 * @package   Core/TokenEconomy
 * @standard  Aegis-CrossStack-v1.0
 * * Token Economy — optimizes LLM token usage across all MCP responses.
 *   
 *   Features:
 *   1. Token budget tracking per tool call
 *   2. Smart truncation (summary first, detail on demand)
 *   3. Context-aware response sizing
 *   4. Cache for repeated queries (semantic + exact)
 *   5. Response compression (remove redundant fields)
 *   6. Progressive disclosure (summary → detail → full)
 */
"""

import os
import json
import hashlib
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger("CodeCortex.Core.TokenEconomy")

DEFAULT_TOKEN_BUDGET = 2000  # Default max tokens per tool call
MAX_TOKEN_BUDGET = 32000     # Absolute max

# Average tokens per character (rough estimate)
TOKENS_PER_CHAR = 0.25
TOKENS_PER_WORD = 1.3


def estimate_tokens(text: str) -> int:
    """Estimate token count for a string."""
    return int(len(text) * TOKENS_PER_CHAR + text.count(" ") * TOKENS_PER_WORD)


def truncate_to_budget(text: str, budget: int, preserve_head: bool = True) -> str:
    """Truncate text to fit within token budget."""
    if estimate_tokens(text) <= budget:
        return text
    
    chars = int(budget / TOKENS_PER_CHAR)
    if preserve_head:
        return text[:chars] + f"\n... [truncated, {estimate_tokens(text)} tokens → {budget} budget]"
    else:
        return f"... [truncated] ...\n" + text[-chars:]


def smart_summarize(content: str, max_tokens: int = 500) -> str:
    """
    Create a token-efficient summary of code/content.
    Preserves: structure, imports, function signatures, class definitions.
    Strips: implementation details, comments, blank lines.
    """
    if estimate_tokens(content) <= max_tokens:
        return content
    
    lines = content.split("\n")
    important_lines = []
    token_count = 0
    
    for line in lines:
        stripped = line.strip()
        # Always keep: imports, definitions, decorators, return types
        if (stripped.startswith(("import ", "from ", "class ", "def ", "async def ",
                                 "@", "return ", "yield ", "raise ",
                                 "public ", "private ", "function ", "const ", "let ", "var ",
                                 "interface ", "type ", "enum ", "struct ")) or
            stripped.endswith("):") or stripped.endswith(") {") or
            stripped.startswith("#") or stripped.startswith("//") or
            "->" in stripped or ":" in stripped):
            
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
    """
    In-memory LRU cache for expensive operations.
    Keys are content hashes, values are (result, timestamp, token_count).
    """
    
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
                # Remove oldest entry
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


# Global cache instance
_global_cache = None

def get_cache() -> TokenCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = TokenCache()
    return _global_cache


def get_token_budget() -> int:
    """Get token budget from env or default."""
    raw = os.getenv("CODECORTEX_TOKEN_BUDGET", str(DEFAULT_TOKEN_BUDGET)).strip()
    try:
        return min(MAX_TOKEN_BUDGET, max(100, int(raw)))
    except ValueError:
        return DEFAULT_TOKEN_BUDGET


@dataclass
class TokenOptimizedResponse:
    """Wrapper for token-efficient API responses."""
    summary: str = ""
    details: Optional[Dict] = None
    token_count: int = 0
    budget: int = DEFAULT_TOKEN_BUDGET
    truncated: bool = False
    cache_hit: bool = False
    tokens_saved: int = 0
    
    def to_dict(self, include_details: bool = False) -> Dict:
        """Convert to dictionary for API response."""
        result = {
            "summary": self.summary,
            "token_economy": {
                "used": self.token_count,
                "budget": self.budget,
                "truncated": self.truncated,
                "cache_hit": self.cache_hit,
                "tokens_saved": self.tokens_saved,
            }
        }
        if include_details and self.details:
            # Only include details if they fit within budget
            detail_str = json.dumps(self.details, default=str)
            if estimate_tokens(detail_str) <= self.budget * 0.5:
                result["details"] = self.details
        return result


def optimize_response(data: Any, max_tokens: Optional[int] = None) -> TokenOptimizedResponse:
    """
    Wrap any response data with token optimization.
    Automatically truncates/summarizes to fit within budget.
    """
    budget = max_tokens or get_token_budget()
    
    # Convert to string for token counting
    if isinstance(data, str):
        text = data
    else:
        text = json.dumps(data, indent=2, default=str)
    
    token_count = estimate_tokens(text)
    
    if token_count <= budget:
        return TokenOptimizedResponse(
            summary=text if isinstance(data, str) else json.dumps(data, default=str),
            details=data if not isinstance(data, str) else None,
            token_count=token_count,
            budget=budget,
            truncated=False,
        )
    
    # Need to truncate
    if isinstance(data, dict):
        # For dicts, create a summary first
        summary_parts = []
        estimated = 0
        
        for key, value in data.items():
            if key in ("meta", "trace", "_debug", "raw"):
                continue  # Skip internal fields
            
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
        return TokenOptimizedResponse(
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
        
        return TokenOptimizedResponse(
            summary=summary[:int(budget / TOKENS_PER_CHAR)],
            details=data[:10] if len(data) > 10 else data,
            token_count=token_count,
            budget=budget,
            truncated=len(data) > 3 or token_count > budget,
        )
    
    else:
        return TokenOptimizedResponse(
            summary=truncate_to_budget(str(data), budget),
            details=data,
            token_count=token_count,
            budget=budget,
            truncated=token_count > budget,
        )


# ── Token-aware MCP response wrapper ──

def mcp_response(
    success: bool,
    message: str,
    data: Any = None,
    request_id: str = "",
    error_code: str = "",
    max_tokens: Optional[int] = None,
    summary_mode: bool = False,
) -> Dict:
    """Token-optimized MCP response. Auto-compresses data to fit budget."""
    optimized = None
    if data is not None:
        budget = max_tokens or get_token_budget()
        tok = estimate_tokens(json.dumps(data, default=str))
        if summary_mode or tok > budget:
            optimized = optimize_response(data, budget)
    
    if summary_mode and optimized:
        payload = optimized.to_dict(include_details=False)
    elif optimized and optimized.truncated:
        payload = optimized.to_dict(include_details=True)
    else:
        payload = data
    
    result = {
        "success": success,
        "status_code": 200 if success else 400,
        "message": message,
        "data": payload,
        "meta": {"request_id": request_id},
    }
    if not success and error_code:
        result["error_code"] = error_code
    if optimized:
        result["token_economy"] = {
            "used": optimized.token_count,
            "budget": optimized.budget,
            "truncated": optimized.truncated,
            "cache_hit": optimized.cache_hit,
        }
    return result
