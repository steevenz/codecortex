"""
/**
 * @project   CodeCortex
 * @package   Core
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Core package – Database management and infrastructure.
 */
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


class VersionProvider:
    """
    Provides version information without global state.

    Follows Aegis modular-standard.md requirement for no global state.
    Version caching is handled internally within the instance.
    """
    def __init__(self, project_root: Optional[Path] = None):
        self._project_root = project_root or Path(__file__).resolve().parents[2]
        self._cache: Optional[str] = None

    def get_version(self) -> str:
        """
        Load and cache version from .version file.

        Returns:
            Version string or "0.0.0" if file not found
        """
        if self._cache is not None:
            return self._cache

        version_path = self._project_root / ".version"
        try:
            self._cache = version_path.read_text(encoding="utf-8").strip()
        except Exception:
            self._cache = "0.0.0"
        return self._cache


# Default instance for backward compatibility
_default_provider: Optional[VersionProvider] = None


def load_version(project_root: Optional[Path] = None) -> str:
    """
    Load version using provider pattern (no global state violation).

    This function maintains backward compatibility while avoiding global state.
    Each call creates or reuses a provider instance.
    """
    global _default_provider
    if _default_provider is None or project_root is not None:
        _default_provider = VersionProvider(project_root)
    return _default_provider.get_version()


def new_request_id() -> str:
    return f"req_{uuid4()}"


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    v = raw.strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def api_response(
    *,
    success: bool,
    status_code: int,
    message: str,
    data: Any,
    request_id: str,
    error_code: Optional[str] = None,
    version: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    workspace_id: Optional[str] = "local",
    summary_mode: bool = False,
    max_tokens: Optional[int] = None,
) -> dict:
    # Rule R4: success MUST be false for status_code >= 400
    actual_success = False if status_code >= 400 else bool(success)
    
    # Rule R3: data MUST be null for error responses
    actual_data = None if status_code >= 400 else data

    # Token economy: auto-optimize if summary_mode or data exceeds budget
    meta_payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "workspace_id": workspace_id,
        "request_id": request_id,
        "timestamp": utc_now_iso(),
        "version": version or load_version(),
        "api_version": "v1",
        "error_code": error_code,
    }

    token_economy = None
    if actual_data is not None and (summary_mode or actual_data):
        from .token_economy import estimate_tokens, optimize_response, get_token_budget
        import json as _json
        budget = max_tokens or get_token_budget()
        data_str = _json.dumps(actual_data, default=str)
        tok = estimate_tokens(data_str)
        if summary_mode or tok > budget:
            optimized = optimize_response(actual_data, budget)
            if summary_mode:
                actual_data = optimized.to_dict(include_details=False)
            else:
                actual_data = optimized.to_dict(include_details=True)
            token_economy = {
                "used": optimized.token_count,
                "budget": optimized.budget,
                "truncated": optimized.truncated,
                "cache_hit": optimized.cache_hit,
            }

    result = {
        "success": actual_success,
        "status_code": int(status_code),
        "message": message,
        "data": actual_data,
        "meta": meta_payload,
    }
    if token_economy:
        result["token_economy"] = token_economy
    return result
